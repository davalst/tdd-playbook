#!/usr/bin/env python3
"""Planted-input calibration for scripts/install_into_repo.py hook RECONCILIATION.

The old merge was append-only: a hook the plugin removed/renamed stayed in downstream
settings.json forever (drift). Planted here: a STALE plugin-namespace group must be pruned,
a CUSTOM user group must survive, current groups land exactly once, and re-runs are
idempotent. Self-contained, no pytest. Run: python3 tests/test_installer.py
"""
import ast
import contextlib
import importlib.util
import io
import json
import os
import re
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
        check("portable host contract installed beside every adapter",
              os.path.isfile(os.path.join(cdir, "bin", "host_contract.py")))
        # commands rewritten to the project namespace (no raw plugin var)
        check("plugin-root var rewritten",
              all("${CLAUDE_PLUGIN_ROOT}" not in c for c in cmds), cmds)
        check("marketplace block dropped", "enabledPlugins" not in settings, settings.keys())
        with open(os.path.join(cdir, ".gitignore")) as fh:
            ignores = set(fh.read().splitlines())
        check("one-shot legacy migration marker is ignored downstream",
              "tdd-lock.json.migrated" in ignores, sorted(ignores))

        # idempotence: re-run must not duplicate anything
        before = sorted(cmds)
        mod.main([target])
        with open(os.path.join(cdir, "settings.json")) as fh:
            after = sorted(flat_commands(json.load(fh)))
        check("re-run is idempotent (no duplicates)", before == after,
              (len(before), len(after)))

    test_doctor()
    test_doctor_classifies_overrides_against_each_guards_default()
    test_codex_install_preserves_user_config()
    test_vendoring_containment()
    test_vendored_skill_equality()
    test_release_version_identity()
    test_no_script_creates_a_release_tag()
    test_codex_registered_scripts_are_vendored()
    test_doctor_sees_break_glass_as_a_standing_demotion()

    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


def test_codex_install_preserves_user_config():
    """Codex is a separate adapter surface: reconcile only our namespace and never touch
    Claude state or a user's unrelated Codex hook groups."""
    print("\n[codex install/reconciliation]")
    mod = load_installer()
    with tempfile.TemporaryDirectory() as target:
        codex_dir = os.path.join(target, ".codex")
        os.makedirs(codex_dir)
        stale = {"matcher": "Bash", "hooks": [{
            "type": "command",
            "command": "python3 .codex/tdd-playbook/hooks/removed_guard.py"}]}
        custom = {"matcher": "Bash", "hooks": [{
            "type": "command", "command": "./scripts/my-codex-hook.sh",
            "timeout": 7}]}
        initial = {"description": "keep me", "hooks": {"PreToolUse": [stale, custom]}}
        with open(os.path.join(codex_dir, "hooks.json"), "w") as fh:
            json.dump(initial, fh, indent=2)
            fh.write("\n")

        rc = mod.main(["--host", "codex", target])
        check("Codex installer runs clean", rc == 0, rc)
        check("Codex-only install does not create or conflate .claude state",
              not os.path.exists(os.path.join(target, ".claude")))
        with open(os.path.join(codex_dir, "hooks.json")) as fh:
            installed = json.load(fh)
        commands = flat_commands(installed)
        groups = installed.get("hooks", {}).get("PreToolUse", [])
        check("Codex installer preserves unrelated top-level config",
              installed.get("description") == "keep me", installed)
        check("Codex installer preserves custom hook group semantically",
              custom in groups and any("my-codex-hook.sh" in cmd for cmd in commands), groups)
        check("Codex installer prunes stale adapter-owned hook entries",
              not any("removed_guard.py" in cmd for cmd in commands), commands)
        check("Codex installer wires TEST-LOCK for both native routes",
              sum("pre_tool_test_lock.py" in cmd for cmd in commands) == 2, commands)
        check("Codex runtime carries the shared contract and thin adapter",
              os.path.isfile(os.path.join(codex_dir, "tdd-playbook", "bin",
                                          "host_contract.py"))
              and os.path.isfile(os.path.join(codex_dir, "tdd-playbook", "adapters",
                                              "codex", "pre_tool_test_lock.py")))
        check("Codex package does not vendor undiscoverable Claude command/agent islands",
              not os.path.exists(os.path.join(codex_dir, "tdd-playbook", "commands"))
              and not os.path.exists(os.path.join(codex_dir, "tdd-playbook", "agents")))
        stamp = os.path.join(codex_dir, ".tdd-playbook-version")
        check("Codex package has its own version stamp", os.path.isfile(stamp), stamp)

        before = installed
        second = mod.main(["--host", "codex", target])
        with open(os.path.join(codex_dir, "hooks.json")) as fh:
            after = json.load(fh)
        check("Codex reinstall is idempotent and preserves user config",
              second == 0 and before == after, (second, before, after))

    with tempfile.TemporaryDirectory() as target:
        mod.main([target])
        check("legacy default remains Claude-only for compatibility",
              os.path.isdir(os.path.join(target, ".claude"))
              and not os.path.exists(os.path.join(target, ".codex")))


