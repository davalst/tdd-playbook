#!/usr/bin/env python3
"""Install the TDD Playbook's Claude or Codex host package into a repository.

Claude cloud/web/mobile sandboxes need the established vendored `.claude/` package.  Codex uses a
separate `.codex/` package and hook registry.  This installer never conflates those vendor states:
each reconciler prunes only its own command namespace and preserves unrelated host configuration.
The default remains Claude-only for downstream compatibility; Codex and dual installs are explicit.

Usage:
    python3 scripts/install_into_repo.py [TARGET_REPO]   # default: Claude, current directory
    python3 scripts/install_into_repo.py --host codex [TARGET_REPO]
    python3 scripts/install_into_repo.py --host all [TARGET_REPO]
    python3 scripts/install_into_repo.py --doctor [TARGET_REPO]   # version-skew check
Then commit the selected host directory.  Codex project hooks also require project trust and hook
review; configuration present on disk is not proof that the native runtime invoked it.

Re-run any time to refresh a repo after the canonical plugin updates (it overwrites the vendored
copies; your repo-specific hooks in settings.json are preserved).

--doctor compares three versions that silently drift apart: the CANONICAL plugin (this checkout),
the repo's VENDORED copy (stamped at vendor time in .claude/.tdd-playbook-version), and the locally
INSTALLED plugin cache (~/.claude/plugins/cache). Origin: a live setup ran v1.1.0 plugin hooks
alongside v1.5-era vendored hooks for weeks — duplicate, version-skewed enforcement nobody could
see. Skew exits 1 with the fix to run; missing surfaces (no cache in a cloud sandbox, repo not
vendored) are informational, not failures.
"""
from __future__ import annotations

import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "plugins", "tdd-playbook"))
PLUGIN_ROOT_VAR = "${CLAUDE_PLUGIN_ROOT}"
PROJECT_ROOT_VAR = "$CLAUDE_PROJECT_DIR/.claude"
CODEX_PLUGIN_ROOT_VAR = "${PLUGIN_ROOT}"
CODEX_PROJECT_ROOT_VAR = "$(git rev-parse --show-toplevel)/.codex/tdd-playbook"

# (src subdir under the plugin, dest subdir under <repo>/.claude). Layout preserved so the
# ${CLAUDE_PLUGIN_ROOT} → $CLAUDE_PROJECT_DIR/.claude rewrite keeps every internal path valid.
COPY_TREES = [
    ("skills/tdd-playbook", "skills/tdd-playbook"),
    ("commands", "commands"),
    ("agents", "agents"),
    ("adapters", "adapters"),
    ("bin", "bin"),
    ("hooks/scripts", "hooks/scripts"),
]
# Codex's current native discovery surface consumes the hook runtime only.  Claude-shaped
# commands/agents copied under a private runtime directory are not discoverable and therefore
# become integration islands.  The parity manifest owns their unavailable/debt disposition.
CODEX_COPY_TREES = [
    ("adapters", "adapters"),
    ("bin", "bin"),
]
CODEX_COPY_FILES = [
    ("hooks/scripts/_common.py", "hooks/scripts/_common.py"),
    ("hooks/scripts/test_lock_guard.py", "hooks/scripts/test_lock_guard.py"),
]
# files whose body references ${CLAUDE_PLUGIN_ROOT} and must be rewritten on copy
REWRITE_EXT = {".md", ".py", ".json", ".sh"}


def _rewrite(text: str) -> str:
    return text.replace(PLUGIN_ROOT_VAR, PROJECT_ROOT_VAR)


def _rewrite_codex(text: str) -> str:
    return text.replace(CODEX_PLUGIN_ROOT_VAR, CODEX_PROJECT_ROOT_VAR)


