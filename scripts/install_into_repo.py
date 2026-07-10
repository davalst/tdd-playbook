#!/usr/bin/env python3
"""Vendor the TDD Playbook plugin into a repo's .claude/ so it loads in CLOUD Claude Code.

Cloud/web/mobile sandboxes only see project-level config that's part of the repo clone — they do
NOT reliably load plugins from an external marketplace, and never load your ~/.claude. So to make
the Playbook available in a cloud session for a repo, its components must live committed under that
repo's .claude/ directory. This script copies them there (preserving the plugin's internal layout
so ${CLAUDE_PLUGIN_ROOT} simply maps to $CLAUDE_PROJECT_DIR/.claude), and merges the hooks into the
repo's .claude/settings.json without clobbering existing hooks.

Usage:
    python3 scripts/install_into_repo.py [TARGET_REPO]   # default: current directory
    python3 scripts/install_into_repo.py --doctor [TARGET_REPO]   # version-skew check
Then:  git -C TARGET_REPO add .claude && git commit && git push   # → loads in cloud

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

# (src subdir under the plugin, dest subdir under <repo>/.claude). Layout preserved so the
# ${CLAUDE_PLUGIN_ROOT} → $CLAUDE_PROJECT_DIR/.claude rewrite keeps every internal path valid.
COPY_TREES = [
    ("skills/tdd-playbook", "skills/tdd-playbook"),
    ("commands", "commands"),
    ("agents", "agents"),
    ("bin", "bin"),
    ("hooks/scripts", "hooks/scripts"),
]
# files whose body references ${CLAUDE_PLUGIN_ROOT} and must be rewritten on copy
REWRITE_EXT = {".md", ".py", ".json", ".sh"}


def _rewrite(text: str) -> str:
    return text.replace(PLUGIN_ROOT_VAR, PROJECT_ROOT_VAR)


def _copy_tree(src: str, dest: str) -> int:
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
                    fh.write(_rewrite(body))
            else:
                shutil.copy2(s, d)
            if ext == ".py" or ext == ".sh":
                os.chmod(d, 0o755)
            n += 1
    return n


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


_STAMP_REL = os.path.join(".claude", ".tdd-playbook-version")


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


def doctor(target: str) -> int:
    """Version-skew check across canonical / vendored / plugin cache. 1 = skew found."""
    canonical = _canonical_version()
    rc = 0
    print(f"canonical plugin version: {canonical}")

    stamp = os.path.join(target, _STAMP_REL)
    if not os.path.isfile(stamp):
        print(f"vendored copy: none in {target} (fine if this repo is plugin-only; "
              "run install_into_repo.py to vendor for cloud)")
    else:
        with open(stamp) as fh:
            vendored = fh.read().strip()
        if vendored == canonical:
            print(f"vendored copy: {vendored} — in sync")
        else:
            print(f"VENDORED SKEW: repo has {vendored}, canonical is {canonical} — "
                  f"re-run: python3 scripts/install_into_repo.py {target}")
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
    return rc


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] == "--doctor":
        target = os.path.abspath(argv[1]) if len(argv) > 1 else os.getcwd()
        return doctor(target)
    target = os.path.abspath(argv[0]) if argv else os.getcwd()
    if not os.path.isdir(target):
        sys.stderr.write(f"target repo not found: {target}\n")
        return 2
    if not os.path.isdir(PLUGIN):
        sys.stderr.write(f"plugin source not found: {PLUGIN}\n")
        return 2

    claude_dir = os.path.join(target, ".claude")
    os.makedirs(claude_dir, exist_ok=True)
    total = 0
    for src_rel, dest_rel in COPY_TREES:
        src = os.path.join(PLUGIN, src_rel)
        if os.path.isdir(src):
            total += _copy_tree(src, os.path.join(claude_dir, dest_rel))
    hooks_added = _merge_hooks(claude_dir)
    with open(os.path.join(target, _STAMP_REL), "w") as fh:
        fh.write(_canonical_version() + "\n")

    print(f"Vendored {total} file(s) into {claude_dir}")
    print(f"Merged {hooks_added} hook group(s) into .claude/settings.json "
          f"(removed any marketplace/enabledPlugins block)")
    print("\nNext:")
    print(f"  git -C {target} add .claude && git -C {target} commit -m "
          f"'chore: vendor TDD Playbook for cloud' && git -C {target} push")
    print("Then open a CLOUD session on the repo — skill + commands + agents + hooks load from "
          "the clone (no marketplace needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
