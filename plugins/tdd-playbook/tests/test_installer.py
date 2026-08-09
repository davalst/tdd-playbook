#!/usr/bin/env python3
"""Planted-input calibration for scripts/install_into_repo.py hook RECONCILIATION.

The old merge was append-only: a hook the plugin removed/renamed stayed in downstream
settings.json forever (drift). Planted here: a STALE plugin-namespace group must be pruned,
a CUSTOM user group must survive, current groups land exactly once, and re-runs are
idempotent. Self-contained, no pytest. Run: python3 tests/test_installer.py
"""
import ast
import importlib.util
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
    test_codex_install_preserves_user_config()
    test_vendoring_containment()
    test_vendored_skill_equality()
    test_release_version_identity()
    test_no_script_creates_a_release_tag()

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
# Roots scanned for tag-creation. tests/ is INCLUDED on purpose: a tagging path hidden in
# a test helper is the same hole. No exemption hatch exists (§6a: exemptions are for
# internals, never a darkness hatch) — the plants below are assembled at RUNTIME so this
# file never contains a literal the scanner would have to be told to ignore.
_SCAN_ROOTS = ("scripts", "plugins/tdd-playbook", "calibration")
_SCAN_EXT = (".py", ".sh")

# Tag INSPECTION is legitimate and common here (`git describe --tags --abbrev=0` picks the
# gate's baseline-rev in gate_runner, review_ledger and test_harness). Only tag CREATION
# and tag PUSH are forbidden.
#
# This scans the AST, not the text, and the difference is load-bearing rather than
# stylistic. The first draft of this check was a line regex; it correctly found
# release_verify.py's two sites AND flagged four lines of THIS file's own prose — a
# docstring describing the rule, and a check() message naming it. That is §1's documented
# proxy failure verbatim ("a grep matches your own docstring — parse it"), and the tempting
# repair (exempt this file) is the darkness hatch §6a forbids. So: only a CALL creates a
# tag. Prose that mentions one is prose.
_READ_ONLY_TAG_FLAGS = ("-l", "--list", "-d", "--delete", "-n", "-v", "--verify", "--contains")
# a shell string handed to a call — `subprocess.run("git tag -a v1", shell=True)`. Docstrings
# are ast.Expr statements, never call arguments, so they cannot reach this.
_SHELL_TAG = re.compile(r"\bgit\s+tag\b(?!\s*(?:-l\b|--list\b|-d\b|--delete\b|-n|-v\b))")
_SHELL_PUSH_TAG = re.compile(r"\bgit\s+push\b[^\n]*(?:--tags\b|refs/tags)")
_TAG_NAMES = ("tag", "tagname", "tag_name", "tagref")