def _copy_tree(src: str, dest: str, rewrite=_rewrite) -> int:
    n = 0
    for root, _dirs, files in os.walk(src):
        if "__pycache__" in root:
            continue
        rel = os.path.relpath(root, src)
        out_dir = os.path.join(dest, rel) if rel != "." else dest
        os.makedirs(out_dir, exist_ok=True)
        for fn in files:
            if fn.endswith(".pyc"):
                continue
            s = os.path.join(root, fn)
            d = os.path.join(out_dir, fn)
            ext = os.path.splitext(fn)[1]
            if ext in REWRITE_EXT:
                with open(s, "r") as fh:
                    body = fh.read()
                with open(d, "w") as fh:
                    fh.write(rewrite(body))
            else:
                shutil.copy2(s, d)
            if ext == ".py" or ext == ".sh":
                os.chmod(d, 0o755)
            n += 1
    return n


def _copy_file(src: str, dest: str, rewrite=_rewrite) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(src, "r") as fh:
        body = fh.read()
    with open(dest, "w") as fh:
        fh.write(rewrite(body))
    if os.path.splitext(dest)[1] in (".py", ".sh"):
        os.chmod(dest, 0o755)
    return 1


_PLUGIN_NS = "/.claude/hooks/scripts/"  # our vendored namespace — plugin-owned, reconciled


def _is_plugin_group(group: dict) -> bool:
    """A hook group is OURS iff every command in it points into the vendored namespace.

    User hooks that live elsewhere (any other path) are never touched. Anyone vendoring
    their OWN scripts into .claude/hooks/scripts/ is inside the plugin-owned namespace and
    will be reconciled — documented behavior; keep custom scripts in another directory.
    """
    hooks = group.get("hooks", [])
    return bool(hooks) and all(_PLUGIN_NS in (h.get("command") or "") for h in hooks)


def _merge_hooks(claude_dir: str) -> int:
    """RECONCILE the plugin's hooks into <repo>/.claude/settings.json.

    Plugin-namespace groups are pruned then re-added from the current hooks.json, so a hook
    the plugin removed or renamed disappears downstream instead of accumulating as drift.
    Non-plugin groups are preserved untouched. Idempotent.
    """
    plugin_hooks_path = os.path.join(PLUGIN, "hooks", "hooks.json")
    if not os.path.isfile(plugin_hooks_path):
        return 0
    with open(plugin_hooks_path) as fh:
        plugin_hooks = json.loads(_rewrite(fh.read())).get("hooks", {})

    settings_path = os.path.join(claude_dir, "settings.json")
    settings: dict = {}
    if os.path.isfile(settings_path):
        with open(settings_path) as fh:
            settings = json.load(fh)
    existing = settings.setdefault("hooks", {})

    # 1) prune every plugin-namespace group from every event bucket (stale or current)
    for event in list(existing):
        kept = [g for g in existing[event] if not _is_plugin_group(g)]
        if kept:
            existing[event] = kept
        else:
            del existing[event]

    # 2) add the CURRENT plugin groups
    added = 0
    for event, groups in plugin_hooks.items():
        bucket = existing.setdefault(event, [])
        for group in groups:
            bucket.append(group)
            added += 1
    # drop the unreliable marketplace path if present — vendored content supersedes it
    settings.pop("extraKnownMarketplaces", None)
    settings.pop("enabledPlugins", None)

    with open(settings_path, "w") as fh:
        json.dump(settings, fh, indent=4)
        fh.write("\n")
    return added


_CODEX_PLUGIN_NS = ".codex/tdd-playbook/"


def _is_codex_plugin_group(group: dict) -> bool:
    hooks = group.get("hooks", [])
    return bool(hooks) and all(
        _CODEX_PLUGIN_NS in (handler.get("command") or "") for handler in hooks)