def _rewritten_canonical(mod):
    with open(os.path.join(mod.PLUGIN, "skills", "tdd-playbook", "SKILL.md")) as fh:
        return fh.read().replace(mod.PLUGIN_ROOT_VAR, mod.PROJECT_ROOT_VAR)


def test_vendored_skill_equality():
    """v1.24 (D11): vendored SKILL == canonical modulo the ${CLAUDE_PLUGIN_ROOT} rewrite —
    ONE rewrite-aware equality assertion that subsumes every per-marker content pin, now
    and for every future doctrine addition (no per-needle treadmill in this suite)."""
    print("\n[test_vendored_skill_equality]")
    mod = load_installer()
    with tempfile.TemporaryDirectory() as target:
        rc = mod.main([target])
        vendored_path = os.path.join(target, ".claude", "skills", "tdd-playbook", "SKILL.md")
        check("vendored SKILL present", os.path.isfile(vendored_path), vendored_path)
        with open(vendored_path) as fh:
            vendored = fh.read()
        expected = _rewritten_canonical(mod)
        check("vendored SKILL == canonical modulo the plugin-root rewrite",
              vendored == expected,
              "first divergence at char {}".format(next(
                  (i for i, (a, b) in enumerate(zip(vendored, expected)) if a != b),
                  min(len(vendored), len(expected)))))

        # PLANTED: a tampered vendored copy (a §6c heading stripped downstream) must be
        # DETECTABLE by the same comparison — the pin can fail (§13 calibrate-the-checker)
        tampered = vendored.replace("## 6c. Dataflow Liveness", "## (section removed)")
        check("planted: stripped-§6c vendored copy detected by the equality check",
              tampered != expected and "## 6c. Dataflow Liveness" in expected,
              "plant did not change the text — is §6c in the canonical SKILL?")


def test_release_version_identity():
    """A release has one identity across the marketplace, plugin, and both host adapters."""
    print("\n[release version identity]")
    paths = {
        "marketplace": os.path.join(REPO, ".claude-plugin", "marketplace.json"),
        "plugin": os.path.join(REPO, "plugins", "tdd-playbook", ".claude-plugin",
                               "plugin.json"),
        "claude-adapter": os.path.join(REPO, "plugins", "tdd-playbook", "adapters",
                                       "claude", "adapter.json"),
        "codex-adapter": os.path.join(REPO, "plugins", "tdd-playbook", "adapters",
                                      "codex", "adapter.json"),
    }
    loaded = {}
    for name, path in paths.items():
        with open(path) as fh:
            loaded[name] = json.load(fh)
    versions = {
        "marketplace": loaded["marketplace"]["plugins"][0]["version"],
        "plugin": loaded["plugin"]["version"],
        "claude-adapter": loaded["claude-adapter"]["adapter_version"],
        "codex-adapter": loaded["codex-adapter"]["adapter_version"],
    }
    check("release identity: marketplace, plugin, and adapters agree",
          len(set(versions.values())) == 1, versions)

    # PLANTED: freeze the exact skew caught while preparing v1.31.0 — a host adapter left at
    # the previous release must make the shared identity predicate fail.
    planted = dict(versions)
    planted["codex-adapter"] = "previous-release-plant"
    check("release identity: PLANTED stale host adapter is detected",
          len(set(planted.values())) != 1, planted)


