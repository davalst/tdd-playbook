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
import subprocess
import sys
import tempfile
import time

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
    test_vendoring_containment()

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

            # PLANTED (hole 2, 2026-07-28): a standing guard demotion in the settings env
            # block is a persistent invisible kill switch -> doctor fails loudly
            # (cache env still points at the empty dir -> informational, so the ONLY
            # failure signal here is the demotion)
            sp = os.path.join(target, ".claude", "settings.json")
            with open(sp) as fh:
                settings = json.load(fh)
            settings["env"] = {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"}
            with open(sp, "w") as fh:
                json.dump(settings, fh)
            check("doctor catches STANDING DEMOTION in settings env (exit 1)",
                  mod.main(["--doctor", target]) == 1)
            settings.pop("env")
            with open(sp, "w") as fh:
                json.dump(settings, fh)
            check("doctor clean again after demotion removed",
                  mod.main(["--doctor", target]) == 0)

            # PLANTED (H8, live incident 2026-07-28): commits made AFTER the last guard
            # heartbeat mean work happened while the guard layer was dark (plugin disabled
            # user-wide by a mis-click in another repo; a whole day + 3 releases, zero
            # alarms) -> doctor fails loudly. A missing heartbeat is informational only
            # (fresh clones have none — never a false RED).
            def git(*a):
                subprocess.run(["git", "-C", target, *a], capture_output=True, timeout=30)
            git("init", "-q")
            git("config", "user.email", "t@t")
            git("config", "user.name", "t")
            git("add", "-A")
            git("commit", "-qm", "work")
            check("doctor: no heartbeat + commits -> informational, exit 0 (fresh clone)",
                  mod.main(["--doctor", target]) == 0)
            hb = os.path.join(target, ".claude", "playbook-guards-heartbeat")
            with open(hb, "w") as fh:
                fh.write("2026-07-20T00:00:00+00:00\n")
            old = time.time() - 8 * 86400
            os.utime(hb, (old, old))  # heartbeat 8 days older than the commit above
            check("doctor: PLANTED commit newer than heartbeat -> GUARDS DARK, exit 1",
                  mod.main(["--doctor", target]) == 1)
            now = time.time()
            os.utime(hb, (now, now))
            check("doctor: fresh heartbeat -> exit 0 (guards were live)",
                  mod.main(["--doctor", target]) == 0)
        finally:
            os.environ.pop("TDD_PLAYBOOK_PLUGIN_CACHE", None)


def test_vendoring_containment():
    """PLANTED (lift/ratchet D5, R2): calibration/lift data must never reach a vendored
    tree — asserted on the FACT (containment inside PLUGIN), not the directory name (F6:
    a name-based check is literally true while describing something other than what's
    needed). Red-first proof: a deliberately escaping COPY_TREES entry must be DETECTED."""
    print("\n[vendoring containment (R2)]")
    mod = load_installer()
    for src_rel, _dest in mod.COPY_TREES:
        rel = os.path.relpath(os.path.join(mod.PLUGIN, src_rel), mod.PLUGIN)
        check("COPY_TREES contained in PLUGIN: {}".format(src_rel),
              not rel.startswith(".."), rel)

    # calibrate-the-checker: an escaping entry (the way calibration/ COULD ride in) is
    # detected by the same rule — the pin can fail, so it isn't theater
    escaped = os.path.relpath(os.path.join(mod.PLUGIN, "..", "..", "calibration"),
                              mod.PLUGIN)
    check("PLANTED escaping entry ../../calibration is detected",
          escaped.startswith(".."), escaped)

    # behavioral: a real scratch install vendors nothing calibration-shaped
    with tempfile.TemporaryDirectory() as target:
        mod.main([target])
        offenders = []
        for root, _dirs, files in os.walk(os.path.join(target, ".claude")):
            for f in files:
                p = os.path.join(root, f)
                if "calibration" in os.path.relpath(p, target).lower():
                    offenders.append(p)
        check("scratch install: no calibration-shaped path vendored", offenders == [],
              offenders)


if __name__ == "__main__":
    main()