def _merge_codex_hooks(codex_dir: str) -> int:
    """Reconcile adapter-owned Codex groups while preserving every unrelated entry."""
    source = os.path.join(PLUGIN, "adapters", "codex", "hooks.json")
    with open(source) as fh:
        adapter_hooks = json.loads(_rewrite_codex(fh.read())).get("hooks", {})
    path = os.path.join(codex_dir, "hooks.json")
    settings: dict = {}
    if os.path.isfile(path):
        with open(path) as fh:
            settings = json.load(fh)
    existing = settings.setdefault("hooks", {})
    for event in list(existing):
        kept = [group for group in existing[event] if not _is_codex_plugin_group(group)]
        if kept:
            existing[event] = kept
        else:
            del existing[event]
    added = 0
    for event, groups in adapter_hooks.items():
        existing.setdefault(event, []).extend(groups)
        added += len(groups)
    with open(path, "w") as fh:
        json.dump(settings, fh, indent=4)
        fh.write("\n")
    return added


_STAMP_REL = os.path.join(".claude", ".tdd-playbook-version")
_CODEX_STAMP_REL = os.path.join(".codex", ".tdd-playbook-version")


def _canonical_version() -> str:
    with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")) as fh:
        return json.load(fh)["version"]


def _cache_versions() -> list[str] | None:
    """Installed plugin-cache versions of tdd-playbook, or None when no cache exists
    (e.g. a cloud sandbox — vendored-only surface, nothing to compare)."""
    root = os.environ.get("TDD_PLAYBOOK_PLUGIN_CACHE") or os.path.expanduser(
        "~/.claude/plugins/cache")
    if not os.path.isdir(root):
        return None
    versions = []
    for marketplace in os.listdir(root):
        vdir = os.path.join(root, marketplace, "tdd-playbook")
        if os.path.isdir(vdir):
            versions.extend(v for v in os.listdir(vdir)
                            if os.path.isdir(os.path.join(vdir, v)))
    return versions or None


def _is_guard_control_var(key):
    """Delegate to the module that OWNS the guard env contract, so this check cannot drift
    from it again. Falls back to the historical prefix if _common is unavailable (a partial
    vendored tree) — fail toward flagging, never toward silence."""
    try:
        sys.path.insert(0, os.path.join(PLUGIN, "hooks", "scripts"))
        from _common import is_guard_control_var
        return is_guard_control_var(key)
    except Exception:
        return key.startswith("TDD_PLAYBOOK_HOOK") or key == "TDD_PLAYBOOK_BREAK_GLASS"


def _guard_override_effect(key, value):
    """Delegate the demotion-vs-enablement call to the module that owns the mode contract
    (same reasoning as _is_guard_control_var). On a partial vendored tree where _common is
    unavailable, fail toward flagging: every override reads as a demotion."""
    try:
        sys.path.insert(0, os.path.join(PLUGIN, "hooks", "scripts"))
        from _common import guard_override_effect
        return guard_override_effect(key, value)
    except Exception:
        return "demotion"