def test_doctor_classifies_overrides_against_each_guards_default():
    """A standing override is a DEMOTION only if it is weaker than what the guard ships.

    Origin 2026-08-17: doctor called every guard control var a "STANDING DEMOTION … H-class
    kill switch". Five guards ship `off` since v1.32.0, so this repo's own
    TDD_PLAYBOOK_HOOK_EXITCODE=warn — the documented way to turn a retired guard back ON — was
    reported as a kill switch on every release run of that session. A warning that fires on a
    correct configuration teaches the operator to skim the one that matters.

    Both directions, over the SAME mechanism, so this cannot regress to flagging nothing
    either: an off-by-default guard raised to warn must NOT set exit 1; a block-by-default
    guard lowered to warn MUST; BREAK_GLASS MUST regardless of value; and an unrecognised hook
    name MUST (fail toward flagging)."""
    print("\n[doctor override classification]")
    mod = load_installer()
    sys.path.insert(0, os.path.join(REPO, "plugins", "tdd-playbook", "hooks", "scripts"))
    import _common

    # unit: the contract lives in _common, keyed off its own defaults table
    cases = [
        ("TDD_PLAYBOOK_HOOK_EXITCODE", "warn", "enablement"),   # ships off
        ("TDD_PLAYBOOK_HOOK_TESTLOCK", "warn", "demotion"),     # ships block
        ("TDD_PLAYBOOK_HOOK_TESTLOCK", "off", "demotion"),
        ("TDD_PLAYBOOK_HOOK_TESTLOCK", "block", "noop"),
        ("TDD_PLAYBOOK_HOOK_FIXTUREGUARD", "block", "enablement"),  # ships warn
        ("TDD_PLAYBOOK_HOOK_FIXTUREGUARD", "off", "demotion"),
        ("TDD_PLAYBOOK_BREAK_GLASS", "1", "demotion"),
        ("TDD_PLAYBOOK_HOOK_NOSUCHGUARD", "warn", "unknown"),   # fail toward flagging
        ("TDD_PLAYBOOK_HOOK_EXITCODE", "nonsense", "unknown"),
    ]
    for key, val, want in cases:
        got = _common.guard_override_effect(key, val)
        check("classify {}={} -> {}".format(key, val, want), got == want, got)

    # end-to-end through the real doctor, since a classifier nobody consults is inert
    with tempfile.TemporaryDirectory() as target, tempfile.TemporaryDirectory() as cache:
        os.environ["TDD_PLAYBOOK_PLUGIN_CACHE"] = cache
        try:
            mod.main([target])
            with open(os.path.join(REPO, "plugins", "tdd-playbook", ".claude-plugin",
                                   "plugin.json")) as fh:
                canonical = json.load(fh)["version"]
            os.makedirs(os.path.join(cache, "mkt", "tdd-playbook", canonical))
            settings = os.path.join(target, ".claude", "settings.local.json")

            def doctor_with(env):
                with open(settings, "w") as fh:
                    json.dump({"env": env}, fh)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = mod.main(["--doctor", target])
                return code, buf.getvalue()

            code, out = doctor_with({"TDD_PLAYBOOK_HOOK_EXITCODE": "warn"})
            check("opt-in enablement is NOT a demotion (exit 0)", code == 0, out)
            check("and it is still REPORTED, not silent", "guard opt-in" in out, out)
            check("the alarming wording is absent", "STANDING DEMOTION" not in out, out)

            code, out = doctor_with({"TDD_PLAYBOOK_HOOK_TESTLOCK": "warn"})
            check("a real demotion still fails (exit 1)", code == 1, out)
            check("a real demotion is named", "STANDING DEMOTION" in out, out)
        finally:
            os.environ.pop("TDD_PLAYBOOK_PLUGIN_CACHE", None)


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

            # PLANTED (REL-META-1, v1.31.0): Codex has its own runtime/stamp. A stale
            # Codex install must fail doctor even when the Claude stamp is current.
            mod.main(["--host", "codex", target])
            codex_stamp = os.path.join(target, ".codex", ".tdd-playbook-version")
            with open(codex_stamp, "w") as fh:
                fh.write("0.0.1\n")
            check("doctor catches stale Codex vendored stamp (exit 1)",
                  mod.main(["--doctor", target]) == 1)
            with open(codex_stamp, "w") as fh:
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


# --------------------------------------------------------- release authority (v1.32.0)
# The roster is DERIVED from `git ls-files`, never hand-listed. An earlier draft hardcoded
# ("scripts", "plugins/tdd-playbook", "calibration") — the FIFTH hand-maintained "where the
# code lives" roster in this repo, and one that already disagreed with dataflow-sweeps.json.
# It was complete on the day it was written and blind by construction to anything added
# later: a `.github/workflows/release.yml` with a GITHUB_TOKEN can create and push a tag,
# and would have sat outside both the roots AND the .py/.sh filter. Deriving it makes the
# README claim true by construction instead of true-for-now.
#
# tests/ is scanned too: a tagging path hidden in a test helper is the same hole. There is
# no exemption hatch (§6a: exemptions are for internals, never a darkness hatch) — the
# plants are assembled at RUNTIME so this file contains no literal needing an ignore entry.
_SCAN_EXT = (".py", ".sh", ".yml", ".yaml", ".bash", ".zsh")