def _tag_creation_hits(source):
    """(lineno, why) for every CALL in `source` that creates or pushes a git tag.

    Pure function on text so the planted twins below need no file on disk. Non-Python
    (.sh) callers pass through _tag_creation_hits_text instead."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _tag_creation_hits_text(source)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        words, has_tag_var = [], False
        for arg in node.args:
            items = arg.elts if isinstance(arg, (ast.List, ast.Tuple)) else [arg]
            for el in items:
                if isinstance(el, ast.Constant) and isinstance(el.value, str):
                    words.append(el.value.strip())
                elif isinstance(el, ast.Name) and el.id in _TAG_NAMES:
                    has_tag_var = True
        # The call must actually be a git invocation. Without this, `words.index("tag")`
        # — a line of THIS scanner — reads as a tag creation. Second false positive of the
        # same family as the docstring one, and the same lesson: the check must ALLOW what
        # it claims to allow (§13, two-directional calibration).
        callee = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if "git" not in callee.lower() and "git" not in words:
            continue
        # a shell command line passed as a literal argument
        for w in words:
            if _SHELL_TAG.search(w) or _SHELL_PUSH_TAG.search(w):
                hits.append((node.lineno, "shell tag command: " + w[:60]))
                break
        else:
            if "tag" in words:
                rest = words[words.index("tag") + 1:]
                if not rest or not rest[0].startswith(_READ_ONLY_TAG_FLAGS):
                    hits.append((node.lineno, "creates a tag: " + " ".join(words[:6])))
                    continue
            if "push" in words and (
                    has_tag_var or any(w.startswith("--tags") or "refs/tags" in w
                                       for w in words)):
                hits.append((node.lineno, "pushes a tag: " + " ".join(words[:6])))
    return hits


def _tag_creation_hits_text(source):
    """Line scan for shell scripts, which have no AST and no docstrings."""
    hits = []
    for n, raw in enumerate(source.splitlines(), 1):
        if raw.strip().startswith("#"):
            continue
        if _SHELL_TAG.search(raw) or _SHELL_PUSH_TAG.search(raw):
            hits.append((n, raw.strip()))
    return hits


def test_no_script_creates_a_release_tag():
    """v1.32.0 owner-control: the CIVerd verdict is GONE from the release path, so what
    authorizes a release is David creating the tag. That is only true while NO in-repo
    script can create one — otherwise 'the owner tags it' is a convention a future commit
    can quietly delete. This is the mechanical half; the server-side half (a GitHub `v*`
    ruleset restricting tag creation to davalst) is registered as dated debt on the
    `release-tag-authority` capability, because a repo-side check can never bind an actor
    who can edit the repo.

    Red-first fact, not ritual: before scripts/release_verify.py was deleted this scan
    returned that file's `_git("tag", "-a", ...)` at :100 and `_git("push", "origin", tag)`
    at :104 — the only two tag-creation sites in the tree."""
    print("\n[release authority: no script creates a tag]")

    # (1) calibrate-the-checker FIRST — a scanner that cannot fire proves nothing (§13).
    #     Assembled at runtime so these literals never appear in this file's own source.
    _t = "t" + "ag"
    plants = {
        "shell create": "git " + _t + " -a v9.9.9 -m 'release'",
        "argv create": '_git("' + _t + '", "-a", name, sha)',
        "push --tags": 'subprocess.run(["git", "push", "origin", "--' + _t + 's"])',
        "argv push": '_git("push", "origin", ' + _t + ')',
    }
    for label, text in plants.items():
        check("PLANTED {} is detected".format(label), bool(_tag_creation_hits(text)), text)

    # (2) and it must ALLOW what it claims to allow — the other direction of the
    #     two-directional calibration table (§13). Both halves have bitten: the first
    #     draft of this scanner blocked correctly AND flagged this file's own prose.
    allowed = {
        "describe --tags": 'tag = _git_text("describe", "--' + _t + 's", "--abbrev=0")',
        "tag -l": '_git("' + _t + '", "-l", "v1.*")',
        "branch push": '_git(root, "push", "origin", "main")',
        "arg parsing": 'ap.add_argument("--no-' + _t + '", help="verify only")',
        # the regression that produced the AST rewrite: prose is not an action
        "docstring mentioning the rule":
            'def f():\n    """we never run git ' + _t + ' -a here."""\n    return 1',
        "comment mentioning the rule": "# never call git " + _t + " -a from a script",
        # the second false positive: a non-git call whose argument happens to be "tag"
        "non-git call with a tag argument": 'i = words.index("' + _t + '")',
        "dict lookup": 'v = row.get("' + _t + '", None)',
    }
    for label, text in allowed.items():
        check("ALLOWED {} is not flagged".format(label),
              not _tag_creation_hits(text), text)

    # (3) the live scan — the assertion that actually guards the release path
    offenders, scanned = [], 0
    for root_rel in _SCAN_ROOTS:
        for root, dirs, files in os.walk(os.path.join(REPO, root_rel)):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
            for fname in files:
                if not fname.endswith(_SCAN_EXT):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, encoding="utf-8") as fh:
                        src = fh.read()
                except (OSError, UnicodeDecodeError):
                    continue
                scanned += 1
                finder = _tag_creation_hits if fname.endswith(".py") \
                    else _tag_creation_hits_text
                for lineno, why in finder(src):
                    offenders.append("{}:{}: {}".format(
                        os.path.relpath(path, REPO), lineno, why[:90]))

    # denominator, never a bare green (§12): a result states what it covered
    check("no in-repo script creates or pushes a release tag "
          "(scanned {} file(s) under {})".format(scanned, ", ".join(_SCAN_ROOTS)),
          offenders == [], "; ".join(offenders))
    check("the scan was not vacuous (§4a): it read a non-trivial roster", scanned > 50,
          scanned)


if __name__ == "__main__":
    main()
