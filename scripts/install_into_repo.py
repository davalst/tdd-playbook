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
Then:  git -C TARGET_REPO add .claude && git commit && git push   # → loads in cloud

Re-run any time to refresh a repo after the canonical plugin updates (it overwrites the vendored
copies; your repo-specific hooks in settings.json are preserved).
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


def _merge_hooks(claude_dir: str) -> int:
    """Merge the plugin's hooks/hooks.json into <repo>/.claude/settings.json (append per event)."""
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

    added = 0
    for event, groups in plugin_hooks.items():
        bucket = existing.setdefault(event, [])
        existing_blob = json.dumps(bucket, sort_keys=True)
        for group in groups:
            # idempotent: don't double-add the same group on re-run
            if json.dumps(group, sort_keys=True) not in existing_blob:
                bucket.append(group)
                added += 1
    # drop the unreliable marketplace path if present — vendored content supersedes it
    settings.pop("extraKnownMarketplaces", None)
    settings.pop("enabledPlugins", None)

    with open(settings_path, "w") as fh:
        json.dump(settings, fh, indent=4)
        fh.write("\n")
    return added


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
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