# Tag INSPECTION is legitimate and common here (`git describe --tags --abbrev=0` supplies
# the gate's own baseline-rev in gate_runner, review_ledger and test_harness). Only
# CREATION and PUSH are forbidden.
#
# Python is parsed, not grepped. The first draft was a line regex: it found the two real
# sites AND four lines of this file's own prose, then `words.index("tag")` — a line of the
# scanner itself. That is §1's documented proxy failure ("a grep matches your own docstring
# — parse it"). Both false positives are frozen as ALLOWED rows below.
_READ_ONLY_TAG_FLAGS = ("-l", "--list", "-d", "--delete", "-n", "-v", "--verify", "--contains")
# `git [-C path ...] tag` — the SUBCOMMAND position, not "git" and "tag" loose on one line.
# The loose form matched check_scoreboard_integrity.py's own --help prose ("git rev of the
# trusted baseline ... the previous release tag"), which is the same parse-don't-grep lesson
# a third time, so the subcommand anchor is the fix rather than an exemption.
_GIT_ = r"\bgit\b(?:\s+-[A-Za-z-]+(?:[= ]\S+)?)*\s+"
_SHELL_TAG = re.compile(
    _GIT_ + r"tag\b(?!\s*(?:-l\b|--list\b|-d\b|--delete\b|-n|-v\b))"
    r"|" + _GIT_ + r"update-ref\b[^\n]*refs/tags"
    r"|\bgh\b[^\n]*\brelease\s+create\b"
    r"|\bgh\b[^\n]*\bapi\b[^\n]*refs/tags")
_SHELL_PUSH_TAG = re.compile(
    _GIT_ + r"push\b[^\n]*(?:--tags\b|refs/tags|\sv\d+\.\d+)")
_TAG_NAMES = ("tag", "tagname", "tag_name", "tagref", "version_tag")
# word-ish "is this a git invocation" for ARGV words
_GITISH = re.compile(r"\bgit\b|\bgh\b")
# ...and for a CALLEE NAME, where `_git` / `run_git` / `_git_text` are the house helpers.
# `\bgit\b` cannot match `_git` because underscore is a word character — the bug that made
# every _git(...) plant fail on the first pass at this fix.
_CALLEE_GITISH = re.compile(r"git|(?:^|_)gh(?:$|_)")


def _argv_creates_tag(words, has_tag_var):
    """Given the string words of one argv-ish sequence, does it create/push a tag?"""
    if not (any(w == "git" or w == "gh" for w in words)
            or any(_GITISH.search(w) for w in words)):
        return None
    for w in words:
        if _SHELL_TAG.search(w) or _SHELL_PUSH_TAG.search(w):
            return "shell tag command: " + w[:60]
    if "tag" in words:
        rest = words[words.index("tag") + 1:]
        if not rest or not rest[0].startswith(_READ_ONLY_TAG_FLAGS):
            return "creates a tag: " + " ".join(words[:6])
    if "update-ref" in words and any(w.startswith("refs/tags") for w in words):
        return "writes a tag ref: " + " ".join(words[:6])
    if "release" in words and "create" in words:
        return "creates a release (implies a tag): " + " ".join(words[:6])
    if "push" in words and (
            has_tag_var
            or any(w.startswith("--tags") or "refs/tags" in w for w in words)
            or any(re.fullmatch(r"v\d+\.\d+(\.\d+)?", w) for w in words)):
        return "pushes a tag: " + " ".join(words[:6])
    return None