def doctor(target: str) -> int:
    """Version-skew check across canonical / vendored / plugin cache. 1 = skew found."""
    canonical = _canonical_version()
    rc = 0
    print(f"canonical plugin version: {canonical}")

    for host, relative, install_args in (
            ("Claude", _STAMP_REL, ""),
            ("Codex", _CODEX_STAMP_REL, "--host codex ")):
        stamp = os.path.join(target, relative)
        if not os.path.isfile(stamp):
            print(f"{host} vendored copy: none in {target} (fine if this host is "
                  "plugin-only; run install_into_repo.py to vendor for cloud)")
            continue
        with open(stamp) as fh:
            vendored = fh.read().strip()
        if vendored == canonical:
            print(f"{host} vendored copy: {vendored} — in sync")
        else:
            print(f"{host.upper()} VENDORED SKEW: repo has {vendored}, canonical is "
                  f"{canonical} — re-run: python3 scripts/install_into_repo.py "
                  f"{install_args}{target}")
            rc = 1

    cache = _cache_versions()
    if cache is None:
        print("plugin cache: none found (vendored-only surface — nothing to compare)")
    elif canonical in cache:
        print(f"plugin cache: {sorted(cache)} — includes canonical")
    else:
        print(f"PLUGIN CACHE SKEW: installed {sorted(cache)}, canonical is {canonical} — "
              "update the plugin (claude /plugin → update tdd-playbook, or refresh the "
              "marketplace) so live sessions stop running stale hooks")
        rc = 1

    # Standing demotions (2026-07-28 sweep, hole 2): an env-block demotion in settings is a
    # persistent, invisible guard kill switch — the doctor makes it visible per repo.
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        sp = os.path.join(target, rel)
        if not os.path.isfile(sp):
            continue
        try:
            with open(sp) as fh:
                envblock = json.load(fh).get("env", {}) or {}
        except ValueError:
            print(f"DEMOTION CHECK: {rel} is unparseable — cannot rule out a standing "
                  "demotion (fail closed)")
            rc = 1
            continue
        # The list of vars that weaken the guard layer is owned by _common, not guessed with a
        # prefix here: TDD_PLAYBOOK_BREAK_GLASS does not start with TDD_PLAYBOOK_HOOK and is a
        # STRICTLY WIDER switch than the per-hook demotions this check was written to catch,
        # so the prefix silently exempted the biggest one (v1.32.0).
        # Classify against each guard's OWN default, don't flag every knob. Five guards ship
        # `off` since v1.32.0, so an override can just as easily turn one back ON — reporting
        # that as a kill switch is how the real demotions get skimmed past (2026-08-17).
        overrides = {k: v for k, v in envblock.items() if _is_guard_control_var(k)}
        buckets = {}
        for k, v in overrides.items():
            buckets.setdefault(_guard_override_effect(k, v), {})[k] = v
        weaker = {**buckets.get("demotion", {}), **buckets.get("unknown", {})}
        if weaker:
            print(f"STANDING DEMOTION: {rel} env block sets {weaker} — guards are "
                  "demoted for EVERY session in this repo; restore or journal it with an "
                  "owner and expiry (H-class kill switch otherwise)")
            rc = 1
        stronger = buckets.get("enablement", {})
        if stronger:
            print(f"guard opt-in: {rel} env block sets {stronger} — STRONGER than shipped "
                  "defaults (a retired/advisory guard turned up), not a demotion")
        same = buckets.get("noop", {})
        if same:
            print(f"guard override (no effect): {rel} env block sets {same} — already the "
                  "shipped default")

    # H8 (live incident 2026-07-28): plugin enablement is USER-scope — disabling it in any
    # repo darkens the guard layer everywhere, silently. The heartbeat (written by the
    # UserPromptSubmit hook) is the liveness signal; commits that postdate it mean work
    # happened while no guard fired.
    sys.path.insert(0, os.path.join(PLUGIN, "hooks", "scripts"))
    from _common import guards_dark
    status, detail = guards_dark(target)
    if status == "dark":
        print(f"GUARDS DARK: {detail} — check `claude /plugin` enablement "
              "(user-scope: a disable in ANY repo darkens ALL repos) and reload")
        rc = 1
    else:
        print(f"guards liveness: {status} — {detail}")
    return rc


# Runtime exhaust the vendored playbook writes under .claude/ — the vendoring workflow is
# `git add .claude`, so without this a downstream repo commits a growing event log (G2).
_CLAUDE_IGNORES = ["playbook-yield.jsonl", "tdd-lock-journal.jsonl", "tdd-lock.json",
                   "tdd-lock.json.migrated", "playbook-guards-heartbeat"]


def _merge_claude_gitignore(claude_dir: str) -> None:
    path = os.path.join(claude_dir, ".gitignore")
    existing = []
    if os.path.isfile(path):
        with open(path) as fh:
            existing = [ln.rstrip("\n") for ln in fh]
    missing = [ln for ln in _CLAUDE_IGNORES if ln not in existing]
    if missing:
        with open(path, "a") as fh:
            for ln in missing:
                fh.write(ln + "\n")


