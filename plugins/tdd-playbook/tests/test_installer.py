#!/usr/bin/env python3
"""Planted-input calibration for scripts/install_into_repo.py hook RECONCILIATION.

The old merge was append-only: a hook the plugin removed/renamed stayed in downstream
settings.json forever (drift). Planted here: a STALE plugin-namespace group must be pruned,
a CUSTOM user group must survive, current groups land exactly once, and re-runs are
idempotent. Self-contained, no pytest. Run: python3 tests/test_installer.py
"""
import importlib.util
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
INSTALLER = os.path.join(REPO, "scripts", "install_into_repo.py")

_r = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def load_installer():
    spec = importlib.util.spec_from_file_location("install_into_repo", INSTALLER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def flat_commands(settings):
    cmds = []
    for groups in settings.get("hooks", {}).values():
        for g in groups:
            for h in g.get("hooks", []):
                cmds.append(h.get("command", ""))
    return cmds


def main():
    print("install_into_repo reconciliation calibration")
    mod = load_installer()

    with tempfile.TemporaryDirectory() as target:
        cdir = os.path.join(target, ".claude")
        os.makedirs(cdir)
        stale = {"matcher": "Edit|Write", "hooks": [{
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/removed_guard.py\""}]}
        custom = {"matcher": "Bash", "hooks": [{
            "type": "command", "command": "./scripts/my-own-hook.sh"}]}
        with open(os.path.join(cdir, "settings.json"), "w") as fh:
            json.dump({"hooks": {"PostToolUse": [stale, custom]},
                       "enabledPlugins": {"x": True}}, fh)

        rc = mod.main([target])
        check("installer runs clean", rc == 0, rc)
        with open(os.path.join(cdir, "settings.json")) as fh:
            settings = json.load(fh)
        cmds = flat_commands(settings)

        # PLANTED: the stale plugin-namespace group must be GONE
        check("stale plugin hook pruned", not any("removed_guard" in c for c in cmds), cmds)
        # the custom user hook must SURVIVE
        check("custom user hook preserved", any("my-own-hook.sh" in c for c in cmds), cmds)
        # current guards present (spot-check the newest and an old one)
        check("current test_lock_guard installed",
              any("test_lock_guard.py" in c for c in cmds), cmds)
        check("current weakening guard installed",
              any("test_weakening_guard.py" in c for c in cmds), cmds)
        # commands rewritten to the project namespace (no raw plugin var)
        check("plugin-root var rewritten",
              all("${CLAUDE_PLUGIN_ROOT}" not in c for c in cmds), cmds)
        check("marketplace block dropped", "enabledPlugins" not in settings, settings.keys())

        # idempotence: re-run must not duplicate anything
        before = sorted(cmds)
        mod.main([target])
        with open(os.path.join(cdir, "settings.json")) as fh:
            after = sorted(flat_commands(json.load(fh)))
        check("re-run is idempotent (no duplicates)", before == after,
              (len(before), len(after)))

    test_doctor()

    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


def test_doctor():
    """--doctor: version-skew between canonical plugin, vendored copy, and plugin cache
    must be LOUD (origin: a live setup silently ran v1.1.0 plugin hooks alongside v1.5-era
    vendored hooks — duplicate, version-skewed enforcement for weeks)."""
    print("\n[doctor version-skew]")
    mod = load_installer()
    with open(os.path.join(REPO, "plugins", "tdd-playbook", ".claude-plugin",
                           "plugin.json")) as fh:
        canonical = json.load(fh)["version"]

    with tempfile.TemporaryDirectory() as target, tempfile.TemporaryDirectory() as cache:
        os.environ["TDD_PLAYBOOK_PLUGIN_CACHE"] = cache
        try:
            # vendor writes the version stamp
            mod.main([target])
            stamp = os.path.join(target, ".claude", ".tdd-playbook-version")
            check("vendor writes version stamp", os.path.isfile(stamp), stamp)
            with open(stamp) as fh:
                check("stamp carries the canonical version",
                      fh.read().strip() == canonical, canonical)

            # matching cache + fresh vendor -> clean bill
            vdir = os.path.join(cache, "some-marketplace", "tdd-playbook", canonical)
            os.makedirs(vdir)
            check("doctor clean -> exit 0", mod.main(["--doctor", target]) == 0)

            # PLANTED: stale vendored stamp -> doctor fails loudly
            with open(stamp, "w") as fh:
                fh.write("0.0.1\n")
            check("doctor catches VENDORED skew (exit 1)",
                  mod.main(["--doctor", target]) == 1)
            with open(stamp, "w") as fh:
                fh.write(canonical + "\n")

            # PLANTED: stale plugin cache (canonical version absent) -> doctor fails loudly
            os.rename(vdir, os.path.join(cache, "some-marketplace", "tdd-playbook", "0.9.0"))
            check("doctor catches PLUGIN CACHE skew (exit 1)",
                  mod.main(["--doctor", target]) == 1)

            # no cache at all (cloud sandbox) -> informational, not a failure
            os.environ["TDD_PLAYBOOK_PLUGIN_CACHE"] = os.path.join(cache, "empty-nope")
            check("doctor with no plugin cache -> exit 0 (vendored-only surface)",
                  mod.main(["--doctor", target]) == 0)

            # non-vendored repo -> informational, not a failure
            with tempfile.TemporaryDirectory() as bare:
                check("doctor on non-vendored repo -> exit 0",
                      mod.main(["--doctor", bare]) == 0)
        finally:
            os.environ.pop("TDD_PLAYBOOK_PLUGIN_CACHE", None)


if __name__ == "__main__":
    main()