def _tag_creation_hits(source):
    """(lineno, why) for every construct in `source` that creates or pushes a git tag.

    Pure function on text so the plants below need no file on disk. Non-Python callers go
    to _tag_creation_hits_text."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _tag_creation_hits_text(source)
    hits, seen = [], set()

    def add(lineno, why):
        if lineno not in seen:
            seen.add(lineno)
            hits.append((lineno, why))

    for node in ast.walk(tree):
        # (a) a list/tuple LITERAL anywhere — catches `cmd = ["git","tag",...]` handed to a
        #     runner on a later line, which the call-arg-only draft missed entirely.
        if isinstance(node, (ast.List, ast.Tuple)):
            words = [e.value.strip() for e in node.elts
                     if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            why = _argv_creates_tag(words, False)
            if why:
                add(node.lineno, why)
            continue
        if not isinstance(node, ast.Call):
            continue
        # (b) a CALL: flatten literal string args (incl. one level of list/tuple) and note
        #     any argument that is a variable named like a tag.
        words, has_tag_var = [], False
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            items = arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg]
            for el in items:
                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                    words.append(el.value.strip())
                elif isinstance(el, ast.Name) and el.id in _TAG_NAMES:
                    has_tag_var = True
                elif isinstance(el, ast.JoinedStr):
                    words.append("".join(v.value for v in el.values
                                         if isinstance(v, ast.Constant)
                                         and isinstance(v.value, str)))
        # The construct must be git-ish. Without this, `words.index("tag")` — a line of
        # this scanner — reads as a tag creation (the second self-inflicted false positive).
        # It must test the CONTENT of each word, not exact membership of the token "git":
        # a shell string is ONE word ("git tag -a v1"), so an exact-membership test skipped
        # every shell form BEFORE _SHELL_TAG could see it, including the example written in
        # this module's own comment. Both adversaries found it independently.
        callee = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        callee_gitish = bool(_CALLEE_GITISH.search(callee.lower()))
        if not callee_gitish and not any(_GITISH.search(w) for w in words):
            continue
        why = _argv_creates_tag(words, has_tag_var)
        if why is None and callee_gitish:
            # a git-wrapper helper: _git("tag", "-a", ...) carries no literal "git" word
            why = _argv_creates_tag(words + ["git"], has_tag_var)
        if why:
            add(node.lineno, why)
    return hits


def _load_tag_guard():
    """The SHIPPED classifier. test_installer used to keep its own copy of the tag policy and
    the two had already drifted -- `--verify`/`--contains` were read-only in the guard and
    FLAGGED here, and only the guard knew about release ACTIONS. One classifier, two call
    sites; this suite's job is to calibrate the thing that ships, not a lookalike."""
    path = os.path.join(REPO, "plugins", "tdd-playbook", "hooks", "scripts", "tag_guard.py")
    spec = importlib.util.spec_from_file_location("tag_guard", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tag_creation_hits_text(source):
    """Line scan for shell scripts and YAML, which have no Python AST and no docstrings.

    Delegates to the shipped guard's regexes so shell policy has ONE definition, and adds the
    workflow-authority rules for CI, where a tag is created by an ACTION with no git verb."""
    guard = _load_tag_guard()
    hits = []
    for n, raw in enumerate(source.splitlines(), 1):
        if raw.strip().startswith("#"):
            continue
        if guard._TAG_READ_OR_DELETE.search(raw):
            continue
        if (guard._TAG_CREATE.search(raw) or guard._TAG_REF_WRITE.search(raw)
                or guard._TAG_PUSH.search(raw) or guard._GH_RELEASE.search(raw)):
            hits.append((n, raw.strip()))
    for why in guard.workflow_findings(source):
        hits.append((0, why))
    return hits


def _yaml_ok(text):
    """YAML validity, without adding a dependency (the plugin is stdlib-only by invariant).

    SKILL.md §10 records the incident this guards: an unquoted colon in a step `name:`
    silently invalidates a whole workflow, and an invalid workflow produces NO check run --
    which reads to a human exactly like "CI hasn't finished yet." The debt text claimed the
    file was "YAML-validated"; that was a one-time manual act with no pin."""
    try:
        import yaml
    except ImportError:
        # stdlib fallback: structural sanity that catches the documented failure shape
        return ("jobs:" in text and "runs-on:" in text
                and not re.search(r"^\s+name:\s+[^\"'\s][^\n]*:\s", text, re.M))
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    return isinstance(doc, dict) and "jobs" in doc


def _tracked_scannable(repo):
    """The roster, DERIVED. Falls back to a walk only if git is unavailable."""
    r = subprocess.run(["git", "-C", repo, "ls-files", "-z"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        return sorted(f for f in r.stdout.split("\0")
                      if f and f.endswith(_SCAN_EXT))
    out = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
        out += [os.path.relpath(os.path.join(root, f), repo)
                for f in files if f.endswith(_SCAN_EXT)]
    return sorted(out)


def test_codex_registered_scripts_are_vendored():
    """D-D (review-as-judgment-surface plan, 2026-08-14): CODEX_COPY_FILES is the one
    real hand-maintained roster of the deleted D0's class — two files that exist only
    because the registered adapter script imports them. So the parity is TRANSITIVE:
    every script the Codex adapter's hooks.json registers must resolve under
    CODEX_COPY_TREES ∪ CODEX_COPY_FILES, and so must its repo-local imports (AST-parsed,
    never grepped — §12). Dropping either roster entry strands the vendored hook at
    import time on a host this repo cannot see."""
    mod = load_installer()
    plugin = os.path.join(REPO, "plugins", "tdd-playbook")
    hp_spec = importlib.util.spec_from_file_location(
        "host_parity", os.path.join(plugin, "bin", "host_parity.py"))
    host_parity = importlib.util.module_from_spec(hp_spec)
    hp_spec.loader.exec_module(host_parity)
    registered = host_parity.registered_scripts(
        os.path.join(plugin, "adapters", "codex", "hooks.json"))
    check("vacuity: the codex adapter registers at least one script (§4a)",
          len(registered) >= 1, registered)

    tree_prefixes = tuple(src + "/" for src, _dest in mod.CODEX_COPY_TREES)
    file_srcs = {src for src, _dest in mod.CODEX_COPY_FILES}

    def vendored(rel, files=file_srcs):
        return rel in files or rel.startswith(tree_prefixes)

    def local_imports(rel):
        with open(os.path.join(plugin, rel)) as fh:
            tree = ast.parse(fh.read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module)
        found = set()
        for name in names:
            for shape in ("bin/{}.py", "hooks/scripts/{}.py", "adapters/codex/{}.py"):
                candidate = shape.format(name.replace(".", "/"))
                if os.path.isfile(os.path.join(plugin, candidate)):
                    found.add(candidate)
        return found

    dependencies = set()
    for rel in sorted(registered):
        check("registered codex script is vendored: " + rel, vendored(rel),
              (tree_prefixes, sorted(file_srcs)))
        for dep in sorted(local_imports(rel)):
            dependencies.add(dep)
            check("...and its repo-local import is vendored: " + dep, vendored(dep))
    check("the CODEX_COPY_FILES roster is LOAD-BEARING (some dependency rides it, "
          "not the trees)", any(dep in file_srcs for dep in dependencies),
          sorted(dependencies))

    # PLANTED (red-first, frozen): dropping test_lock_guard.py from CODEX_COPY_FILES
    # must be caught — the exact drift D0 was reaching for.
    pruned = {src for src in file_srcs if "test_lock_guard" not in src}
    check("PLANTED: dropping test_lock_guard from CODEX_COPY_FILES is caught",
          any(not vendored(dep, pruned) for dep in dependencies), sorted(dependencies))


def test_doctor_sees_break_glass_as_a_standing_demotion():
    """v1.32.0: the doctor's STANDING DEMOTION check keyed on
    `startswith("TDD_PLAYBOOK_HOOK")`, and TDD_PLAYBOOK_BREAK_GLASS does not carry that
    prefix — so the WIDEST switch (it demotes all four blocking gates at once) was the one
    the check could not see, while a single per-hook demotion was reported. That is the
    2026-07-28 'hole 2' reopened by a wider knob: the proxy (a name prefix) drifted from the
    fact (an env var that weakens the guard layer). The predicate now lives in _common,
    which owns the env contract."""
    print("\n[doctor: break-glass is a standing demotion]")
    mod = load_installer()
    check("doctor delegates to the env-contract owner, not a name prefix",
          mod._is_guard_control_var("TDD_PLAYBOOK_BREAK_GLASS"), "break-glass not recognised")
    check("...and still recognises the per-hook demotions it was written for",
          mod._is_guard_control_var("TDD_PLAYBOOK_HOOK_TESTWEAKEN"))
    check("...and does not sweep up unrelated env vars",
          not mod._is_guard_control_var("PATH")
          and not mod._is_guard_control_var("TDD_PLAYBOOK_YIELD_LOG"))

    # behavioural: a standing break-glass in committed settings must be REPORTED
    with tempfile.TemporaryDirectory() as target:
        cdir = os.path.join(target, ".claude")
        os.makedirs(cdir)
        with open(os.path.join(cdir, "settings.json"), "w") as fh:
            json.dump({"env": {"TDD_PLAYBOOK_BREAK_GLASS": "i just dislike being blocked"}}, fh)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod.main(["--doctor", target])
        out = buf.getvalue()
        check("PLANTED standing break-glass is reported as a STANDING DEMOTION",
              "STANDING DEMOTION" in out and "BREAK_GLASS" in out, (rc, out[:300]))
        check("...and the doctor fails closed on it", rc == 1, rc)


def test_no_script_creates_a_release_tag():
    """v1.32.0 owner-control: the CIVerd verdict is GONE from the release path, so what
    authorizes a release is David creating the tag. That is only true while no in-repo
    AUTOMATION can create one. Two halves, and this suite is honest about owning one:

      - this scan stops a committed SCRIPT (or CI workflow) from tagging;
      - hooks/scripts/tag_guard.py stops the SESSION from tagging at the Bash seam;
      - a GitHub `v*` ruleset would stop everything else, and is dated debt on the
        `release-tag-authority` capability until armed.

    Red-first fact, not ritual: before scripts/release_verify.py was deleted this scan
    returned its `_git("tag", "-a", ...)` at :100 and `_git("push", "origin", tag)` at :104
    — the only two tag-creation sites in the tree — and nothing else."""
    print("\n[release authority: no script creates a tag]")

    # (1) calibrate-the-checker FIRST — a scanner that cannot fire proves nothing (§13).
    #     Assembled at runtime so these literals never appear in this file's own source.
    #     Every PYTHON plant below is VALID PYTHON on purpose: an earlier plant set used
    #     bare shell strings, which raise SyntaxError and fall through to the .sh text
    #     scanner — so the branch they were supposed to calibrate had none, and eight
    #     ordinary forms were missed by a check reported as green.
    _t = "t" + "ag"
    py_plants = {
        "argv create": '_git("' + _t + '", "-a", name, sha)',
        "subprocess argv": 'subprocess.run(["git", "' + _t + '", "-a", "v1", "-m", "x"])',
        "shell string": 'subprocess.run("git ' + _t + ' -a v1 -m x", shell=True)',
        "os.system": 'os.system("git ' + _t + ' -a v1.0.0 && git push origin v1.0.0")',
        "variable argv": 'cmd = ["git", "' + _t + '", "-a", "v1"]\nsubprocess.run(cmd)',
        "sh -c": 'subprocess.run(["sh", "-c", "git ' + _t + ' -a v1 -m x"])',
        "push --tags": 'subprocess.run(["git", "push", "origin", "--' + _t + 's"])',
        "push literal tag": 'subprocess.run(["git", "push", "origin", "v1.0.0"])',
        "argv push var": '_git("push", "origin", ' + _t + ')',
        "update-ref": '_git("update-ref", "refs/' + _t + 's/v1", "HEAD")',
        "gh release": 'subprocess.run(["gh", "release", "create", "v1.0.0"])',
        "f-string tag": 'subprocess.run(["git", "' + _t + '", f"v{ver}"])',
    }
    for label, text in py_plants.items():
        check("PLANTED {} is detected".format(label), bool(_tag_creation_hits(text)), text)
    sh_plants = {
        "shell script": "git " + _t + " -a v9.9.9 -m 'release'",
        "workflow step": "  run: git " + _t + " -a v1 && git push origin --" + _t + "s",
    }
    for label, text in sh_plants.items():
        check("PLANTED {} is detected".format(label),
              bool(_tag_creation_hits_text(text)), text)

    # (2) and it must ALLOW what it claims to allow — the other direction of the
    #     two-directional calibration table (§13). Both halves have bitten here.
    allowed = {
        "describe --tags": '_git_text("describe", "--' + _t + 's", "--abbrev=0")',
        "tag -l": '_git("' + _t + '", "-l", "v1.*")',
        "branch push": '_git(root, "push", "origin", "main")',
        "arg parsing": 'ap.add_argument("--no-' + _t + '", help="verify only")',
        # the regression that produced the AST rewrite: prose is not an action
        "docstring mentioning the rule":
            'def f():\n    """we never run git ' + _t + ' -a here."""\n    return 1',
        "comment mentioning the rule": "# never call git " + _t + " -a from a script",
        # the second self-inflicted false positive: a non-git call taking "tag"
        "non-git call with a tag argument": 'i = words.index("' + _t + '")',
        "dict lookup": 'v = row.get("' + _t + '", None)',
        "tag-shaped list that is not git": 'FIELDS = ["' + _t + '", "owner", "expires"]',
    }
    for label, text in allowed.items():
        check("ALLOWED {} is not flagged".format(label),
              not _tag_creation_hits(text), text)

    # (3) the live scan — the assertion that actually guards the release path
    offenders, roster = [], _tracked_scannable(REPO)
    for rel in roster:
        path = os.path.join(REPO, rel)
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        finder = _tag_creation_hits if rel.endswith(".py") else _tag_creation_hits_text
        for lineno, why in finder(src):
            offenders.append("{}:{}: {}".format(rel, lineno, why[:90]))

    # denominator, never a bare green (§12): a result states what it covered
    check("no tracked script or workflow creates or pushes a release tag "
          "(scanned {} tracked file(s))".format(len(roster)),
          offenders == [], "; ".join(offenders))
    check("the scan was not vacuous (§4a): the derived roster is non-trivial",
          len(roster) > 50, len(roster))
    # SCOPE, asserted rather than assumed (§12). The roster is derived, so "CI is covered"
    # must be checked against something the derivation cannot silently drop. A GitHub
    # workflow runs with a GITHUB_TOKEN and can create and push a tag; the first draft of
    # this scanner hardcoded three source roots and would have been blind to every one.
    workflows = [r for r in roster if r.startswith(".github/workflows/")]
    check("CI workflows are IN the derived roster (a tagging workflow cannot hide there)",
          bool(workflows), roster[:5])
    check("workflow files are scannable by extension, not just present in git",
          all(w.endswith((".yml", ".yaml")) for w in workflows), workflows)

    # (4) the CI job's CONTENT. Everything above proves the workflow creates no tag; none of
    # it proves the workflow still RUNS THE GATE. `run: sh scripts/civerd_gate.sh` -> `run:
    # echo ok` is a one-line diff that leaves this whole suite green while the check mark
    # goes green forever and means nothing -- and CLAUDE.md tells David to read that mark
    # before tagging. This repo has the incident already: 2026-07-28, "the prose loop and the
    # engine's gate command silently diverged and calibration/'s 110 checks never ran in the
    # gate." The deleted test_plant_target_handoff pinned exactly this for the OLD external
    # runner; the pin moves here rather than disappearing with it.
    guard = _load_tag_guard()
    for rel in workflows:
        with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
            wf = fh.read()
        check("CI: {} parses as YAML".format(rel), _yaml_ok(wf), rel)
        check("CI: {} invokes the blessed entrypoint".format(rel),
              re.search(r"sh\s+scripts/civerd_gate\.sh", wf) is not None, rel)
        # `affected` is explicitly NON-AUTHORIZING; an argument would quietly narrow CI to
        # the diagnostic subset while still looking like a full gate run.
        check("CI: {} runs the gate with NO argument (affected mode is non-authorizing)"
              .format(rel),
              re.search(r"sh\s+scripts/civerd_gate\.sh\s*(?:\n|$)", wf) is not None, rel)
        check("CI: {} does not pipe the gate (a piped $? is tail's, §4a)".format(rel),
              not re.search(r"civerd_gate\.sh[^\n]*\|(?!\|)", wf), rel)
        check("CI: {} holds no ref-write authority".format(rel),
              not guard.workflow_findings(wf), guard.workflow_findings(wf))

    # calibrate-the-checker: each CI pin must be able to FAIL (§13). Mutate the real file in
    # memory and require every rule to fire.
    if workflows:
        with open(os.path.join(REPO, workflows[0]), encoding="utf-8") as fh:
            real = fh.read()
        _g = "civerd_gate.sh"
        mutants = {
            "gate call replaced": real.replace("sh scripts/" + _g, "echo ok"),
            "narrowed to affected": real.replace("sh scripts/" + _g,
                                                 "sh scripts/" + _g + " affected"),
            "gate piped": real.replace("sh scripts/" + _g, "sh scripts/" + _g + " | tail -2"),
            "write permission": real.replace("contents: read", "contents: write"),
            "release action added": real + "\n      - uses: softprops/action-gh-release@x\n",
        }
        checks = {
            "gate call replaced": lambda t: re.search(r"sh\s+scripts/civerd_gate\.sh", t) is None,
            "narrowed to affected":
                lambda t: re.search(r"sh\s+scripts/civerd_gate\.sh\s*(?:\n|$)", t) is None,
            "gate piped": lambda t: bool(re.search(r"civerd_gate\.sh[^\n]*\|(?!\|)", t)),
            "write permission": lambda t: bool(guard.workflow_findings(t)),
            "release action added": lambda t: bool(guard.workflow_findings(t)),
        }
        for label, text in mutants.items():
            check("PLANTED CI mutation is detected: " + label, checks[label](text), label)


if __name__ == "__main__":
    main()