def _write_install_manifest(target, host):
    """Record what we wrote, IN the target, so uninstall does not need the source clone."""
    try:
        sys.path.insert(0, os.path.join(PLUGIN, "bin"))
        import vendoring
        vendoring.write_manifest(REPO if "REPO" in globals() else
                                 os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                 target, host)
    except Exception as exc:
        print("manifest: could not record the install roster: {}".format(exc))


def _install_claude(target: str) -> None:
    claude_dir = os.path.join(target, ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    total = 0
    for src_rel, dest_rel in COPY_TREES:
        src = os.path.join(PLUGIN, src_rel)
        if os.path.isdir(src):
            total += _copy_tree(src, os.path.join(claude_dir, dest_rel))
    hooks_added = _merge_hooks(claude_dir)
    _merge_claude_gitignore(claude_dir)
    _write_install_manifest(target, "claude")
    with open(os.path.join(target, _STAMP_REL), "w") as fh:
        fh.write(_canonical_version() + "\n")
    print(f"Vendored {total} file(s) into {claude_dir}")
    print(f"Merged {hooks_added} hook group(s) into .claude/settings.json "
          f"(removed any marketplace/enabledPlugins block)")


def _install_codex(target: str) -> None:
    codex_dir = os.path.join(target, ".codex")
    runtime = os.path.join(codex_dir, "tdd-playbook")
    # This namespace is adapter-owned. Rebuild it so formerly copied, now-unavailable assets
    # do not survive a reconciliatory reinstall as ghost capabilities.
    if os.path.isdir(runtime):
        shutil.rmtree(runtime)
    os.makedirs(runtime, exist_ok=True)
    total = 0
    for src_rel, dest_rel in CODEX_COPY_TREES:
        src = os.path.join(PLUGIN, src_rel)
        if os.path.isdir(src):
            total += _copy_tree(src, os.path.join(runtime, dest_rel), _rewrite_codex)
    for src_rel, dest_rel in CODEX_COPY_FILES:
        total += _copy_file(os.path.join(PLUGIN, src_rel),
                            os.path.join(runtime, dest_rel), _rewrite_codex)
    hooks_added = _merge_codex_hooks(codex_dir)
    with open(os.path.join(target, _CODEX_STAMP_REL), "w") as fh:
        fh.write(_canonical_version() + "\n")
    print(f"Vendored {total} file(s) into {runtime}")
    print(f"Merged {hooks_added} adapter-owned hook group(s) into .codex/hooks.json")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--doctor":
        target = os.path.abspath(argv[1]) if len(argv) > 1 else os.getcwd()
        return doctor(target)
    host = "claude"
    if argv[:1] == ["--host"]:
        if len(argv) < 2 or argv[1] not in ("claude", "codex", "all"):
            sys.stderr.write("--host needs claude|codex|all\n")
            return 2
        host = argv[1]
        argv = argv[2:]
    target = os.path.abspath(argv[0]) if argv else os.getcwd()
    if len(argv) > 1:
        sys.stderr.write("unexpected installer arguments: {}\n".format(" ".join(argv[1:])))
        return 2
    if not os.path.isdir(target):
        sys.stderr.write(f"target repo not found: {target}\n")
        return 2
    if not os.path.isdir(PLUGIN):
        sys.stderr.write(f"plugin source not found: {PLUGIN}\n")
        return 2

    if host in ("claude", "all"):
        _install_claude(target)
    if host in ("codex", "all"):
        _install_codex(target)
    print("\nNext:")
    installed = ".claude" if host == "claude" else ".codex" if host == "codex" \
        else ".claude .codex"
    print(f"  git -C {target} add {installed} && git -C {target} commit -m "
          f"'chore: vendor TDD Playbook host adapters' && git -C {target} push")
    print("Then review/trust the installed host hooks before relying on enforcement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
