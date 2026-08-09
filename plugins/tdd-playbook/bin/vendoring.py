#!/usr/bin/env python3
"""The inverse of scripts/install_into_repo.py — enumerate and remove a vendored Playbook.

WHY THIS LIVES IN bin/ AND NOT scripts/: `scripts/` is never vendored (it is absent from
COPY_TREES), while `bin/` is. A downstream repo that vendored the Playbook has `.claude/bin/`
and no `scripts/` at all, so uninstall logic living only in `scripts/` would be unreachable
exactly where it is needed — in the repo trying to remove itself.

The DELETION RULES are the whole safety story, and they are not uniform because the
namespaces are not:

  - `.claude/skills/tdd-playbook/` — name-scoped to us; remove the subtree.
  - `.claude/hooks/scripts/` — documented plugin-owned, but removed BY NAME anyway: strictly
    safer and equally complete for anything we actually shipped.
  - `.claude/commands/`, `.claude/agents/`, `.claude/bin/`, `.claude/adapters/` — SHARED
    namespaces. A user's own `my-own.md` slash command lives beside ours. An `rmtree` here is
    the single worst bug available in this feature, so: delete by name, then rmdir only if
    empty.
  - `.claude/settings.json` — prune OUR hook groups via the installer's own
    `_is_plugin_group`, and delete the file only if it reduces to `{}`.

Known irreversibilities, surfaced rather than discovered later: install pops
`extraKnownMarketplaces` and `enabledPlugins` from settings.json and records them nowhere, so
no uninstall can restore them; and `.claude/.gitignore` lines cannot be distinguished from
lines the user already had. Both are reported by `plan()` as `note` rows.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _installer(repo):
    """Load the installer as a module so its COPY_TREES / prune predicate are the ONE
    definition of what was written. Re-listing them here would be a second roster that drifts
    from the first, which is the failure this module exists downstream of."""
    import importlib.util
    path = os.path.join(repo, "scripts", "install_into_repo.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("install_into_repo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _walk_rel(src_root, dest_root_rel):
    out = []
    for dirpath, dirnames, filenames in os.walk(src_root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if fn.endswith(".pyc"):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), src_root)
            out.append(os.path.join(dest_root_rel, rel).replace(os.sep, "/"))
    return out


def installed_paths(repo, target, host="claude"):
    """Repo-relative paths this installer would have written into `target`.

    Derived by walking the SOURCE trees, so it cannot drift from what install copies."""
    mod = _installer(repo)
    if mod is None:
        return []
    plugin = mod.PLUGIN
    out = []
    if host in ("claude", "all"):
        for src_rel, dest_rel in mod.COPY_TREES:
            out += _walk_rel(os.path.join(plugin, src_rel),
                             os.path.join(".claude", dest_rel))
        out.append(mod._STAMP_REL.replace(os.sep, "/"))
    if host in ("codex", "all"):
        for src_rel, dest_rel in getattr(mod, "CODEX_COPY_TREES", []):
            out += _walk_rel(os.path.join(plugin, src_rel),
                             os.path.join(".codex", "tdd-playbook", dest_rel))
        for src_rel, dest_rel in getattr(mod, "CODEX_COPY_FILES", []):
            out.append(os.path.join(".codex", "tdd-playbook",
                                    dest_rel).replace(os.sep, "/"))
        out.append(mod._CODEX_STAMP_REL.replace(os.sep, "/"))
    return sorted(set(out))


def prune_plugin_groups(existing, is_ours):
    """Drop OUR hook groups from a settings `hooks` mapping, in place. Returns the count.

    This is the installer's own reconcile step, extracted verbatim so install and uninstall
    provably share one definition of "a group of ours"."""
    removed = 0
    for event in list(existing):
        kept = [g for g in existing[event] if not is_ours(g)]
        removed += len(existing[event]) - len(kept)
        if kept:
            existing[event] = kept
        else:
            del existing[event]
    return removed


def _prune_settings(target, mod, apply):
    rel = os.path.join(".claude", "settings.json")
    path = os.path.join(target, rel)
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as fh:
            settings = json.load(fh)
    except ValueError:
        return [{"kind": "note", "path": rel,
                 "why": "unparseable JSON — left untouched, prune it by hand"}]
    hooks = settings.get("hooks") or {}
    before = sum(len(v) for v in hooks.values())
    removed = prune_plugin_groups(hooks, mod._is_plugin_group)
    if not removed:
        return []
    rows = [{"kind": "edit", "path": rel,
             "why": "prune {} playbook hook group(s); PRESERVE {}".format(
                 removed, before - removed)}]
    if apply:
        if hooks:
            settings["hooks"] = hooks
        else:
            settings.pop("hooks", None)
        if settings:
            with open(path, "w") as fh:
                json.dump(settings, fh, indent=4)
                fh.write("\n")
        else:
            os.remove(path)
    return rows


def uninstall(target, host="claude", apply=False, repo=None):
    """Plan (and optionally perform) the removal. Returns the list of planned rows."""
    repo = repo or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    mod = _installer(repo)
    if mod is None:
        return [{"kind": "note", "path": "", "why": "installer not found; nothing to invert"}]

    # Materialise the FULL list before removing anything: this module is itself vendored to
    # .claude/bin/vendoring.py, so uninstall deletes its own source out from under the
    # running process. The loaded module object survives; a lazily-walked list would not.
    rels = list(installed_paths(repo, target, host))
    rows = [{"kind": "file", "path": r, "why": "vendored by install"}
            for r in rels if os.path.exists(os.path.join(target, r))]
    rows += _prune_settings(target, mod, apply)
    rows.append({"kind": "note", "path": os.path.join(".claude", ".gitignore"),
                 "why": "install-added ignore lines are NOT removed — they cannot be told "
                        "apart from lines you already had"})
    rows.append({"kind": "note", "path": os.path.join(".claude", "settings.json"),
                 "why": "extraKnownMarketplaces/enabledPlugins were dropped AT INSTALL time "
                        "and recorded nowhere; no uninstall can restore them"})

    if apply:
        for r in rels:
            p = os.path.join(target, r)
            if os.path.isfile(p) or os.path.islink(p):
                os.remove(p)
        # remove now-empty directories we owned, deepest first; never force
        for r in sorted({os.path.dirname(x) for x in rels}, key=len, reverse=True):
            d = os.path.join(target, r)
            while d.startswith(target) and os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
                d = os.path.dirname(d)
        skills = os.path.join(target, ".claude", "skills", "tdd-playbook")
        if os.path.isdir(skills):
            shutil.rmtree(skills)
        codex_rt = os.path.join(target, ".codex", "tdd-playbook")
        if host in ("codex", "all") and os.path.isdir(codex_rt):
            shutil.rmtree(codex_rt)
    return rows


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="vendoring")
    ap.add_argument("target")
    ap.add_argument("--host", choices=("claude", "codex", "all"), default="claude")
    ap.add_argument("--apply", action="store_true",
                    help="perform the removal (default is a dry run)")
    args = ap.parse_args(argv)
    rows = uninstall(os.path.abspath(args.target), args.host, args.apply)
    if not args.apply:
        print("tdd uninstall — DRY RUN. Nothing has been changed. Re-run with --apply.\n")
    for r in rows:
        print("  {:<5} {:<52} {}".format(r["kind"], r["path"], r["why"]))
    print("\n{} path(s), {} edit(s), {} note(s)".format(
        sum(1 for r in rows if r["kind"] == "file"),
        sum(1 for r in rows if r["kind"] == "edit"),
        sum(1 for r in rows if r["kind"] == "note")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
