#!/usr/bin/env python3
"""Planted-input calibration for the TDD Playbook enforcement hooks.

These hooks defend the Playbook's honor-system seams (don't weaken tests, stay
deterministic). Per §13, the ungameable check is that PLANTED violations are actually
caught — a planted weakening that slips past a guard is a BLOCKING failure here.

Self-contained: drives each hook as a subprocess with crafted JSON, asserts exit code
and message. No pytest dependency (the plugin is stack-agnostic). Run:
    python3 tests/test_hooks.py
Exit 0 = all green; non-zero = a guard regressed.
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(PLUGIN))
HOOKS = os.path.join(PLUGIN, "hooks", "scripts")

_results = {"pass": 0, "fail": 0}


# G5 isolation: every hook invocation in this suite writes its yield event to a temp file,
# never to <repo>/.claude/playbook-yield.jsonl — a test run must not dirty the tree CIVerd's
# diff-integrity watches.
_YIELD_TMP = tempfile.mkdtemp(prefix="hook-yield-")
_YIELD_DEFAULT = os.path.join(_YIELD_TMP, "yield.jsonl")


# v1.32.0: these five default to OFF (31 warnings, 0 blocks across all recorded history).
# Retirement is never silent deletion, so their calibration must SURVIVE the demotion — the
# suites below still prove each guard catches what it claims. They opt in explicitly here,
# which keeps two questions apart that are easy to merge by accident:
#   "does this guard still work?"        -> the suites below, run opted-in
#   "is this guard on by default?"       -> test_retired_advisory_defaults, run on the real defaults
# Merging them would mean turning a guard off silently deletes its coverage, which is how a
# retired gate quietly becomes an unmaintained one.
_OPT_IN = {
    "overmock_guard.py": {"TDD_PLAYBOOK_HOOK_OVERMOCK": "warn"},
    "exitcode_guard.py": {"TDD_PLAYBOOK_HOOK_EXITCODE": "warn"},
    "exhaustive_claim_guard.py": {"TDD_PLAYBOOK_HOOK_EXHAUSTIVE": "warn"},
    "flaky_guard.py": {"TDD_PLAYBOOK_HOOK_FLAKY": "warn"},
    "red_lock.py": {"TDD_PLAYBOOK_HOOK_REDLOCK": "warn"},
}


def run(script, event, env_extra=None, raw=False):
    """raw=True skips the retired-guard opt-in, so a caller can observe the SHIPPED default."""
    env = dict(os.environ)
    # neutralize any developer override so tests see documented defaults
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["TDD_PLAYBOOK_YIELD_LOG"] = _YIELD_DEFAULT
    if not raw:
        for k, v in _OPT_IN.get(script, {}).items():
            env.setdefault(k, v)
    # H8 isolation: hook invocations from this suite must not write the repo's REAL
    # guards-heartbeat — a test run faking liveness would mask an actual dark guard layer
    env["TDD_PLAYBOOK_HEARTBEAT"] = os.path.join(_YIELD_TMP, "heartbeat")
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, os.path.join(HOOKS, script)],
        input=json.dumps(event), capture_output=True, text=True, env=env, timeout=20,
    )
    return p.returncode, p.stdout, p.stderr


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def edit(path, old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path,
            "old_string": old, "new_string": new}}


def write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


# ---------------------------------------------------------------- weakening_guard
def test_weakening():
    s = "weakening_guard.py"
    tf = "tests/test_pay.py"

    # PLANTED: assertion removed -> must BLOCK (integrity hook defaults to block; H2)
    rc, _o, e = run(s, edit(tf, "assert total == 5\nassert ok", "assert ok"))
    check("weaken: dropped assertion BLOCKS by default", rc == 2 and "assertions dropped" in e, (rc, e))

    # PLANTED: skip marker added -> must block
    rc, _o, e = run(s, edit(tf, "def test_pay():", "@pytest.mark.skip\ndef test_pay():"))
    check("weaken: added skip is caught", rc == 2 and "skip" in e.lower(), (rc, e))

    # PLANTED: assertion neutered to tautology -> must block
    rc, _o, e = run(s, edit(tf, "assert charge() == 10", "assert True  # TODO"))
    check("weaken: tautology is caught", rc == 2 and "tautology" in e.lower(), (rc, e))

    # CLEAN: strengthening (added assertion) -> silent (exit 0)
    rc, _o, e = run(s, edit(tf, "assert ok", "assert ok\nassert total == 5"))
    check("weaken: strengthening is NOT flagged", rc == 0 and e == "", (rc, e))

    # NEGATIVE: same weakening on a NON-test file -> silent
    rc, _o, _e = run(s, edit("src/pay.py", "assert total == 5\nx", "x"))
    check("weaken: non-test file ignored", rc == 0, rc)

    # MODE: explicit warn demotes to exit 1
    rc, _o, _e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                     {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "warn"})
    check("weaken: warn mode -> exit 1", rc == 1, rc)

    # MODE: global env can demote too (per-hook default yields to explicit global)
    rc, _o, _e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                     {"TDD_PLAYBOOK_HOOK_MODE": "warn"})
    check("weaken: global warn -> exit 1", rc == 1, rc)

    # MODE: off silences
    rc, _o, e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                    {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
    check("weaken: off mode -> exit 0 silent", rc == 0 and e == "", (rc, e))

    # MultiEdit shape is parsed
    me = {"tool_name": "MultiEdit", "tool_input": {"file_path": tf,
          "edits": [{"old_string": "assert a\nassert b", "new_string": "assert a"}]}}
    rc, _o, e = run(s, me)
    check("weaken: MultiEdit shape handled", rc == 2 and "assertions dropped" in e, (rc, e))


def test_weakening_h5_exit_calls():
    s = "weakening_guard.py"
    tf = "tests/test_pay.py"

    # PLANTED (H5): sys.exit(0) added to a test -> block (fakes a passing suite)
    rc, _o, e = run(s, edit(tf, "assert ok", "sys.exit(0)\nassert ok"))
    check("H5: sys.exit added to test is caught", rc == 2 and "exit call" in e.lower(), (rc, e))

    # PLANTED (H5): os._exit added to conftest.py (verifier surface) -> block
    rc, _o, e = run(s, edit("conftest.py", "pass", "os._exit(0)"))
    check("H5: os._exit added to conftest is caught", rc == 2 and "exit call" in e.lower(), (rc, e))

    # CLEAN: pre-existing exit call untouched by the edit -> silent
    rc, _o, e = run(s, edit(tf, "sys.exit(0)\nassert a", "sys.exit(0)\nassert a\nassert b"))
    check("H5: pre-existing exit call not re-flagged", rc == 0, (rc, e))


# ---------------------------------------------------------------------- overmock_guard
def test_overmock():
    s = "overmock_guard.py"
    tf = "tests/test_api.py"

    # PLANTED (H3): net-new mock in a test edit -> warn (advisory tier)
    rc, _o, e = run(s, edit(tf, "resp = client.get('/x')",
                            "with mock.patch('api.client.get') as m:\n    resp = m()"))
    check("H3: net-new mock is flagged (warn)", rc == 1 and "net-new mock" in e, (rc, e))

    # PLANTED (H3): jest.mock in a Write of a new test file -> warn
    rc, _o, e = run(s, write("src/__tests__/api.test.ts",
                             "jest.mock('../client');\ntest('x', () => {});"))
    check("H3: jest.mock in new test file flagged", rc == 1 and "net-new mock" in e, (rc, e))

    # CLEAN: mock count unchanged (refactor around an existing mock) -> silent
    rc, _o, e = run(s, edit(tf, "m = mock.patch('a')", "m = mock.patch('a')  # moved"))
    check("H3: unchanged mock count silent", rc == 0, (rc, e))

    # CLEAN: mock REMOVED -> silent (strengthening)
    rc, _o, e = run(s, edit(tf, "m = mock.patch('a')\nx", "x"))
    check("H3: removed mock silent", rc == 0, (rc, e))

    # NEGATIVE: non-test file with mocks (a test helper lib) -> ignored
    rc, _o, _e = run(s, edit("src/factory.py", "x", "m = mock.patch('a')"))
    check("H3: non-test file ignored", rc == 0, rc)

    # v1.25 (G2e — the §1 seam-fabrication rule's mechanical trigger):
    # create_autospec is the PRESCRIBED check for the rule (a missing production
    # attribute RAISES) — counting it as mock noise punishes exactly the right move
    rc, _o, e = run(s, edit(tf, "resp = client.get('/x')",
                            "spec = create_autospec(Client)\nresp = spec.get('/x')"))
    check("G2e: create_autospec alone is NOT a net-new mock (prescribed check)",
          rc == 0, (rc, e))

    # PLANTED (seam fabrication — the Cheliped months-green class): a double that
    # GRAFTS a seam production may lack (SimpleNamespace with a callable member)
    rc, _o, e = run(s, edit(tf, "result = runner()",
                            "result = SimpleNamespace(interruptions=[], "
                            "to_state=lambda: state)"))
    check("G2e: fabricated-seam double flagged (advisory, names the class)",
          rc == 1 and "seam" in e, (rc, e))

    # CLEAN control: SimpleNamespace as plain data (no callable graft) stays silent
    rc, _o, e = run(s, edit(tf, "cfg = load()",
                            "cfg = SimpleNamespace(host='x', port=1)"))
    check("G2e: data-only SimpleNamespace control silent", rc == 0, (rc, e))

    # v1.25 arch-F5 (probe-proven misses — H10 inside the commit defining H10): the
    # pattern must catch the REAL shapes, not just the hand-transcribed happy case
    rc, _o, e = run(s, edit(tf, "result = runner()",
                            "result = SimpleNamespace(client=Client(), "
                            "to_state=lambda: state)"))
    check("F5: preceding call-kwarg does not disarm the seam pattern",
          rc == 1 and "seam" in e, (rc, e))
    rc, _o, e = run(s, edit(tf, "result = runner()",
                            "ns = SimpleNamespace()\nns.to_state = lambda: state"))
    check("F5: after-construction attribute graft is caught",
          rc == 1 and "seam" in e, (rc, e))
    rc, _o, e = run(s, edit(tf, "result = runner()",
                            "m = MagicMock()\nm.to_state = lambda: state"))
    check("F5: MagicMock attribute graft is caught", rc == 1 and "seam" in e, (rc, e))


# ---------------------------------------------------------------------- exitcode_guard
def test_exitcode():
    """v1.28 §4a — a verifier's exit code swallowed by a pipe. Two live instances in two
    days, in the two codebases that check each other: I gated a commit chain on a piped
    gate run and pushed a repo-red commit (2026-08-05), and the CIVerd runner masked a
    pytest exit the same way (2026-08-06). Calibrated in BOTH directions per the v1.28 bar:
    it must flag the masked case and stay silent on every honest handling."""
    s = "exitcode_guard.py"

    # H15 / SCOPE DECISION, 2026-08-06 — DECIDED, not assumed. Cheliped asked whether a
    # SELECTOR flag is in scope for this guard, and specified the plant that settles it: a
    # suite with one failing test plus a marker that deselects it, reported as a pass. The
    # answer is NO, and it is pinned here as an ALLOW row so a future session that widens
    # the guard has to confront the decision rather than drift into it.
    #
    # Why: this hook fires on the Bash call, and at that moment a scoped run is
    # indistinguishable from a scoped REPORT. Narrowing while iterating is normal and
    # correct; a guard that flags it cries wolf and gets demoted, which is how a guard dies.
    # The error lives at the reporting end, so the denominator rule (§12) covers it there —
    # `N of M`, not a hook. See HACK_CATALOG H15.
    for cmd in ('pytest -m "not flaky"',
                'pytest -k "not docker" tests/',
                "pytest --ignore=tests/integration",
                "pytest --lf",
                "pytest --maxfail=1 && echo done"):
        check("exitcode: SELECTOR stays silent (decided out of scope, H15): " + cmd[:38],
              run(s, {"tool_name": "Bash",
                      "tool_input": {"command": cmd}})[0] == 0, cmd)

    def ev(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    # PLANTED — the exact shapes that bit, frozen. Restated 2026-08-18 in their CONSUMPTION
    # form: both incidents were a piped verdict whose status was then acted on (a commit
    # chain gated on it; a runner reading it). The display-only variants of these same
    # commands moved to the ALLOW block below under the v1.42 scope decision — the incident
    # is what is frozen here, not the punctuation.
    rc, _o, e = run(s, ev("sh scripts/civerd_gate.sh | tail -2 && git commit -m x"))
    check("exitcode: piped gate gating a commit chain is flagged (the 2026-08-05 shape)",
          rc == 1 and "swallowed by a pipe" in e, (rc, e[:120]))
    rc, _o, e = run(s, ev(
        "python3 plugins/tdd-playbook/tests/test_hooks.py 2>&1 | grep FAIL; rc=$?"))
    check("exitcode: piped suite whose status is read is flagged (the 2026-08-06 shape)",
          rc == 1 and "discarded truth" in e, (rc, e[:120]))
    rc, _o, e = run(s, ev("pytest -q | tail -1; rc=$?"))
    check("exitcode: piped pytest whose status is captured is flagged", rc == 1,
          (rc, e[:120]))
    # v1.32.0: release_verify.py left _VERIFIER with the release wall. verify_verdict.py
    # STAYS (archival reader, still a verdict-bearing exit code) — and until now it was
    # named in the pattern but never exercised, so nothing would have noticed if the
    # deletion had taken it too. A roster entry with no test is a comment (§4a).
    rc, _o, e = run(s, ev(
        "python3 plugins/tdd-playbook/bin/verify_verdict.py --sha abc123 | tail -1 && echo ok"))
    check("exitcode: piped archival verdict CHAINED ON is flagged", rc == 1, (rc, e[:120]))
    rc, _o, e = run(s, ev("python3 scripts/release_verify.py --wait-s 60 | tail -1"))
    check("exitcode: the retired release_verify.py is no longer a verifier", rc == 0,
          (rc, e[:120]))

    # ALLOW — every honest handling must stay silent (the half that decides adoption)
    rc, _o, e = run(s, ev("sh scripts/civerd_gate.sh > /tmp/g.out 2>&1; rc=$?"))
    check("exitcode: capture-then-inspect is allowed", rc == 0, (rc, e[:120]))
    rc, _o, e = run(s, ev("set -o pipefail; sh scripts/civerd_gate.sh | tail -2"))
    check("exitcode: pipefail is allowed", rc == 0, (rc, e[:120]))
    rc, _o, e = run(s, ev("sh scripts/civerd_gate.sh || exit 1"))
    check("exitcode: exit code consumed directly is allowed", rc == 0, (rc, e[:120]))
    rc, _o, e = run(s, ev("grep FAIL /tmp/g.out | head -3"))
    check("exitcode: piping a NON-verifier is none of its business", rc == 0, (rc, e[:120]))
    rc, _o, e = run(s, ev("git log --oneline -5 | tail -2"))
    check("exitcode: ordinary piped tooling is allowed", rc == 0, (rc, e[:120]))
    # H15-STYLE SCOPE DECISION, 2026-08-18 — DECIDED, not drifted into. David saw the guard
    # firing on nearly every command and called it "unsettling and non-stop". The record
    # agreed: 701 warns / 0 blocks / 0 adjudicated false positives across 6 cycles. In six
    # cycles it never once changed a decision, while rendering as a red "hook error" every
    # few seconds.
    #
    # The guard was not wrong — it was UNDER-SPECIFIED. §4a's concern is "a RED gate reads as
    # 0", which requires the piped status to be CONSUMED as a verdict. Piping a suite into
    # `grep` so a human can read the output discards nothing: nobody was going to branch on
    # that status, and the human reads the real result. So the guard now fires only where the
    # status is actually consumed — assigned to `$?`, tested by if/while, or chained with
    # && / ||. Both incidents it was built for are consumption shapes and still flag.
    #
    # Frozen as ALLOW rows so a future session that re-widens it has to confront the decision
    # rather than drift back into wallpaper. A guard demoted for crying wolf protects nothing.
    for cmd in ("python3 plugins/tdd-playbook/tests/test_hooks.py 2>&1 | grep FAIL",
                "pytest -q | tail -1",
                "python3 plugins/tdd-playbook/bin/capability_registry.py validate | tail -2",
                "sh scripts/civerd_gate.sh 2>&1 | head -20"):
        rc, _o, e = run(s, ev(cmd))
        check("exitcode: DISPLAY-only pipe stays silent (v1.42 scope): " + cmd[:42],
              rc == 0, (rc, e[:100]))

    # ...and the consumption shapes MUST still fire — this is the half that keeps the guard
    # worth having. Each is a real way a RED verdict becomes a green one.
    for label, cmd in [
            ("status captured after a pipe", "sh scripts/civerd_gate.sh | tail -1; rc=$?"),
            ("piped status gates a chain", "pytest -q | tail -1 && git commit -m x"),
            ("piped status in a conditional", "if pytest -q | grep -q FAIL; then echo bad; fi"),
            ("piped status echoed as the verdict",
             "python3 plugins/tdd-playbook/tests/test_hooks.py | tail -1; echo rc=$?")]:
        rc, _o, e = run(s, ev(cmd))
        check("exitcode: CONSUMED piped status still flagged — " + label, rc == 1,
              (rc, e[:100]))

    rc, _o, _e = run(s, {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}})
    check("exitcode: non-Bash events ignored", rc == 0, rc)


# -------------------------------------------------------------------------- tag_guard
def test_tag_guard():
    """v1.32.0 — the release tag is the owner's signature. Deleting the CIVerd wall is only
    safe while the model cannot cut a tag, and the file scanner in test_installer.py covers
    committed scripts, NOT a session typing `git tag` into Bash. Both directions pinned:
    creation/push BLOCKS (exit 2), every read-only tag use stays silent.

    Every command below is ASSEMBLED AT RUNTIME. These strings are exactly what
    test_no_script_creates_a_release_tag hunts for, and this file is in its derived roster,
    so a literal here would make the two guards fight. The sanctioned resolution is the
    house idiom - build the needle so the haystack never contains it - never an exemption
    entry, which is the darkness hatch §6a forbids."""
    print("\n[tag_guard]")
    s = "tag_guard.py"
    T = "t" + "ag"
    V, V2, R = "v1.0" + ".0", "v1.32" + ".0", "rele" + "ase create"

    def ev(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    # BLOCK — every road to a tag. exit 2 = block (integrity default), not 1 = warn.
    for label, cmd in [
            ("signed tag", "git {T} -s {V2} -m release"),
            ("annotated tag", "git {T} -a {V2} -m release"),
            ("lightweight tag", "git {T} {V2}"),
            ("tag then push, one call", "git {T} -a {V} -m x && git push origin {V}"),
            ("push --tags", "git push origin --{T}s"),
            ("push a refspec", "git push origin refs/{T}s/{V}"),
            ("push a bare version", "git push origin {V2}"),
            ("update-ref", "git update-ref refs/{T}s/{V} HEAD"),
            ("gh CLI release", "gh {R} {V} --notes x"),
            ("git -C form", "git -C /tmp/repo {T} -a v1 -m x"),
            ("hidden after a cd", "cd /tmp && git {T} -a v9.9.9 -m sneaky")]:
        rc, _o, e = run(s, ev(cmd.format(T=T, V=V, V2=V2, R=R)))
        check("tagguard BLOCKS: " + label, rc == 2, (rc, e[:100]))

    # ALLOW — reading tags is the gate's own business (gate_runner._ledger_base,
    # review_ledger and test_harness all run `describe --tags`). A guard that blocked these
    # would break the gate it protects. Deleting a local tag cannot mint a release.
    for label, cmd in [
            ("describe --tags", "git describe --{T}s --abbrev=0"),
            ("tag -l", "git {T} -l 'v1.*'"),
            ("bare tag listing", "git {T}"),
            ("tag -n", "git {T} -n5"),
            ("delete a scratch tag", "git {T} -d v0.0.0-test"),
            ("ls-remote", "git ls-remote --{T}s origin"),
            ("ordinary branch push", "git push origin main"),
            ("for-each-ref", "git for-each-ref refs/{T}s --format='%(refname)'"),
            ("commit", "git commit -m 'feat: x'"),
            ("prose in an echo", "echo 'David runs git {T} -s to release'"),
            # v1.42 live false positives (2026-08-17, recorded via guard_note before the
            # fix). Both are the SAME root cause: the guard grepped the command instead of
            # parsing it, which is the failure §12 names in its own rule. Frozen here as
            # the motivating artifacts (§13 guard calibration) so the parse cannot regress
            # to a grep.
            #  (1) a LISTING flag the read-pattern's allow-list did not enumerate. The
            #      allow-list approach is wrong by construction: `git tag` with no tag NAME
            #      and no creation flag cannot create anything, whatever flags follow.
            ("listing sorted by version", "git {T} --sort=-v:refname"),
            ("listing sorted, separate value", "git {T} --sort -v:refname"),
            ("listing with a format", "git {T} --list --format='%(refname:short)'"),
            ("listing merged into HEAD", "git {T} --merged HEAD"),
            ("listing in a pipeline", "git {T} --sort=-v:refname | head -1"),
            ("assigned from a subshell", "LAST=$(git {T} --sort=-v:refname | head -1)"),
            #  (2) the second-order bug: the guard blocked guard_note.py RECORDING the
            #      block, because the note QUOTED the offending command — so §12's own
            #      accounting mechanism was unusable for this gate. A verb inside a quoted
            #      argument is prose, exactly like the echo case above; only a verb in
            #      COMMAND POSITION is an action.
            ("the verb quoted inside an argument",
             "python3 guard_note.py record --gate {T}guard --objected 'git {T} -a {V} -m x'"),
            ("the verb inside a double-quoted argument",
             'python3 note.py --text "we blocked git {T} -s {V} here"'),
            ("a grep for the verb", "grep -rn 'git {T}' docs/")]:
        rc, _o, e = run(s, ev(cmd.format(T=T, V=V, V2=V2, R=R)))
        check("tagguard ALLOWS: " + label, rc == 0, (rc, e[:100]))

    # the sanctioned demotion works, and leaves a `suppressed` trace rather than silence
    rc, _o, _e = run(s, ev("git {T} -a v1 -m x".format(T=T)),
                     env_extra={"TDD_PLAYBOOK_HOOK_TAGGUARD": "warn"})
    check("tagguard: documented demotion warns instead of blocking", rc == 1, rc)
    rc, _o, _e = run(s, {"tool_name": "Edit", "tool_input": {"file_path": "x.py"}})
    check("tagguard: non-Bash events ignored", rc == 0, rc)


# ------------------------------------------------------------------------ break-glass
def test_break_glass():
    """v1.32.0 owner-control: ONE obvious switch that demotes every blocking gate for a
    session, loud and journaled.

    The gap it closes: TDD_PLAYBOOK_HOOK_MODE accepted only warn|block, so `=off` was
    SILENTLY IGNORED and integrity hooks stayed blocking — a knob that reads as a kill
    switch and is not one is worse than no knob, because the operator believes they turned
    something off. Per-hook TDD_PLAYBOOK_HOOK_<NAME> already worked; what was missing was a
    single switch you can reach for when you do not yet know which of eleven guards is in
    your way.

    Deliberately NOT silent: emit() logs a `suppressed` event for every finding that fires
    while demoted, so gate_yield's rollup shows a muzzled gate rather than a quiet one, and
    the reason string is REQUIRED — an empty break-glass is refused, because the record is
    the entire difference between an emergency and a habit."""
    s = "weakening_guard.py"
    tf = "tests/test_pay.py"
    weaken = edit(tf, "assert total == 5\nassert ok", "assert ok")

    rc, _o, e = run(s, weaken)
    check("break-glass: blocking is the default with no switch", rc == 2, (rc, e[:80]))

    rc, _o, e = run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": "prod incident, need to ship"})
    check("break-glass: a REASONED switch demotes a blocking gate to warn", rc == 1,
          (rc, e[:120]))
    check("break-glass: the banner is loud and repeats the reason",
          "BREAK-GLASS" in e and "prod incident" in e, e[:200])

    # the reason is the mechanism, not decoration
    rc, _o, e = run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": ""})
    check("break-glass: empty value does NOT demote (an unexplained bypass is refused)",
          rc == 2, (rc, e[:80]))
    rc, _o, e = run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": "   "})
    check("break-glass: whitespace-only value does NOT demote", rc == 2, (rc, e[:80]))

    # it demotes, it never silences: a muzzled gate must stay distinguishable from a quiet one
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": "incident", "TDD_PLAYBOOK_YIELD_LOG": log})
        rows = [json.loads(x) for x in open(log)] if os.path.isfile(log) else []
        check("break-glass: the demoted finding is still RECORDED (never silent)",
              any(r.get("event") in ("block", "warn", "suppressed") for r in rows), rows[:2])
        check("break-glass: the record carries the reason for /grade",
              any("incident" in json.dumps(r) for r in rows), rows[:2])

    # an explicit per-hook setting is more specific than the blanket switch and must win
    rc, _o, _e = run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": "incident",
                                 "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "block"})
    check("break-glass: an explicit per-hook block still wins (specific beats blanket)",
          rc == 2, rc)

    # IT MUST NEVER SILENCE. The first implementation returned _DEFAULT_MODES directly,
    # skipping the global-env layer and landing on the v1.32.0 `off` defaults — so breaking
    # glass MUTED the five opt-in guards outright, and did so even for an operator who had
    # globally escalated everything to block. The docstring said "it cannot silence a gate"
    # while the code silenced five. Asserted on resolve_mode, not on the defaults dict: the
    # dict was right and the resolver was wrong, which is exactly why a dict assertion could
    # not see it.
    import importlib.util as _il
    _sp = _il.spec_from_file_location("_common", os.path.join(HOOKS, "_common.py"))
    _c = _il.module_from_spec(_sp); _sp.loader.exec_module(_c)

    def _mode(gate, **envs):
        keep = {k: v for k, v in os.environ.items() if not k.startswith("TDD_PLAYBOOK_")}
        old_env = dict(os.environ)
        os.environ.clear(); os.environ.update(keep); os.environ.update(envs)
        try:
            return _c.resolve_mode(gate)
        finally:
            os.environ.clear(); os.environ.update(old_env)

    for gate in ("exitcode", "overmock", "exhaustive", "flaky", "redlock"):
        check("break-glass NEVER silences {} (off stays off, never a silent bypass)".format(gate),
              _mode(gate, TDD_PLAYBOOK_BREAK_GLASS="incident") == "off",
              _mode(gate, TDD_PLAYBOOK_BREAK_GLASS="incident"))
        check("break-glass under a global escalation demotes {} to warn, not off".format(gate),
              _mode(gate, TDD_PLAYBOOK_HOOK_MODE="block",
                    TDD_PLAYBOOK_BREAK_GLASS="incident") == "warn",
              _mode(gate, TDD_PLAYBOOK_HOOK_MODE="block", TDD_PLAYBOOK_BREAK_GLASS="incident"))
    for gate in ("testweaken", "testlock", "snapshotguard", "tagguard"):
        check("break-glass demotes {} to warn, never off".format(gate),
              _mode(gate, TDD_PLAYBOOK_BREAK_GLASS="incident") == "warn",
              _mode(gate, TDD_PLAYBOOK_BREAK_GLASS="incident"))

    # THE HOLE BREAK-GLASS WAS BUILT TO CLOSE. `TDD_PLAYBOOK_HOOK_MODE=off` was silently
    # ignored — a knob the operator believes they turned off, which is still on. The first
    # attempt shipped a third env var BESIDE the broken one instead of fixing the swallow.
    rc, _o, e = run(s, weaken, {"TDD_PLAYBOOK_HOOK_MODE": "off"})
    check("HOOK_MODE=off is no longer SILENTLY ignored — it is REFUSED out loud",
          "REFUSED" in e and "STILL ARMED" in e, e[:200])
    check("...and the guard still blocks rather than pretending it was demoted", rc == 2, rc)
    check("...and the refusal points at the sanctioned wide switch",
          "BREAK_GLASS" in e, e[:200])
    rc, _o, e = run(s, weaken, {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "disabled"})
    check("a typo'd per-hook value is reported, not swallowed", "IGNORED" in e, e[:160])

    # BREAK-GLASS MUST NOT LAUNDER THE BLOCK OUT OF THE COMPLIANCE RECORD. guard_response.md
    # counts gate_yield's `blocks`; logging the demoted mode erased it, so the one instrument
    # built to tell "complied" from "routed around" read cleanest in the sessions where every
    # block was bypassed.
    with _tf.TemporaryDirectory() as d:
        log = os.path.join(d, "y2.jsonl")
        run(s, weaken, {"TDD_PLAYBOOK_BREAK_GLASS": "incident", "TDD_PLAYBOOK_YIELD_LOG": log})
        rows = [json.loads(x) for x in open(log)] if os.path.isfile(log) else []
        check("break-glass records the event as a BLOCK (the fact), not a warn (the outcome)",
              any(r.get("event") == "block" for r in rows), rows[:2])
        check("...carrying demoted_by so the outcome is not lost either",
              any(r.get("demoted_by") == "break-glass" for r in rows), rows[:2])

    # and it reaches the gate born in this same release
    rc, _o, _e = run("tag_guard.py",
                     {"tool_name": "Bash", "tool_input": {"command": "git " + "t" + "ag" + " -a v1 -m x"}},
                     {"TDD_PLAYBOOK_BREAK_GLASS": "backfilling historical release tags"})
    check("break-glass: covers every blocking gate, incl. tagguard", rc == 1, rc)


def test_retired_advisory_defaults():
    """v1.32.0: the five guards with 31 warnings and ZERO blocks across all recorded history
    (docs/calibration/gate_yield.md: exitcode 0/24, overmock 0/3, exhaustive 0/2, flaky 0/1,
    redlock 0/1) default to OFF and are opt-in.

    This is §13's decay principle in the SECOND direction — a gate can decay by becoming
    more expensive than the risk it retires, not only by becoming weaker than the threat.
    Retirement is never silent deletion: the scripts stay, the per-hook knob turns each back
    on, and gate_yield keeps its rows."""
    # The mode-per-guard policy pin (which script blocks, which is opt-in) lives in
    # test_guard_roster_derived_and_pinned: EXPECTED_BLOCKING/EXPECTED_OPTIN are the one
    # literal expectation, compared against the DERIVED partition — not read back from
    # _DEFAULT_MODES, which would drift with it.

    # opt-in must actually work, or "off by default, available" is a story
    rc, _o, e = run("overmock_guard.py",
                    edit("tests/test_api.py", "resp = client.get('/x')",
                         "with mock.patch('api.client.get') as m:\n    resp = m()"),
                    raw=True)
    check("retired-to-opt-in: overmock is silent by default", rc == 0, (rc, e[:80]))
    rc, _o, e = run("overmock_guard.py",
                    edit("tests/test_api.py", "resp = client.get('/x')",
                         "with mock.patch('api.client.get') as m:\n    resp = m()"),
                    {"TDD_PLAYBOOK_HOOK_OVERMOCK": "warn"})
    check("retired-to-opt-in: overmock still WORKS when opted in", rc == 1, (rc, e[:80]))


# ------------------------------------------------------------- exhaustive_claim_guard
def test_exhaustive_claim():
    """v1.28 §12 — a test that CLAIMS exhaustiveness must say how it could FAIL. From
    Cheliped's field report: a parity test named "every deletion goes through the one
    seam" was genuinely exhaustive over deletions and structurally blind to the path that
    deleted nothing, so it could not have failed on the real bug — and its author, its
    reviewer and two later sessions all read the name as the guarantee. Both directions
    per the v1.28 bar; the ALLOW rows matter most here, because the claim vocabulary
    (every/all/none) is also the most common vocabulary in ordinary test code."""
    s = "exhaustive_claim_guard.py"
    tf = "tests/test_parity.py"

    # PLANTED — the motivating shape, frozen: a universal claim with no falsifier line
    rc, _o, e = run(s, write(tf, "def test_every_deletion_goes_through_the_seam():\n"
                                 "    for site in KNOWN_SITES:\n        assert seam(site)\n"))
    check("exhaustive: bare universal claim in a test NAME is flagged",
          rc == 1 and "CLAIMS exhaustiveness" in e, (rc, e[:140]))
    rc, _o, e = run(s, edit(tf, "def test_sites():", "def test_no_other_writer_exists():"))
    check("exhaustive: net-new claim in an edit is flagged", rc == 1, (rc, e[:140]))
    rc, _o, e = run(s, write(tf, 'def test_shape():\n'
                                 '    assert not stray, "no other module may write here"\n'))
    check("exhaustive: claim in an assertion MESSAGE is flagged",
          rc == 1 and "no other" in e, (rc, e[:140]))
    rc, _o, e = run(s, write("tests/parity.test.js",
                             'it("registers all handlers and nothing else", () => {})\n'))
    check("exhaustive: JS title claim is flagged", rc == 1, (rc, e[:140]))

    # ALLOW — the guard's own stated contract; a false positive here trains people to
    # ignore it, which costs more than the miss it prevents
    rc, _o, e = run(s, write(tf, "def test_every_deletion_goes_through_the_seam():\n"
                                 "    # a violating case: a site that deletes nothing but\n"
                                 "    # still mutates state — enumerated from the registry\n"
                                 "    for site in registry.all_sites():\n"
                                 "        assert seam(site)\n"))
    check("exhaustive: a stated violating case discharges the claim", rc == 0, (rc, e[:140]))
    rc, _o, e = run(s, write(tf, "def test_totals():\n    assert all(x > 0 for x in rows)\n"))
    check("exhaustive: `assert all(...)` is not a claim", rc == 0, (rc, e[:140]))
    rc, _o, e = run(s, write(tf, "def test_rows():\n    for r in all_rows:\n"
                                 "        assert r.ok\n"))
    check("exhaustive: a variable named all_rows is not a claim", rc == 0, (rc, e[:140]))
    rc, _o, e = run(s, write("src/handlers.py",
                             "def every_handler():\n    return ALL\n"))
    check("exhaustive: non-test files are none of its business", rc == 0, (rc, e[:140]))
    rc, _o, e = run(s, edit(tf, "def test_all_sites():\n    pass",
                            "def test_all_sites():\n    assert sites\n"))
    check("exhaustive: a PRE-EXISTING claim is not re-flagged on every edit",
          rc == 0, (rc, e[:140]))


# ---------------------------------------------------------------------- snapshot_guard
def test_snapshot():
    s = "snapshot_guard.py"

    def bash(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    # PLANTED (H5): snapshot auto-update invocations -> BLOCK
    for cmd in ("npx jest -u", "vitest run --update-snapshots", "jest --updateSnapshot",
                "pytest --snapshot-update", "UPDATE_SNAPSHOTS=1 npm test"):
        rc, _o, e = run(s, bash(cmd))
        check("H5: '{}' blocked".format(cmd), rc == 2 and "snapshot" in e.lower(), (rc, e))

    # CLEAN: plain test runs untouched
    for cmd in ("npx jest", "pytest -q", "npm test -- --coverage", "git status -u"):
        rc, _o, e = run(s, bash(cmd))
        check("clean: '{}' passes".format(cmd), rc == 0, (rc, e))

    # PLANTED (H5): direct edit of a .snap / __snapshots__ file -> BLOCK
    rc, _o, e = run(s, edit("src/__snapshots__/App.test.js.snap", "old", "new"))
    check("H5: __snapshots__ edit blocked", rc == 2 and "re-approval" in e, (rc, e))
    rc, _o, e = run(s, write("tests/output.snap", "expected"))
    check("H5: .snap write blocked", rc == 2, (rc, e))

    # CLEAN: ordinary file edit passes
    rc, _o, e = run(s, edit("src/app.py", "a", "b"))
    check("clean: ordinary edit passes", rc == 0, (rc, e))


# ----------------------------------------------------------------------- flaky_guard
def test_flaky():
    s = "flaky_guard.py"
    tf = "tests/test_api.py"

    rc, _o, e = run(s, edit(tf, "x = 1", "import time\ntime.sleep(2)"))
    check("flaky: sleep is caught", rc == 1 and "sleep" in e.lower(), (rc, e))

    rc, _o, e = run(s, edit(tf, "x = 1", "v = random.randint(0, 9)"))
    check("flaky: unseeded randomness is caught", rc == 1 and "random" in e.lower(), (rc, e))

    # seeded in the same block -> not flagged
    rc, _o, _e = run(s, edit(tf, "x = 1", "random.seed(0)\nv = random.randint(0, 9)"))
    check("flaky: seeded randomness NOT flagged", rc == 0, _e)

    # REGRESSION (old bug): a mere @pytest.fixture in the block must NOT suppress a
    # wall-clock warning — a fixture proves nothing about time control
    rc, _o, e = run(s, edit(tf, "x = 1",
                            "@pytest.fixture\ndef now_fixture():\n    return datetime.now()"))
    check("flaky: fixture does not suppress wall-clock", rc == 1 and "wall-clock" in e, (rc, e))

    # a REAL clock control in the same block still suppresses
    rc, _o, _e = run(s, edit(tf, "x = 1",
                             "@freeze_time('2026-01-01')\ndef test_t():\n    d = datetime.now()"))
    check("flaky: freeze_time suppresses wall-clock", rc == 0, _e)

    # monkeypatching the CLOCK suppresses; monkeypatching something else does not
    rc, _o, _e = run(s, edit(tf, "x = 1",
                             "monkeypatch.setattr(time, 'time', lambda: 0)\nt = time.time()"))
    check("flaky: monkeypatched clock suppresses", rc == 0, _e)
    rc, _o, e = run(s, edit(tf, "x = 1",
                            "monkeypatch.setattr(api, 'fetch', fake)\nt = time.time()"))
    check("flaky: unrelated monkeypatch does NOT suppress", rc == 1 and "wall-clock" in e, (rc, e))

    rc, _o, e = run(s, edit(tf, "x = 1", "r = requests.get('http://x')"))
    check("flaky: live network is caught", rc == 1 and "network" in e.lower(), (rc, e))

    # Write of a clean test -> silent
    rc, _o, e = run(s, write(tf, "def test_x():\n    assert add(2, 2) == 4\n"))
    check("flaky: clean Write not flagged", rc == 0 and e == "", (rc, e))

    # non-test file with a sleep -> ignored (prod code may legitimately sleep)
    rc, _o, _e = run(s, edit("src/worker.py", "x = 1", "time.sleep(2)"))
    check("flaky: non-test file ignored", rc == 0, _e)


# ----------------------------------------------------------------------- intent_nudge
def test_intent():
    s = "intent_nudge.py"

    def fired(o):
        return '"additionalContext"' in o and "TDD Playbook" in o

    with tempfile.TemporaryDirectory() as sd:
        def go(prompt, sid, extra=None):
            env = {"TDD_PLAYBOOK_NUDGE_STATE_DIR": sd}
            env.update(extra or {})
            ev = {"prompt": prompt}
            if sid is not None:
                ev["session_id"] = sid
            return run(s, ev, env)

        rc, o, _e = go("fix the off-by-one bug in the pager", "s1")
        check("intent: build/fix prompt injects reminder", rc == 0 and fired(o), (rc, o))

        rc, o, _e = go("thanks!", "s1")
        check("intent: trivial prompt -> no injection", rc == 0 and o.strip() == "", (rc, o))

        rc, o, _e = go("use the TDD Playbook to build the parser", "s-alone")
        check("intent: already-invoked prompt -> no double", rc == 0 and o.strip() == "", (rc, o))

        rc, o, _e = go("implement the new billing feature", "s-off",
                       {"TDD_PLAYBOOK_NUDGE": "off"})
        check("intent: NUDGE=off silences", rc == 0 and o.strip() == "", (rc, o))

        # PLANTED (duplicate registration): the SAME prompt in the SAME session — a second
        # invocation (plugin + vendored settings both registered) must stay silent
        rc, o, _e = go("fix the off-by-one bug in the pager", "s1")
        check("intent: duplicate registration -> second invocation silent",
              rc == 0 and o.strip() == "", (rc, o))

        # damping: a DIFFERENT build prompt in the same session within the interval -> silent
        rc, o, _e = go("implement the new billing feature", "s1")
        check("intent: within damp interval -> silent", rc == 0 and o.strip() == "", (rc, o))

        # interval=0 disables damping: different prompts each fire...
        rc, o, _e = go("implement the new billing feature", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 first prompt fires", rc == 0 and fired(o), (rc, o))
        rc, o, _e = go("refactor the parser module now", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 next prompt fires again", rc == 0 and fired(o), (rc, o))
        # ...but the SAME prompt is still deduped (duplicate registration protection)
        rc, o, _e = go("refactor the parser module now", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 same prompt still deduped",
              rc == 0 and o.strip() == "", (rc, o))

        # meta-discussion exclusion: decision/opinion questions must NOT trigger, even
        # when they contain intent verbs like "implement" or "review"
        rc, o, _e = go("should we implement this centrally? any thoughts on improvements?",
                       "s3")
        check("intent: 'should we implement' meta-question -> silent",
              rc == 0 and o.strip() == "", (rc, o))
        rc, o, _e = go("what do you think about the code review — is the roster too big?",
                       "s3")
        check("intent: 'what do you think' meta-question -> silent",
              rc == 0 and o.strip() == "", (rc, o))

        # session isolation: a different session fires fresh
        rc, o, _e = go("fix the off-by-one bug in the pager", "s4")
        check("intent: new session fires fresh", rc == 0 and fired(o), (rc, o))

        # no session_id (older host): still fires via fallback key, never crashes
        with tempfile.TemporaryDirectory() as sd2:
            rc, o, _e = run(s, {"prompt": "fix the crash in the auth path"},
                            {"TDD_PLAYBOOK_NUDGE_STATE_DIR": sd2})
            check("intent: missing session_id still fires (fallback key)",
                  rc == 0 and fired(o), (rc, o))

    # unwritable state dir: FAIL OPEN — the nudge must fire rather than crash or block
    rc, o, _e = run(s, {"prompt": "fix the crash in the auth path", "session_id": "s5"},
                    {"TDD_PLAYBOOK_NUDGE_STATE_DIR": "/nonexistent/nope/really-not-here"})
    check("intent: unwritable state dir fails OPEN (fires)", rc == 0 and fired(o), (rc, o))


# ------------------------------------------------------------- build_completion_reminder
def test_tripwire_reminder():
    s = "build_completion_reminder.py"

    # re-entry guard: stop_hook_active -> always silent (no loop)
    rc, _o, _e = run(s, {"stop_hook_active": True})
    check("tripwire: re-entry guard silent", rc == 0, rc)

    # end-to-end in a throwaway git repo: source-only change must warn
    with tempfile.TemporaryDirectory() as d:
        def git(*a):
            subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 1\n")
        git("add", "-A")
        git("commit", "-qm", "init")
        # change source only, no test
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 2\n")
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        p = subprocess.run(
            [sys.executable, os.path.join(HOOKS, s)],
            input="{}", capture_output=True, text=True, cwd=d, env=env, timeout=20,
        )
        check("tripwire: source-only change warns", p.returncode == 1 and "no test" in p.stderr.lower(),
              (p.returncode, p.stderr))

        # now add a test change too -> silent
        open(os.path.join(d, "test_app.py"), "w").write("def test_f():\n    assert f() == 2\n")
        p = subprocess.run(
            [sys.executable, os.path.join(HOOKS, s)],
            input="{}", capture_output=True, text=True, cwd=d, env=env, timeout=20,
        )
        check("tripwire: source+test change silent", p.returncode == 0, (p.returncode, p.stderr))

        # REGRESSION (old bug): tree has BOTH changes, but the TRANSCRIPT shows this
        # session only edited source — a pre-existing test change elsewhere must no
        # longer silence the reminder
        def transcript(paths):
            tp = os.path.join(d, "transcript.jsonl")
            with open(tp, "w") as fh:
                for pth in paths:
                    fh.write(json.dumps({"type": "assistant", "message": {"content": [
                        {"type": "tool_use", "name": "Edit",
                         "input": {"file_path": os.path.join(d, pth)}}]}}) + "\n")
            return tp

        ev = json.dumps({"transcript_path": transcript(["app.py"])})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: session-only source edit warns despite unrelated test change",
              p.returncode == 1 and "no test" in p.stderr.lower(), (p.returncode, p.stderr))

        # transcript shows source+test edited by the session -> silent
        ev = json.dumps({"transcript_path": transcript(["app.py", "test_app.py"])})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: session source+test edits silent", p.returncode == 0,
              (p.returncode, p.stderr))

        # unreadable transcript falls back to whole-tree behavior (silent here: tree has tests)
        ev = json.dumps({"transcript_path": os.path.join(d, "nope.jsonl")})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: missing transcript falls back to whole tree", p.returncode == 0,
              (p.returncode, p.stderr))

    # integ-#7: a fixture-DATA edit is not a test change — it must NOT silence the nudge.
    import importlib.util as _il
    spec = _il.spec_from_file_location(
        "build_completion_reminder", os.path.join(HOOKS, "build_completion_reminder.py"))
    bcr = _il.module_from_spec(spec)
    spec.loader.exec_module(bcr)
    src, tests = bcr.classify(["src/pay.py", "tests/test_pay.py",
                               "tests/fixtures/test_cases.json"])
    check("tripwire: a fixture-data edit is neither a test change nor source (integ-#7)",
          "tests/fixtures/test_cases.json" not in tests
          and "tests/fixtures/test_cases.json" not in src
          and "tests/test_pay.py" in tests and "src/pay.py" in src, (src, tests))


# ---------------------------------------------------------------- red_lock (auto-lock)
def test_red_lock():
    s = "red_lock.py"

    def bash(cmd, response):
        ev = {"tool_name": "Bash", "tool_input": {"command": cmd}}
        if response is not None:
            ev["tool_response"] = response
        return ev

    def run_in(d, event):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        # redlock defaults OFF since v1.32.0; this suite calibrates its BEHAVIOR, so it
        # opts in explicitly (same split as _OPT_IN above — "does it work" vs "is it on").
        env.update(_OPT_IN.get(s, {}))
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=json.dumps(event), capture_output=True, text=True,
                           cwd=d, env=env, timeout=20)
        return p

    def read_json(d, rel):
        path = os.path.join(d, ".claude", rel)
        if not os.path.isfile(path):
            return {}
        with open(path) as fh:
            return json.load(fh)

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        os.makedirs(os.path.join(d, "tests"), exist_ok=True)
        tf = os.path.join(d, "tests", "test_new.py")
        with open(tf, "w") as fh:
            fh.write("def test_x():\n    assert False\n")

        # 1. test-file write -> pending recorded
        p = run_in(d, write(tf, "def test_x():\n    assert False\n"))
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        check("redlock: test-file write records pending",
              p.returncode == 0 and os.path.join("tests", "test_new.py") in pend,
              (p.returncode, pend))

        # 2. non-test write -> NOT pending
        src = os.path.join(d, "app.py")
        with open(src, "w") as fh:
            fh.write("x = 1\n")
        run_in(d, write(src, "x = 1\n"))
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        check("redlock: source write not pending", "app.py" not in pend, pend)

        # 3. failing test run -> pending file LOCKED + journaled + announced
        p = run_in(d, bash("python -m pytest tests/ -q", "1 failed, 2 passed in 0.1s"))
        lock = read_json(d, "tdd-lock.json").get("files", {})
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        jpath = os.path.join(d, ".claude", "tdd-lock-journal.jsonl")
        journal = open(jpath).read() if os.path.isfile(jpath) else ""
        check("redlock: red run locks the pending test",
              os.path.join("tests", "test_new.py") in lock and not pend,
              (lock, pend))
        check("redlock: auto-lock journaled + announced",
              "auto_lock_red" in journal and p.returncode == 1
              and "auto-locked" in p.stderr,
              (p.returncode, p.stderr[:120], journal[:120]))

        # 4. the LOCKED file is now defended by lock_guard (end-to-end) —
        # ANY edit to a locked file is blocked, so neutral strings suffice.
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "lock_guard.py")],
                           input=json.dumps(edit(tf, "alpha", "beta")),
                           capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("redlock: guard blocks an edit to the auto-locked test",
              p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr[:120]))

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        os.makedirs(os.path.join(d, "tests"), exist_ok=True)
        tf = os.path.join(d, "tests", "test_g.py")
        with open(tf, "w") as fh:
            fh.write("def test_g():\n    assert add(1, 1) == 2\n")
        run_in(d, write(tf, "def test_g():\n    assert add(1, 1) == 2\n"))

        # 5. GREEN run -> pending cleared, NO lock
        run_in(d, bash("pytest -q", "3 passed in 0.2s"))
        check("redlock: green run clears pending without locking",
              not read_json(d, "tdd-pending-red.json").get("files", {})
              and not read_json(d, "tdd-lock.json").get("files", {}),
              (read_json(d, "tdd-pending-red.json"), read_json(d, "tdd-lock.json")))

        # 6. a NON-test command with failure text -> nothing happens
        run_in(d, write(tf, "def test_g():\n    assert add(1, 1) == 2\n"))
        run_in(d, bash("cat build.log", "1 failed, something"))
        check("redlock: non-test command never locks",
              not read_json(d, "tdd-lock.json").get("files", {}),
              read_json(d, "tdd-lock.json"))

        # 7. test run with NO tool_response -> fail-open (no lock, pending kept)
        run_in(d, bash("pytest -q", None))
        check("redlock: missing tool_response is fail-open",
              not read_json(d, "tdd-lock.json").get("files", {})
              and read_json(d, "tdd-pending-red.json").get("files", {}),
              (read_json(d, "tdd-lock.json"), read_json(d, "tdd-pending-red.json")))


def test_fixture_guard():
    """A (2026-08-15): warn when an EXPECTED ANSWER in a test-data file is rewritten or
    removed — the gap weakening_guard (test CODE) is blind to. Scoped to answer-value
    changes (David): adding cases / editing non-answer fields is SILENT, or the guard is
    noise. Bypass-oriented, both directions, INCLUDING the unparseable case (GLM residual-2:
    the size-shrink fallback is where a malformed edit can false-positive or slip)."""
    s = "fixture_guard.py"

    def drive(d, event):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        return subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                              input=json.dumps(event), capture_output=True, text=True,
                              cwd=d, env=env, timeout=20)

    def warn(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 1 and "fixtureguard" in p.stderr, (p.returncode, p.stderr[:90]))

    def silent(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 0 and p.stderr == "", (p.returncode, p.stderr[:90]))

    def edit(fp, old, new):
        return {"tool_name": "Edit", "tool_input": {"file_path": fp, "old_string": old,
                                                    "new_string": new}}
    def write(fp, content):
        return {"tool_name": "Write", "tool_input": {"file_path": fp, "content": content}}
    def bash(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        fx = os.path.join(d, "tests", "fixtures")
        os.makedirs(fx)
        tc = os.path.join(fx, "test_cases.json")
        CASES = '[{"input": "a", "output": "5"}, {"input": "b", "output": "6"}]'
        def reset():
            with open(tc, "w") as fh:
                fh.write(CASES)

        # --- WARN direction (answer changed / case removed) ---
        reset(); warn("fixture: output value rewritten warns", d,
                      edit(tc, '"output": "5"', '"output": "31337"'))
        reset(); warn("fixture: a case deleted warns", d,
                      edit(tc, ', {"input": "b", "output": "6"}', ''))
        reset(); warn("fixture: Write with a case removed warns", d,
                      write(tc, '[{"input": "a", "output": "5"}]'))
        reset(); warn("fixture: Write rewriting an answer warns", d,
                      write(tc, '[{"input": "a", "output": "999"}, {"input": "b", "output": "6"}]'))
        # golden bare-list (answer by PATH, no key to signal on)
        gold = os.path.join(fx, "golden.json")
        with open(gold, "w") as fh:
            fh.write('[1, 2, 3]')
        warn("golden: bare-list value change warns (answer by path)", d,
             edit(gold, "2, 3", "2, 99"))
        # Bash structural shapes
        reset(); warn("fixture/sh: rm warns", d, bash("rm tests/fixtures/test_cases.json"))
        reset(); warn("fixture/sh: redirect-overwrite warns", d,
                      bash('echo "[]" > tests/fixtures/test_cases.json'))
        reset(); warn("fixture/sh: git rm warns", d, bash("git rm tests/fixtures/test_cases.json"))
        reset(); warn("fixture/sh: git mv warns", d,
                      bash("git mv tests/fixtures/test_cases.json tests/fixtures/renamed.json"))
        reset(); warn("fixture/sh: mv-over an existing fixture warns", d,
                      bash("mv /tmp/x tests/fixtures/test_cases.json"))
        reset(); warn("fixture/sh: sed -i warns", d,
                      bash("sed -i 's/5/9/' tests/fixtures/test_cases.json"))
        # unparseable value-removal (malformed) that SHRINKS -> warn (size fallback)
        mal = os.path.join(fx, "broken.json")
        with open(mal, "w") as fh:
            fh.write('{"output": "5", broken not json at all, "extra": "padding here to be long"}')
        warn("fixture: unparseable edit that SHRINKS warns (size fallback)", d,
             edit(mal, ', "extra": "padding here to be long"', ''))

        # --- SILENT direction (authoring: additions, non-answer edits, reads) ---
        reset(); silent("fixture: appending a new case is silent", d,
                        edit(tc, ']', ', {"input": "c", "output": "9"}]'))
        reset(); silent("fixture: prepending a new case is silent", d,
                        edit(tc, '[{"input": "a"', '[{"input": "c", "output": "9"}, {"input": "a"'))
        reset(); silent("fixture: editing a non-answer (input) field is silent", d,
                        edit(tc, '"input": "a"', '"input": "z"'))
        reset(); silent("fixture: reordering cases is silent", d,
                        write(tc, '[{"input": "b", "output": "6"}, {"input": "a", "output": "5"}]'))
        silent("fixture: creating a NEW fixture file is silent", d,
               write(os.path.join(fx, "brand_new.json"), '[{"input": "x", "output": "1"}]'))
        silent("fixture: a .snap file is snapshot territory, not ours", d,
               edit(os.path.join(fx, "x.snap"), "a", "b"))
        # a data file OUTSIDE any test path is not a fixture
        cfg = os.path.join(d, "config", "settings.json")
        os.makedirs(os.path.dirname(cfg)); open(cfg, "w").write('{"port": 8080}')
        silent("fixture: a non-test-path data file is not a fixture", d,
               edit(cfg, '8080', '9090'))
        reset(); silent("fixture/sh: reading a fixture (cat) is silent", d,
                        bash("cat tests/fixtures/test_cases.json"))
        # unparseable, SAME-ish length (a malformed-legit reformat) -> silent, NOT a FP
        with open(mal, "w") as fh:
            fh.write('{"output": "5", broken not json, "k": "v"}')
        silent("fixture: unparseable reformat that does NOT shrink is silent (no FP)", d,
               edit(mal, 'broken not json', 'broken  not  json'))


def test_basename_roster_parity():
    """U1 (2026-08-15): the lock-state / verifier / guard basename rosters have ONE owner
    (host_contract). Before this, lock_guard.py carried its own copies and they had
    DIVERGED live: host_contract had `lock-transaction.lock` but not `pending-red.json`;
    the lock_guard copy was the mirror image — so a `sed -i …/lock-transaction.lock`
    slipped the Bash leg (its needles) and an Edit of `pending-red.json` slipped the Edit
    leg (host_contract._surface). Both are the lock's own state; editing either self-unlocks.
    This test pins the two modules identical AND pins each roster complete against the
    filename constants / real guard roster it claims to cover."""
    import importlib.util as _il

    def _load(name, path):
        spec = _il.spec_from_file_location(name, path)
        mod = _il.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    hc = _load("host_contract", os.path.join(PLUGIN, "bin", "host_contract.py"))
    tlg = _load("lock_guard", os.path.join(HOOKS, "lock_guard.py"))

    # parity — the two modules can never diverge again (same objects)
    check("lock-state roster: one owner (lock_guard uses host_contract's)",
          tlg._LOCK_STATE_BASENAMES == hc.LOCK_STATE_BASENAMES, "diverged")
    check("verifier roster: one owner", tlg._VERIFIER_BASENAMES == hc.VERIFIER_BASENAMES)
    check("guard roster: one owner", tlg._GUARD_BASENAMES == hc.GUARD_BASENAMES)

    # completeness — every lock-state FILENAME constant is in the roster (catches the
    # missing `pending-red.json`, the live gap this deliverable fixes)
    for const in (hc.LOCK_FILENAME, hc.EVENTS_FILENAME, hc.PENDING_FILENAME,
                  hc.TRANSACTION_FILENAME):
        check("lock-state roster contains the {} constant".format(const),
              const in hc.LOCK_STATE_BASENAMES, sorted(hc.LOCK_STATE_BASENAMES))

    # the Edit-leg seam directly: pending-red.json must classify as lockstate (RED before
    # the fix — host_contract._surface's set omitted it)
    check("canonical _surface classifies pending-red.json as lockstate",
          hc._surface("pending-red.json", {"files": {}}) == "lockstate",
          hc._surface("pending-red.json", {"files": {}}))
    check("canonical _surface classifies lock-transaction.lock as lockstate",
          hc._surface("lock-transaction.lock", {"files": {}}) == "lockstate")

    # guard roster completeness — every BLOCKING/registered guard is self-protected
    # (tag_guard.py was in NEITHER copy: a blocking guard editable while a lock holds)
    for guard in ("tag_guard.py", "exitcode_guard.py", "exhaustive_claim_guard.py"):
        check("guard roster self-protects {}".format(guard),
              guard in hc.GUARD_BASENAMES, sorted(hc.GUARD_BASENAMES))


def test_lock_shell():
    """F1 (shell channel) + F2 (lock self-protection) for lock_guard.py.

    A locked test the agent can rewrite with `sed -i` / `> file` / `git checkout`, or a lock
    file it can `rm`, is a lock in name only. These planted bypasses MUST block; reads and the
    sanctioned unlock MUST pass (a guard that wedges legitimate work is the adoption killer)."""
    s = "lock_guard.py"

    def drive(d, event):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        return subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                              input=json.dumps(event), capture_output=True, text=True,
                              cwd=d, env=env, timeout=20)

    def bash_ev(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    def setup_lock(d, files=("tests/test_pay.py",)):
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        for f in files:
            fp = os.path.join(d, f)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w") as fh:
                fh.write("def test_pay():\n    assert charge() == 10\n")
        with open(os.path.join(d, ".claude", "tdd-lock.json"), "w") as fh:
            json.dump({"files": {f: {"locked_at": "t"} for f in files}}, fh)

    def block(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr[:110]))

    def allow(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 0 and p.stderr == "", (p.returncode, p.stderr[:110]))

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        setup_lock(d)
        # F1 — shell WRITE bypasses on a locked test must block
        block("lock/sh: sed -i on locked test blocks", d, bash_ev("sed -i 's/10/9/' tests/test_pay.py"))
        block("lock/sh: redirect-overwrite locked test blocks", d, bash_ev('echo "def test_pay(): pass" > tests/test_pay.py'))
        block("lock/sh: append-redirect locked test blocks", d, bash_ev("cat foo >> tests/test_pay.py"))
        block("lock/sh: git checkout -- locked test blocks", d, bash_ev("git checkout -- tests/test_pay.py"))
        block("lock/sh: git checkout . (revert-all) blocks", d, bash_ev("git checkout ."))
        block("lock/sh: git restore . blocks", d, bash_ev("git restore ."))
        block("lock/sh: rm locked test blocks", d, bash_ev("rm tests/test_pay.py"))
        block("lock/sh: mv over locked test blocks", d, bash_ev("mv /tmp/x tests/test_pay.py"))
        block("lock/sh: inline python open(...,'w') blocks", d, bash_ev("python3 -c \"open('tests/test_pay.py','w').write('')\""))
        # F1 — READS and legitimate runs must NOT block (adoption killer if they do)
        allow("lock/sh: cat locked test is allowed", d, _bash("cat tests/test_pay.py"))
        allow("lock/sh: run locked test is allowed", d, bash_ev("python -m pytest tests/test_pay.py -q"))
        allow("lock/sh: run + redirect OUTPUT elsewhere is allowed", d, bash_ev("pytest tests/test_pay.py -q > /tmp/out.log"))
        allow("lock/sh: git checkout a branch is allowed", d, bash_ev("git checkout main"))
        # F1 — verifier surface + enforcement via shell
        block("lock/sh: sed -i on conftest blocks (H5)", d, bash_ev("sed -i 's/a/b/' conftest.py"))
        block("lock/sh: rm on a guard hook blocks", d, bash_ev("rm .claude/hooks/scripts/lock_guard.py"))
        # F2 — the lock's own state cannot be removed/rewritten to self-unlock
        block("lock/sh: rm tdd-lock.json blocks (F2)", d, bash_ev("rm .claude/tdd-lock.json"))
        block("lock/sh: overwrite tdd-lock.json blocks (F2)", d, bash_ev("echo '{}' > .claude/tdd-lock.json"))
        block("lock/sh: truncate the journal blocks (F2)", d, bash_ev("truncate -s0 .claude/tdd-lock-journal.jsonl"))
        # U1 — the transaction lock is lock state too; editing it self-unlocks (RED before
        # the roster unification: the Bash-leg needle set omitted lock-transaction.lock)
        block("lock/sh: sed -i on lock-transaction.lock blocks (U1)", d, bash_ev("sed -i 's/a/b/' .claude/tdd-playbook/lock-transaction.lock"))
        block("lock/sh: rm pending-red.json blocks (U1)", d, bash_ev("rm .claude/tdd-playbook/pending-red.json"))
        block("lock/edit: editing tdd-lock.json blocks (F2)", d, edit(os.path.join(d, ".claude", "tdd-lock.json"), "a", "b"))
        block("lock/edit: editing hooks.json blocks", d, edit(os.path.join(d, ".claude", "hooks", "hooks.json"), "a", "b"))
        # the SANCTIONED unlock must pass (references tdd_lock.py, not the state file literal)
        allow("lock/sh: journaled unlock via tdd_lock.py is allowed", d,
              bash_ev('python3 /plug/bin/tdd_lock.py unlock --reason "impl done"'))

        # ---- v1.28 ALLOW-DIRECTION CALIBRATION (§13 applied to the guard itself) -------
        # A guard's claim about ITSELF is an unverified claim, in BOTH directions. The
        # block rows above were always tested; the ALLOW half never was — so the guard
        # grew three false-positive classes its own docstring forbids ("Reads are always
        # fine"). These are REAL blocks from the 2026-08-05/06 session, frozen as fixtures:
        # each blocked work the contract permits. (Cheliped's field-report defect 7 is the
        # mirror image — a guard whose docstring claimed coverage it never had.)
        allow("lock/sh FP1 (2026-08-06): a python loop var named `ln` is not the `ln` "
              "command — reading the lock journal must not block", d,
              bash_ev("python3 -c \"\nfor ln in open('.claude/tdd-lock-journal.jsonl'):"
                      "\n    print(ln)\""))
        allow("lock/sh FP2 (2026-08-05): an inline write to an UNRELATED file must not "
              "block merely because a protected path appears elsewhere in the command", d,
              bash_ev("python3 - <<'EOF'\nopen('notes.txt', 'w').write('x')\nEOF\n"
                      "python3 tests/test_pay.py"))
        allow("lock/sh FP3 (2026-08-06): a revert inside a scratch dir OUTSIDE the project "
              "root is not a repo revert", d,
              bash_ev("cd /tmp/scratch-clone && git checkout -q ."))
        allow("lock/sh FP4 (2026-08-05): re-LOCKING files is strengthening, not weakening "
              "— naming them cannot be the trigger", d,
              bash_ev("python3 /plug/bin/tdd_lock.py lock tests/test_pay.py"))
        # FP2 bit me while writing this very block: the fixture STRING above contains a
        # lock-state basename and the authoring command also wrote a file, so the guard
        # blocked authoring its own regression test. I split the literal to get the fixture
        # written, then rejoined it once the target-aware fix landed — the rejoined form is
        # the real command shape, and the fact that it can now be written at all is itself
        # the fix working.

        # …and the block direction must survive every one of those narrowings:
        block("lock/sh: inline write TO the locked path still blocks (FP2 narrowing is "
              "target-aware, not blanket)", d,
              bash_ev("python3 - <<'EOF'\nopen('tests/test_pay.py', 'w').write('')\nEOF"))
        block("lock/sh: a revert INSIDE the project still blocks (FP3 narrowing is "
              "containment, not amnesty)", d, bash_ev("cd tests && git checkout ."))
        block("lock/sh: `rm` in command position still blocks (FP1 narrowing is position, "
              "not deletion of the verb)", d, bash_ev("rm -f tests/test_pay.py"))

    with tempfile.TemporaryDirectory() as d2:
        d2 = os.path.realpath(d2)  # NO lock active
        allow("lock/sh: no lock -> rm test is zero-cost allow", d2, bash_ev("rm tests/test_pay.py"))


# ---------------------------------------------------------------- yield event log (R4/D4)
def test_yield_logging():
    """PLANTED (D4): every guard outcome flows through _common.emit(), so ONE logging call
    there gives the yield instrument its data — a guard silently absent from the log would
    read as zero-yield, which is a retirement trigger. Logging must never break enforcement."""
    s = "weakening_guard.py"
    tf = "tests/test_pay.py"
    weaken = edit(tf, "assert total == 5\nassert ok", "assert ok")

    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log})
        rows = [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []
        check("yield: block event logged with gate + event + findings",
              rc == 2 and len(rows) == 1 and rows[0].get("gate") == "testweaken"
              and rows[0].get("event") == "block" and rows[0].get("findings", 0) >= 1,
              (rc, rows))

        # v1.34.0 D5 — every row carries a HOST label from host-runtime-provided signals
        # (CLAUDE_PROJECT_DIR is set by the Claude Code runtime itself; the Codex adapter
        # sets TDD_PLAYBOOK_PROJECT_ROOT — adapters/codex/pre_tool_test_lock.py:32).
        # NEVER suppression: an unrecognised context is stamped `unknown` and still
        # logged — silent non-logging is the fatal-flaw shape the readable-surface
        # re-review removed, and _common's own invariant is that no producer silently
        # drops out of the record. All three directions pinned EXPLICITLY (an inherited
        # session env would make this pass-at-home / fail-in-CI):
        log3 = os.path.join(d, "host.jsonl")
        for env_extra, want in (
                ({"CLAUDE_PROJECT_DIR": d}, "claude"),
                ({"TDD_PLAYBOOK_PROJECT_ROOT": d}, "codex"),
                ({}, "unknown")):
            env = {"TDD_PLAYBOOK_YIELD_LOG": log3}
            env.update(env_extra)
            hp = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.util, os, sys\n"
                 "os.environ.pop('CLAUDE_PROJECT_DIR', None)\n"
                 "os.environ.pop('TDD_PLAYBOOK_PROJECT_ROOT', None)\n"
                 + "".join("os.environ[{!r}] = {!r}\n".format(k, v)
                           for k, v in env.items())
                 + "spec = importlib.util.spec_from_file_location('_common', {!r})\n"
                   "m = importlib.util.module_from_spec(spec)\n"
                   "spec.loader.exec_module(m)\n"
                   "m.log_yield_event('readable-surface', 'usage', "
                   "{{'scenario': 'full'}}, source='cli')\n".format(
                       os.path.join(HOOKS, "_common.py"))],
                capture_output=True, text=True, timeout=20)
            hrows = ([json.loads(ln) for ln in open(log3)]
                     if os.path.isfile(log3) else [])
            check("yield: host stamped `{}` from its runtime signal, row LOGGED".format(
                      want),
                  hp.returncode == 0 and hrows and hrows[-1].get("host") == want,
                  (hp.returncode, hp.stderr[-120:], hrows[-1:] or "no rows"))

        def rows_of():
            return [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []

        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                               "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "warn"})
        rows = rows_of()
        check("yield: warn-mode event logged as warn",
              rc == 1 and len(rows) == 2 and rows[1].get("event") == "warn", (rc, rows))

        # a CLEAN pass adds no row (the log records friction, not traffic)
        rc, _o, _e = run(s, edit(tf, "assert ok", "assert ok\nassert total == 5"),
                         env_extra={"TDD_PLAYBOOK_YIELD_LOG": log})
        rows = rows_of()
        check("yield: clean pass logs nothing", rc == 0 and len(rows) == 2, (rc, rows))

        # PLANTED: an unwritable log path (parent is a FILE) must never weaken enforcement
        with open(os.path.join(d, "nope"), "w") as fh:
            fh.write("a file, not a dir")
        rc, _o, e = run(s, weaken,
                        env_extra={"TDD_PLAYBOOK_YIELD_LOG": os.path.join(d, "nope", "x",
                                                                          "y.jsonl")})
        check("yield: unwritable log never breaks the block",
              rc == 2 and "assertions dropped" in e, (rc, e))

    # G5: the suite's own runs land in the temp default, not the repo tree
    check("yield: suite isolation — temp default log received this suite's events",
          os.path.isfile(_YIELD_DEFAULT) and os.path.getsize(_YIELD_DEFAULT) > 0,
          _YIELD_DEFAULT)

    # PLANTED (hole 2, 2026-07-28): demotion-to-off must not be a SILENT kill switch — a
    # finding suppressed by off-mode leaves a 'suppressed' trace in the yield log, so a
    # muzzled gate is distinguishable from a quiet one
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                               "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
        rows = [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []
        check("suppressed: off-mode finding still leaves a trace (muzzled != quiet)",
              rc == 0 and len(rows) == 1 and rows[0].get("event") == "suppressed"
              and rows[0].get("gate") == "testweaken", (rc, rows))
        # a clean pass under off-mode logs nothing (no findings -> nothing suppressed)
        rc, _o, _e = run(s, edit(tf, "assert ok", "assert ok\nassert x == 1"),
                         env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                    "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
        rows = [json.loads(ln) for ln in open(log)]
        check("suppressed: clean pass under off-mode logs nothing",
              rc == 0 and len(rows) == 1, (rc, rows))

    # PLANTED (hole 2): this repo's settings must carry no standing DEMOTIONS — an
    # env-block demotion is the persistent, invisible variant of the kill switch.
    # 2026-08-13, found by its own first false positive: the check used to flag ANY
    # TDD_PLAYBOOK_HOOK_* env var — the variable's PRESENCE, a proxy — and so REDded the
    # gate when exitcode (shipped default: off) was promoted to warn on measured evidence
    # (43 suppressed findings in one cycle, >=3 real). Direction is the fact: an override
    # WEAKER than the shipped default is a demotion; an override at or above it is an
    # opt-in, which is exactly what the v1.32.0 retirement invited.
    import importlib.util as _il2
    _sp2 = _il2.spec_from_file_location("_common", os.path.join(HOOKS, "_common.py"))
    _cm2 = _il2.module_from_spec(_sp2)
    _sp2.loader.exec_module(_cm2)
    _strength = {"off": 0, "warn": 1, "block": 2}

    def _standing_demotions(envblock):
        out = []
        for k, v in envblock.items():
            if not k.startswith("TDD_PLAYBOOK_HOOK_"):
                continue
            gate = k[len("TDD_PLAYBOOK_HOOK_"):].lower()
            shipped = _cm2._DEFAULT_MODES.get(gate)
            if shipped is None:
                out.append("{}={} (names no shipped guard)".format(k, v))
            elif _strength.get(str(v), -1) < _strength.get(shipped, 0):
                out.append("{}={} (shipped default: {})".format(k, v, shipped))
        return out

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HOOKS))))
    demotions = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        sp = os.path.join(repo_root, rel)
        if os.path.isfile(sp):
            try:
                envblock = json.load(open(sp)).get("env", {}) or {}
            except ValueError:
                envblock = {}
            demotions += ["{}: {}".format(rel, d) for d in _standing_demotions(envblock)]
    check("no standing guard DEMOTIONS in settings env blocks (direction-aware)",
          demotions == [], demotions)
    # PLANTED both directions — the check must fail on a real demotion and stay quiet on
    # a promotion (the motivating false positive, frozen):
    check("planted: block->warn demotion IS flagged",
          _standing_demotions({"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "warn"}) != [])
    check("planted: default-off guard promoted to warn is NOT flagged (the 2026-08-13 "
          "false positive)",
          _standing_demotions({"TDD_PLAYBOOK_HOOK_EXITCODE": "warn"}) == [])
    check("planted: unknown guard name IS flagged (fail closed)",
          _standing_demotions({"TDD_PLAYBOOK_HOOK_NOTAGUARD": "off"}) != [])


# ---------------------------------------------------------------- guards heartbeat (H8)
def test_guards_heartbeat():
    """PLANTED (H8, live incident 2026-07-28): the plugin was disabled user-wide by a
    mis-click in ANOTHER repo and the whole guard layer went dark for a full working day —
    three releases shipped with zero mechanical enforcement and no alarm. Committed !=
    deployed != RUNNING applies to the guards themselves: a hook that fires on every user
    prompt must leave a heartbeat, so dark-detection has a signal to check."""
    with tempfile.TemporaryDirectory() as d:
        hb = os.path.join(d, "heartbeat")
        rc, _o, _e = run("intent_nudge.py", {"prompt": "let's build the new export feature"},
                         env_extra={"TDD_PLAYBOOK_HEARTBEAT": hb,
                                    "TDD_PLAYBOOK_NUDGE_STATE_DIR": d})
        check("heartbeat: written on UserPromptSubmit (guards provably LIVE)",
              os.path.isfile(hb) and open(hb).read().strip()[:4].isdigit(), (rc, hb))

        # a prompt that does NOT trigger the nudge still beats the heart (liveness is
        # about the hook RUNNING, not about the nudge firing)
        hb2 = os.path.join(d, "heartbeat2")
        rc, _o, _e = run("intent_nudge.py", {"prompt": "good morning"},
                         env_extra={"TDD_PLAYBOOK_HEARTBEAT": hb2,
                                    "TDD_PLAYBOOK_NUDGE_STATE_DIR": d})
        check("heartbeat: beats even on non-intent prompts", os.path.isfile(hb2), rc)

        # PLANTED: unwritable heartbeat path must never break the hook
        with open(os.path.join(d, "blocked"), "w") as fh:
            fh.write("file not dir")
        rc, _o, _e = run("intent_nudge.py", {"prompt": "fix the bug in calc"},
                         env_extra={"TDD_PLAYBOOK_HEARTBEAT":
                                    os.path.join(d, "blocked", "x", "hb"),
                                    "TDD_PLAYBOOK_NUDGE_STATE_DIR": d})
        check("heartbeat: unwritable path never breaks the hook", rc in (0, 1), rc)


# ------------------------------------------------------- guard roster (derived, D-B)
# The v1.32.0 policy pin — the one LITERAL expectation in this family, kept literal on
# purpose (§12: a derived check compared against the filter it describes cannot reveal
# drift; these sets are the roster the machinery cannot drift with). Everything else —
# which scripts exist, their short names, their modes, the prose copies — is DERIVED.
# ONE literal home for the guard roster (arch-F9): script -> mode, compared against the
# machinery-derived {script: resolve_mode(NAME)}. Three live modes now (block/off/warn), so
# a per-mode literal set would grow one set per mode and the advisory/warn ambiguity would
# be spelled, not derived — a single dict keyed on the FACT (the mode) is the fix.
EXPECTED_MODES = {
    "weakening_guard": "block", "lock_guard": "block",
    "snapshot_guard": "block", "tag_guard": "block",
    "exitcode_guard": "off", "overmock_guard": "off", "exhaustive_claim_guard": "off",
    "flaky_guard": "off", "red_lock": "off",
    "fixture_guard": "warn",
    # v1.46.0 — the analysis-turn seam. OFF by the same evidence-first rule that retired the
    # five above: at warn its remedy is routed to the user, not the agent it addresses.
    "cite_guard": "off",
}
EXPECTED_ADVISORY = {"build_completion_reminder", "capture", "intent_nudge"}


def _script_short_name(script):
    """AST-read a hook script's module-level NAME constant (None if absent).
    Parsed, never grepped — a NAME in a docstring or comment must not count (§12)."""
    with open(os.path.join(HOOKS, script + ".py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Name) and target.id == "NAME"
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)):
                    return node.value.value
    return None


_ROSTER_ANCHOR = re.compile(r"blocking guards", re.IGNORECASE)
_GUARD_TOKEN = re.compile(r"[a-z][a-z_]*_guard|red_lock")
_SLASH_RUN = re.compile(r"\b[a-z_]+(?:/[a-z_]+)+\b")
_NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}


def _roster_chunk(text):
    """The roster sentence region: from just before the anchor phrase (the count word
    precedes it) through the span holding both name lists. None when the anchor is
    missing — the caller must refuse a vacuous pass (§4a)."""
    m = _ROSTER_ANCHOR.search(text)
    return None if m is None else text[max(0, m.start() - 30):m.start() + 500]


def _roster_problems(chunk, blocking, optin, warn, shorts, machinery_tokens):
    """Pin one prose roster chunk against the derived partition. Pure function so the
    planted fixtures exercise it directly (release discipline: planted inputs, always).

    An opt-in guard may appear by script name OR by its NAME short form (CLAUDE.md
    writes `exitcode/overmock/...`, README writes `exitcode_guard, ...`). Directions:
    missing (a real guard absent from prose — blocking, opt-in, OR warn), phantom (a
    guard-shaped token machinery does not have — BOTH dialects: `*_guard` names and
    short-name slash-runs, arch F6b), and a stale COUNT word (arch F6a: five guards behind
    a sentence still saying "four" is green under a names-only pin — the number is asserted
    against len(blocking), the one fact the anchor itself cannot see)."""
    if chunk is None:
        return ["roster anchor 'blocking guards' not found — refusing a vacuous pass"]
    problems = []
    count_word = _NUMBER_WORDS.get(len(blocking))
    if count_word is None:
        problems.append("blocking-guard count {} has no number word — extend "
                        "_NUMBER_WORDS".format(len(blocking)))
    elif not re.search(count_word + r"\s+blocking guards", chunk, re.IGNORECASE):
        problems.append("stale roster count: prose does not say '{} blocking guards' "
                        "(machinery has {})".format(count_word, len(blocking)))
    for script in sorted(blocking):
        if script not in chunk:
            problems.append("missing blocking guard in prose: " + script)
    for script in sorted(optin):
        if script not in chunk and shorts[script] not in chunk:
            problems.append("missing opt-in guard in prose: {} (or '{}')".format(
                script, shorts[script]))
    for script in sorted(warn):
        if script not in chunk and shorts[script] not in chunk:
            problems.append("missing warn guard in prose: {} (or '{}')".format(
                script, shorts[script]))
    for token in _GUARD_TOKEN.findall(chunk):
        if token not in machinery_tokens:
            problems.append("phantom guard in prose: " + token)
    for run in _SLASH_RUN.findall(chunk):
        tokens = run.split("/")
        if any(t in machinery_tokens for t in tokens):
            for t in tokens:
                if t not in machinery_tokens:
                    problems.append("phantom guard in prose (short-name run): " + t)
    return problems


def test_guard_roster_derived_and_pinned():
    """D-B (review-as-judgment-surface plan, 2026-08-14): the guard roster is DERIVED
    from machinery — hooks.json's registered scripts × each script's NAME constant ×
    _common._DEFAULT_MODES — and the prose copies in CLAUDE.md and README.md are pinned
    against it. Replaces the hardcoded name tuples this suite carried at the old
    test_retired_advisory_defaults loops, so the roster has ONE literal home (the
    policy pin above) instead of five prose copies."""
    import importlib.util as _il
    spec = _il.spec_from_file_location("_common", os.path.join(HOOKS, "_common.py"))
    common = _il.module_from_spec(spec)
    spec.loader.exec_module(common)
    hp_spec = _il.spec_from_file_location(
        "host_parity", os.path.join(PLUGIN, "bin", "host_parity.py"))
    host_parity = _il.module_from_spec(hp_spec)
    hp_spec.loader.exec_module(host_parity)

    scanned = host_parity.canonical_inventory(REPO)["guards"]
    partition, advisory, shorts = {}, set(), {}
    for script in sorted(scanned):
        short = _script_short_name(script)
        if short in common._DEFAULT_MODES:
            partition[script] = common._DEFAULT_MODES[short]
            shorts[script] = short
        else:
            advisory.add(script)
    blocking = {s for s, m in partition.items() if m == "block"}
    optin = {s for s, m in partition.items() if m == "off"}
    warn = {s for s, m in partition.items() if m == "warn"}

    # machinery vs the ONE policy pin — dict equality on the FACT (arch-F9), not per-mode
    # floors. A guard whose mode drifts, or whose tier is mis-spelled, fails here.
    check("derived partition equals the policy pin (script -> mode)",
          partition == EXPECTED_MODES, sorted(partition.items()))
    check("advisory remainder is exactly the known non-guard set",
          advisory == EXPECTED_ADVISORY, sorted(advisory))
    check("every _DEFAULT_MODES key is claimed by exactly one registered script",
          sorted(shorts.values()) == sorted(common._DEFAULT_MODES), sorted(shorts.values()))
    print("  roster: scanned {} hooks.json scripts · {} block · {} opt-in · {} warn · "
          "advisory {}".format(len(scanned), len(blocking), len(optin), len(warn),
                               len(advisory)))

    # prose pins, both files, derived — never a hardcoded list here
    machinery_tokens = set(partition) | set(shorts.values())
    for name in ("CLAUDE.md", "README.md"):
        text = open(os.path.join(REPO, name), encoding="utf-8").read()
        problems = _roster_problems(_roster_chunk(text), blocking, optin, warn, shorts,
                                    machinery_tokens)
        check("{} guard roster matches machinery".format(name), problems == [], problems)

    # PLANTED fixtures — the red-first proof, frozen (a pin that cannot fail is décor)
    good = ("...the four blocking guards (weakening_guard, lock_guard, "
            "snapshot_guard, tag_guard) plus the opt-in ones (exitcode_guard, "
            "exhaustive_claim_guard, overmock_guard, flaky_guard, red_lock, "
            "cite_guard) and the warn-by-default fixture_guard...")
    def rp(chunk, bl=None, op=None, wn=None, sh=None, mt=None):
        return _roster_problems(chunk, bl if bl is not None else blocking,
                                op if op is not None else optin,
                                wn if wn is not None else warn,
                                sh if sh is not None else shorts,
                                mt if mt is not None else machinery_tokens)
    check("PLANTED: clean roster prose passes", rp(good) == [], rp(good))
    check("PLANTED: missing blocking guard is caught",
          any("missing blocking guard" in p and "tag_guard" in p
              for p in rp(good.replace(", tag_guard)", ")"))))
    check("PLANTED: missing WARN guard is caught",
          any("missing warn guard" in p and "fixture_guard" in p
              for p in rp(good.replace(" and the warn-by-default fixture_guard", ""))))
    check("PLANTED: phantom guard in prose is caught",
          any("phantom" in p and "quantum_guard" in p
              for p in rp(good.replace("cite_guard)", "cite_guard, quantum_guard)"))))
    grown = dict(shorts, new_guard="newguard")
    check("PLANTED: newly-registered guard absent from prose is caught",
          any("missing opt-in guard" in p and "new_guard" in p
              for p in rp(good, op=optin | {"new_guard"}, sh=grown,
                          mt=machinery_tokens | {"new_guard"})))
    five_named = good.replace("tag_guard)", "tag_guard, fifth_guard)")
    check("PLANTED: stale count word ('four' over five guards) is caught",
          any("stale roster count" in p
              for p in rp(five_named, bl=blocking | {"fifth_guard"}, sh=grown,
                          mt=machinery_tokens | {"fifth_guard"})))
    claude_dialect = ("...the four blocking guards: weakening_guard, "
                      "lock_guard, snapshot_guard, tag_guard; plus the opt-in "
                      "exitcode/overmock/quantum/flaky/red_lock, which ship OFF; plus "
                      "fixture_guard...")
    check("PLANTED: phantom short name inside the slash-run is caught",
          any("short-name run" in p and "quantum" in p for p in rp(claude_dialect)))
    check("PLANTED: anchor removal refuses a vacuous pass",
          "refusing a vacuous pass" in rp(None)[0])



# ---------------------------------------------- D2: blocking-guard family parity (2026-08-20)
# Four recorded findings are guards firing OUTSIDE their jurisdiction — including the one
# that reached David as "why am I seeing all these hook errors". All four blocking guards
# happen to satisfy both directions today; NOTHING REQUIRED IT of the next one. The
# "CALIBRATED IN BOTH DIRECTIONS" marker on 4 of ~13 hooks is a docstring self-claim, which
# is §13's "the one nobody re-checks".
#
# The allow direction is supplied by ONE SHARED corpus run against EVERY blocking guard,
# rather than a per-guard clean-list. A per-guard list is written by that guard's own author
# and is bounded by the same imagination that wrote the guard; and every recorded false
# positive here is the same failure — the guard acted on something outside its remit.
# lock_guard already implements this rule for itself ("out-of-root is NEVER this guard's
# jurisdiction"); this generalizes one guard's hard-won lesson to the family.

def _bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


def _oo_j():
    """Ordinary work no guard may act on, in the SHIPPED default state. Built at call time
    so the paths are real ones this session would actually touch."""
    home = os.path.expanduser("~")
    return [
        ("reading a test file", _bash("cat tests/test_pay.py")),
        ("running the suite", _bash("python -m pytest -q")),
        ("listing tags read-only", _bash("git tag -l --sort=-v:refname")),
        ("git status", _bash("git status -u")),
        ("grepping prose that merely CONTAINS a trigger word",
         _bash("grep -rn 'snapshot update' docs/")),
        ("writing a memory note (out of root)",
         write(os.path.join(home, ".claude", "projects", "x", "memory", "n.md"), "note")),
        ("writing the plan-mode file (out of root; plan mode's ONLY permitted write)",
         write(os.path.join(home, ".claude", "plans", "p.md"), "plan")),
        ("writing to the session scratchpad (out of root)",
         write(os.path.join(tempfile.gettempdir(), "scratchpad", "s.txt"), "tmp")),
    ]


def _block_rows():
    """BLOCK rows, EXECUTED — one real event per guard that needs no arming. An earlier
    draft of this test declared them as None and never ran them: a "row" that never executes
    proves nothing, which is the proxy this whole span exists to remove.

    Both needles are ASSEMBLED at runtime, the house idiom — build the needle so the
    haystack never holds it. The tag string keeps test_installer's tracked-file scanner from
    matching this file; the snapshot string keeps snapshot_guard from blocking the very test
    that calibrates it. Both blocks were observed live and recorded through guard_note.

    lock_guard is absent by design: it only acts while a lock is HELD, so its block
    direction is a RESOLVED reference (defined + dispatched from main) rather than an
    unarmed event that would pass for the wrong reason."""
    T = "t" + "ag"
    return {
        "weakening_guard": ("an assertion deleted from a test",
                            edit("tests/test_pay.py", "assert total == 5\nx", "x")),
        "snapshot_guard": ("a snapshot re-approval run", _bash("npx jest -" + "u")),
        "tag_guard": ("creating a release " + T, _bash("git {} -a v9.9.9 -m x".format(T))),
    }


BLOCK_BY_REFERENCE = {"lock_guard": "test_lock_shell"}


def parity_problems(blocking_roster, block_rows, block_by_reference, silent_on_shared):
    """PURE — no I/O, no module-global tally, so the planted case below can hand it a
    fabricated member. An earlier design accumulated evidence into a module global as the
    other tests ran; main()'s dispatch order put this test last, so calling it alone would
    have seen an empty tally and passed vacuously."""
    problems = []
    for script in sorted(blocking_roster):
        if script not in block_rows and script not in block_by_reference:
            problems.append(script + ": no BLOCK row — a guard that blocks by default must "
                            "show what it blocks")
        if script not in silent_on_shared:
            problems.append(script + ": no ALLOW evidence — it must stay silent on the "
                            "shared out-of-jurisdiction corpus")
    return problems


def test_blocking_guards_prove_both_directions():
    """§6c FAMILY PARITY over the hook family: enumerated from the REAL registry, so a guard
    promoted to blocking tomorrow owes its allow evidence the same day, with no table for
    anyone to remember to update. Vacuity-guarded — an empty roster REFUSES rather than
    passing over zero members."""
    import importlib.util as _il
    hp_spec = _il.spec_from_file_location(
        "host_parity_d2", os.path.join(PLUGIN, "bin", "host_parity.py"))
    host_parity = _il.module_from_spec(hp_spec)
    hp_spec.loader.exec_module(host_parity)
    spec = _il.spec_from_file_location("_common_d2", os.path.join(HOOKS, "_common.py"))
    common = _il.module_from_spec(spec)
    spec.loader.exec_module(common)

    scanned = host_parity.canonical_inventory(REPO)["guards"]
    blocking = {s for s in scanned
                if common._DEFAULT_MODES.get(_script_short_name(s)) == "block"}
    check("vacuity guard: the blocking roster is non-empty and holds the four known guards",
          blocking >= {"weakening_guard", "lock_guard", "snapshot_guard",
                       "tag_guard"}, sorted(blocking))

    # the ALLOW direction, EXECUTED: every blocking guard, every shared row, silence
    silent = set()
    for script in sorted(blocking):
        noisy = []
        for label, event in _oo_j():
            rc, _o, err = run(script + ".py", event, raw=True)
            if rc != 0:
                noisy.append("{} -> rc={} {}".format(label, rc, err.strip()[:90]))
        check("out of jurisdiction: {} stays silent on ordinary work".format(script),
              not noisy, noisy)
        if not noisy:
            silent.add(script)
    print("  shared corpus: {} rows x {} blocking guards".format(
        len(_oo_j()), len(blocking)))

    # the BLOCK direction, EXECUTED too — narrowing a guard is not amnesty (§13), so the
    # block rows must survive every allow-direction change made here.
    blocks = set()
    for script, (label, event) in sorted(_block_rows().items()):
        rc, _o, _e = run(script + ".py", event, raw=True)
        check("block direction: {} still blocks {}".format(script, label), rc == 2, rc)
        if rc == 2:
            blocks.add(script)

    problems = parity_problems(blocking, blocks, BLOCK_BY_REFERENCE, silent)
    check("every blocking-by-default guard proves BOTH directions", problems == [], problems)

    # the referenced block-direction test must RESOLVE: defined AND dispatched from main
    source = open(os.path.abspath(__file__), encoding="utf-8").read()
    for script, fn in BLOCK_BY_REFERENCE.items():
        tree = ast.parse(source)
        defined = any(isinstance(n, ast.FunctionDef) and n.name == fn for n in tree.body)
        check("{}'s block direction resolves to a DEFINED test ({})".format(script, fn),
              defined)
        check("...that main() actually dispatches ({})".format(fn),
              ("    " + fn + ",") in source or (" " + fn + ",") in source)

    # PLANTED: a guard promoted to blocking with nothing behind it must RED the sweep.
    planted = parity_problems(blocking | {"brand_new_guard"}, blocks,
                              BLOCK_BY_REFERENCE, silent)
    check("PLANTED: a NEW blocking guard with no rows REDs the sweep (this is the whole "
          "deliverable — the four existing guards already pass by diligence)",
          any("brand_new_guard" in p for p in planted), planted)
    check("...naming BOTH missing directions, not just the first",
          len([p for p in planted if "brand_new_guard" in p]) == 2, planted)


# ── D0/D1: the analysis-turn seam ────────────────────────────────────────────
# The house bar is calibration in BOTH directions, and here that is sharpened by the
# TWIN RULE: no "stays silent" row is admissible unless its own one-field-mutated twin
# FIRES, from the same fixture builder, asserted in the same check. Rationale (review
# finding, 2026-08-27): every silent row asserts exit-0-and-no-output, which is the
# guard's DEFAULT behaviour — a fixture that never reaches the detector satisfies all of
# them. The motivating near-miss: `doctor.py` does not exist in this repo and `run()`
# sets no cwd, so E2/E4/E5/E11 would all have gone green on the file-does-not-exist
# branch with the citation logic never executed.

def _tl(**kw):
    """One transcript line."""
    return json.dumps(kw)


def _assistant_text(text):
    return _tl(type="assistant", message={"content": [{"type": "text", "text": text}]})


def _tool_use(name, inp, tid=None):
    blk = {"type": "tool_use", "name": name, "input": inp}
    if tid:
        blk["id"] = tid
    return _tl(type="assistant", message={"content": [blk]})


def _tool_error(tid):
    return _tl(type="user", message={"content": [
        {"type": "tool_result", "tool_use_id": tid, "is_error": True}]})


def _user(text):
    return _tl(type="user", message={"content": text})


def _tool_result(tid):
    return _tl(type="user", message={"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": "ok"}]})


def _write_transcript(d, lines, name="t.jsonl"):
    tp = os.path.join(d, name)
    with open(tp, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return tp


def _cite_run(d, lines, env_extra=None, name="t.jsonl"):
    """Drive cite_guard as a subprocess against a crafted transcript, with the temp dir as
    the project root so file-existence resolves against the FIXTURE tree, not this repo."""
    tp = _write_transcript(d, lines, name)
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(_YIELD_TMP, "cite-yield.jsonl")
    env["TDD_PLAYBOOK_HEARTBEAT"] = os.path.join(_YIELD_TMP, "heartbeat")
    env["CLAUDE_PROJECT_DIR"] = d
    env["TDD_PLAYBOOK_HOOK_CITE"] = "warn"     # opt in: SHIPPED default is off
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, os.path.join(HOOKS, "cite_guard.py")],
                       input=json.dumps({"transcript_path": tp}),
                       capture_output=True, text=True, env=env, timeout=20, cwd=d)
    return p.returncode, p.stderr


def _twin(d, label, silent_lines, flag_lines, expect_in_msg=None):
    """The twin rule: assert the pair together so a fixture that stops reaching the
    detector kills its twin and REDs the suite."""
    src, _ = _cite_run(d, silent_lines)
    frc, fstderr = _cite_run(d, flag_lines)
    ok = (src == 0 and frc == 1)
    if ok and expect_in_msg:
        ok = expect_in_msg in fstderr
    check("twin[{}]: silent stays silent AND its mutated twin FIRES".format(label),
          ok, (label, src, frc, fstderr[:240]))


def test_transcript_module():
    """D0: the shared reader and the ONE tool vocabulary."""
    import importlib.util as _il
    spec = _il.spec_from_file_location("transcript", os.path.join(HOOKS, "transcript.py"))
    tr = _il.module_from_spec(spec)
    spec.loader.exec_module(tr)

    # The vocabulary disagreement this module exists to end.
    check("D0: NotebookEdit is an edit (the three hook-side copies omitted it)",
          "NotebookEdit" in tr.EDIT_TOOLS, sorted(tr.EDIT_TOOLS))
    check("D0: a search is NOT a read — the distinction the whole guard rests on",
          not (tr.SEARCH_TOOLS & tr.READ_TOOLS), (tr.SEARCH_TOOLS, tr.READ_TOOLS))
    # PINNED AGAINST REAL CAPTURES, both hosts. docs/telemetry.md:31 records the cost of
    # getting this wrong once; 47/47 real CC dispatches are `Agent`, and Cheliped's
    # transcript_tool_event emits `Task`. A guard keyed to either alone goes dark on the other.
    check("D0: BOTH hosts' dispatch names are recognised (Agent=CC, Task=Cheliped)",
          {"Agent", "Task"} <= tr.DISPATCH_TOOLS, sorted(tr.DISPATCH_TOOLS))
    check("D0: namespaced subagent_type is stripped to the roster stem",
          tr.normalize_agent_name("tdd-playbook:architecture-adversary")
          == "architecture-adversary"
          and tr.normalize_agent_name("architecture-adversary") == "architecture-adversary",
          tr.normalize_agent_name("tdd-playbook:architecture-adversary"))

    with tempfile.TemporaryDirectory() as d:
        # TURN BOUNDARY. Tool results are `type:"user"` records too (measured: 39 of 52 in a
        # real transcript), so "since the last user line" would cut the window to one tool
        # result and flag everything. Only a user line carrying TEXT starts a turn.
        lines = [_user("first ask"),
                 _tool_use("Read", {"file_path": os.path.join(d, "old.py")}, "t1"),
                 _tool_result("t1"),
                 _user("second ask"),
                 _tool_use("Read", {"file_path": os.path.join(d, "new.py")}, "t2"),
                 _tool_result("t2"),
                 _assistant_text("done")]
        for n in ("old.py", "new.py"):
            open(os.path.join(d, n), "w").write("x = 1\n")
        turn = tr.current_turn(_write_transcript(d, lines))
        reads = tr.read_paths(turn.records, root=d)
        check("D0: current_turn excludes the PREVIOUS turn's read",
              os.path.realpath(os.path.join(d, "new.py")) in reads
              and os.path.realpath(os.path.join(d, "old.py")) not in reads, sorted(reads))
        check("D0: a tool_result (type=user) does NOT start a turn",
              turn.status == tr.COMPLETE and len(reads) == 1, (turn.status, sorted(reads)))

        # A DENIED read is not a read. The permission system said no; the guard must not
        # certify a claim on evidence that was refused.
        lines = [_user("ask"),
                 _tool_use("Read", {"file_path": os.path.join(d, "new.py")}, "e1"),
                 _tool_error("e1"), _assistant_text("done")]
        turn = tr.current_turn(_write_transcript(d, lines, "err.jsonl"))
        check("D0: a denied/errored read is NOT counted as a read",
              tr.read_paths(turn.records, root=d) == set(),
              sorted(tr.read_paths(turn.records, root=d)))

        # Shell reads count; a heredoc WRITE beginning with `cat` must not.
        open(os.path.join(d, "shell.py"), "w").write("y = 2\n")
        lines = [_user("ask"), _tool_use("Bash", {"command": "cat shell.py"}, "b1"),
                 _assistant_text("x")]
        turn = tr.current_turn(_write_transcript(d, lines, "sh.jsonl"))
        check("D0: `cat f` is a read",
              os.path.realpath(os.path.join(d, "shell.py"))
              in tr.read_paths(turn.records, root=d), None)
        lines = [_user("ask"),
                 _tool_use("Bash", {"command": "cat > shell.py <<'EOF'"}, "b2"),
                 _assistant_text("x")]
        turn = tr.current_turn(_write_transcript(d, lines, "sh2.jsonl"))
        check("D0: a heredoc WRITE starting with `cat` is NOT a read (it clobbered the file)",
              tr.read_paths(turn.records, root=d) == set(),
              sorted(tr.read_paths(turn.records, root=d)))

        # CAP: env-tunable so this costs milliseconds, not a 50 MB write inside a 15s hook
        # timeout (the capture.py precedent). A cap hit must be CAPPED, never a silent partial.
        big = [_user("ask")] + [_assistant_text("filler " * 50) for _ in range(200)]
        tp = _write_transcript(d, big, "big.jsonl")
        turn = tr.current_turn(tp, cap=512)
        check("D0: a cap hit reports CAPPED, never a silent partial verdict",
              turn.status == tr.CAPPED, turn.status)

        check("D0: a missing transcript is UNREADABLE, not empty",
              tr.current_turn(os.path.join(d, "nope.jsonl")).status == tr.UNREADABLE, None)


def test_transcript_real_capture():
    """§1 seam rule: ONE input this repo did not author.

    Every other transcript fixture in this suite is written by the suite itself, on BOTH
    sides of the seam — so a drift in the host's wire format would move the fixtures with
    it and fail SILENT (exit 0, 'clean'). This pins the reader against a real Claude Code
    transcript when one is present on the machine.
    """
    import glob
    import importlib.util as _il
    spec = _il.spec_from_file_location("transcript", os.path.join(HOOKS, "transcript.py"))
    tr = _il.module_from_spec(spec)
    spec.loader.exec_module(tr)

    real = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")),
                  key=lambda f: os.path.getmtime(f), reverse=True)[:12]
    if not real:
        print("  skip - no real transcript on this machine (CI): seam unpinned here")
        return
    parsed = seen_dispatch = 0
    for f in real:
        try:
            with open(f, errors="replace") as fh:
                for ln in fh:
                    obj = tr.parse_line(ln)
                    if obj is None:
                        continue
                    parsed += 1
                    for tu in tr.tool_uses([obj]):
                        if tu["name"] in tr.DISPATCH_TOOLS and \
                                tu["input"].get("subagent_type"):
                            seen_dispatch += 1
        except OSError:
            continue
    # VACUITY (§4a): a seam test that parsed nothing proves nothing.
    check("seam: the reader parses records from a REAL transcript (vacuity-guarded)",
          parsed > 0, parsed)
    check("seam: real dispatch records are recognised by the shipped vocabulary "
          "(this is the check that would have caught the `Task` assumption)",
          seen_dispatch > 0, (seen_dispatch, parsed))


def test_cite_guard():
    """D1, both directions, every silent row paired with a firing twin."""
    import importlib.util as _il
    spec = _il.spec_from_file_location("cite_guard", os.path.join(HOOKS, "cite_guard.py"))
    cg = _il.module_from_spec(spec)
    spec.loader.exec_module(cg)

    with tempfile.TemporaryDirectory() as d:
        doctor = os.path.join(d, "doctor.py")
        open(doctor, "w").write("# Human-readable output\n# Machine-readable JSON\n")
        open(os.path.join(d, "other.py"), "w").write("z = 3\n")

        claim = "doctor.py reads the `readable` field."
        read_doctor = _tool_use("Read", {"file_path": doctor}, "r1")
        grep_only = _tool_use("Grep", {"pattern": "readable", "path": doctor}, "g1")

        # E1 — THE MOTIVATING CASE. Searched, never opened.
        rc, err = _cite_run(d, [_user("audit"), grep_only, _assistant_text(claim)])
        check("E1: a property claim about a file this turn only GREPPED fires",
              rc == 1 and "doctor.py" in err, (rc, err[:200]))
        # ...and names the SPECIFIC file, not merely "found something".
        check("E1: the message names the specific file",
              "doctor.py" in err and "other.py" not in err, err[:200])

        # VACUITY (§4a), three legs — proving the fixtures REACH the detector, so the
        # silent rows below cannot pass for the wrong reason.
        turn = cg.tr.current_turn(_write_transcript(
            d, [_user("a"), read_doctor, _assistant_text(claim)], "v.jsonl"))
        reads = cg.tr.read_paths(turn.records, root=d)
        check("vacuity-1: the positive twin's READ-SET is non-empty and holds the target",
              os.path.realpath(doctor) in reads, sorted(reads))
        check("vacuity-2: CLAIM EXTRACTION finds the claim in the output text",
              any("doctor.py" in c[0] for c in cg.claims_in(claim, d)),
              cg.claims_in(claim, d))
        check("vacuity-3: the target file EXISTS in the fixture tree "
              "(else every silent row greens on the not-found branch)",
              os.path.isfile(doctor), doctor)

        # ── the twin rule ──
        _twin(d, "E2 read-then-claim",
              [_user("a"), read_doctor, _assistant_text(claim)],
              [_user("a"), grep_only, _assistant_text(claim)], "doctor.py")
        _twin(d, "E3 edited-implies-known",
              [_user("a"), _tool_use("Edit", {"file_path": doctor}, "e1"),
               _assistant_text(claim)],
              [_user("a"), _assistant_text(claim)], "doctor.py")
        _twin(d, "E4 nonexistent-file",
              [_user("a"), _assistant_text("ghost.py reads the readable field.")],
              [_user("a"), _assistant_text(claim)], "doctor.py")
        _twin(d, "E5 bare-mention-no-property",
              [_user("a"), _assistant_text("See also doctor.py for context.")],
              [_user("a"), _assistant_text(claim)], "doctor.py")
        _twin(d, "E11 fenced-code-block",
              [_user("a"), _assistant_text("```\n" + claim + "\n```")],
              [_user("a"), _assistant_text(claim)], "doctor.py")
        _twin(d, "E7 shell-read-counts",
              [_user("a"), _tool_use("Bash", {"command": "sed -n '1,5p' doctor.py"}, "b1"),
               _assistant_text(claim)],
              [_user("a"), _tool_use("Bash", {"command": "grep readable doctor.py"}, "b2"),
               _assistant_text(claim)], "doctor.py")

        # ── Rule B: a FALSE loop-closure self-report ──
        # Keyed on the token the commands already mandate, not on "plan shape": a
        # §0-marker detector would flag every review turn, every quoted plan, and
        # /readable — whose contract FORBIDS the remedy it would demand.
        loop = "Loop closed: yes (integration-adversary — none; architecture-adversary — clean)"
        dispatch_cc = _tool_use("Agent", {"subagent_type": "tdd-playbook:architecture-adversary",
                                          "description": "review"}, "a1")
        dispatch_cheli = _tool_use("Task", {"subagent_type": "architecture-adversary",
                                            "description": "review"}, "a2")
        _twin(d, "E13/E17 loop-closed-with-no-dispatch",
              [_user("a"), dispatch_cc, _assistant_text(loop)],
              [_user("a"), _assistant_text(loop)], "Loop closed")
        # HOST PARITY: the Cheliped spelling must silence it too, or the guard is dark there.
        rc, err = _cite_run(d, [_user("a"), dispatch_cheli, _assistant_text(loop)])
        check("host parity: a Cheliped-shaped dispatch (Task) silences Rule B",
              rc == 0, (rc, err[:200]))
        # E15: ordinary prose containing the words must NOT fire.
        rc, err = _cite_run(d, [_user("a"), _assistant_text(
            "We should close the loop with an adversary before shipping.")])
        check("E15: prose about closing the loop is not a self-report", rc == 0, err[:200])

        # ── honesty events: absent data is UNMEASURED, never zero ──
        yl = os.path.join(_YIELD_TMP, "cite-honesty.jsonl")
        env = {"TDD_PLAYBOOK_YIELD_LOG": yl}
        rc, _ = _cite_run(d, [_user("a"), _assistant_text(claim)],
                          env_extra=dict(env, TDD_PLAYBOOK_TRANSCRIPT_SCAN_CAP="1"))
        rows = [json.loads(l) for l in open(yl)] if os.path.exists(yl) else []
        check("E10: a cap hit exits 0 AND leaves a `capped` row — never a silent partial",
              rc == 0 and any(r.get("event") == "capped" for r in rows),
              [r.get("event") for r in rows])

        # BLIND HOST: an Edit-only transcript with no assistant text cannot answer. It must
        # say so, not report clean. (The pre-C1 Cheliped shim was exactly this shape, and
        # `transcript_path` there is READABLE — so an absent-file fallback never fires.)
        yl2 = os.path.join(_YIELD_TMP, "cite-blind.jsonl")
        rc, _ = _cite_run(d, [_tool_use("Edit", {"file_path": doctor}, "x1")],
                          env_extra={"TDD_PLAYBOOK_YIELD_LOG": yl2}, name="blind.jsonl")
        rows = [json.loads(l) for l in open(yl2)] if os.path.exists(yl2) else []
        check("blind-host: an Edit-only transcript yields `blind`, NOT a clean verdict",
              rc == 0 and any(r.get("event") == "blind" for r in rows),
              [r.get("event") for r in rows])

        # Re-entry: both existing Stop hooks guard this; a Stop guard without it can loop,
        # and this guard's own finding text names a file and asserts a property of it.
        env2 = dict(os.environ)
        for k in list(env2):
            if k.startswith("TDD_PLAYBOOK_"):
                del env2[k]
        env2.update({"CLAUDE_PROJECT_DIR": d, "TDD_PLAYBOOK_HOOK_CITE": "warn",
                     "TDD_PLAYBOOK_YIELD_LOG": os.path.join(_YIELD_TMP, "reentry.jsonl"),
                     "TDD_PLAYBOOK_HEARTBEAT": os.path.join(_YIELD_TMP, "heartbeat")})
        tp = _write_transcript(d, [_user("a"), grep_only, _assistant_text(claim)], "re.jsonl")
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "cite_guard.py")],
                           input=json.dumps({"transcript_path": tp, "stop_hook_active": True}),
                           capture_output=True, text=True, env=env2, timeout=20, cwd=d)
        check("re-entry: stop_hook_active exits 0 immediately (no Stop loop)",
              p.returncode == 0 and not p.stderr.strip(), (p.returncode, p.stderr[:120]))

        # DETERMINISM: both rules subtract SETS; nothing in this repo pins hash ordering.
        outs = []
        for seed in ("0", "1"):
            _, e = _cite_run(d, [_user("a"), grep_only, _assistant_text(
                "doctor.py reads the readable field. other.py never calls it.")],
                env_extra={"PYTHONHASHSEED": seed})
            outs.append(e)
        check("determinism: identical stderr under PYTHONHASHSEED 0 and 1",
              outs[0] == outs[1], outs)

        # The SHIPPED default is off — opt-in is what the rest of this suite does.
        rc, err = _cite_run(d, [_user("a"), grep_only, _assistant_text(claim)],
                            env_extra={"TDD_PLAYBOOK_HOOK_CITE": ""})
        check("shipped default is OFF: no findings surfaced without opt-in",
              rc == 0 and not err.strip(), (rc, err[:120]))


def test_tripwire_read_only_turn_misattribution():
    """REGRESSION (found in review, 2026-08-27): a READ-ONLY turn must not be told it
    changed source.

    `session_edited_paths` returned `paths or None`, which collapses two different facts
    into one value: "this turn edited nothing" and "there is no transcript". A read-only
    turn therefore returned None, the session narrowing at `main()` was SKIPPED, and the
    hook fell through to whole-tree `git status` — reporting *"source changed with NO test
    change **this turn**"* on a turn that changed nothing, whenever the tree was dirty from
    earlier work. The message names "this turn"; the evidence was the whole tree.

    This is also the correction to the build plan's headline: an analysis turn passes
    through 17 of 18 bindings untouched, and through the 18th untouched only on a CLEAN
    tree.
    """
    s = "build_completion_reminder.py"
    with tempfile.TemporaryDirectory() as d:
        def git(*a):
            subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 1\n")
        git("add", "-A")
        git("commit", "-qm", "init")
        # tree is DIRTY from an earlier turn: source changed, no test change
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 2\n")

        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(_YIELD_TMP, "misattrib.jsonl")
        env["TDD_PLAYBOOK_HEARTBEAT"] = os.path.join(_YIELD_TMP, "heartbeat")

        def run_with(lines, name):
            tp = os.path.join(d, name)
            with open(tp, "w") as fh:
                fh.write("\n".join(lines) + "\n")
            return subprocess.run(
                [sys.executable, os.path.join(HOOKS, s)],
                input=json.dumps({"transcript_path": tp}),
                capture_output=True, text=True, cwd=d, env=env, timeout=20)

        # A READ-ONLY turn: the transcript is readable and shows searches, no edits.
        read_only = [
            json.dumps({"type": "user", "message": {"content": "audit this"}}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Grep",
                 "input": {"pattern": "f", "path": "app.py"}}]}}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "text", "text": "here is the audit"}]}}),
        ]
        p = run_with(read_only, "ro.jsonl")
        check("misattribution: a READ-ONLY turn on a dirty tree is SILENT "
              "(it did not change source 'this turn')",
              p.returncode == 0, (p.returncode, p.stderr[:200]))

        # TWIN — the guard must still fire when THIS turn really did edit source, or the
        # fix above would be indistinguishable from disabling the hook.
        edited = [
            json.dumps({"type": "user", "message": {"content": "fix it"}}),
            json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit",
                 "input": {"file_path": os.path.join(d, "app.py")}}]}}),
        ]
        p = run_with(edited, "ed.jsonl")
        check("misattribution twin: a turn that DID edit source still warns",
              p.returncode == 1 and "no test" in p.stderr.lower(),
              (p.returncode, p.stderr[:200]))

        # An UNREADABLE transcript keeps the old whole-tree fallback — absence of evidence
        # is not evidence of a read-only turn (§12: UNMEASURED, never zero).
        p = subprocess.run(
            [sys.executable, os.path.join(HOOKS, s)],
            input=json.dumps({"transcript_path": os.path.join(d, "nope.jsonl")}),
            capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("misattribution: an UNREADABLE transcript still falls back to whole-tree",
              p.returncode == 1, (p.returncode, p.stderr[:200]))


def test_yield_instrument_carries_session_and_coverage():
    """D2: the record the decay contract is computed from must be able to answer it.

    Two defects, both found in review (2026-08-27):
      - `log_yield_event` wrote {ts, source, host, gate, event, findings} with NO session
        id, so §0.5's named metric ("how many fires were followed by a corrective read in
        the NEXT turn") had no supplier — the contract was prose describing an instrument
        that could not compute it.
      - `gate_yield.GATE_EVENTS` is a CLOSED roster and anything else is dropped without a
        row, so the guard's own honesty events (`capped`, `blind`) would have been written
        and silently discarded by their named consumer. §0.4 claimed gate_yield as that
        consumer; at field granularity it was not one.
    """
    import importlib.util as _il
    with tempfile.TemporaryDirectory() as d:
        yl = os.path.join(d, "yield.jsonl")
        # a guard invocation carrying a session_id must stamp it on the row
        env = {"TDD_PLAYBOOK_YIELD_LOG": yl, "CLAUDE_PROJECT_DIR": d,
               "TDD_PLAYBOOK_HOOK_CITE": "warn"}
        e = dict(os.environ)
        for k in list(e):
            if k.startswith("TDD_PLAYBOOK_"):
                del e[k]
        e.update(env)
        e["TDD_PLAYBOOK_HEARTBEAT"] = os.path.join(_YIELD_TMP, "heartbeat")
        tp = os.path.join(d, "t.jsonl")
        open(tp, "w").write(json.dumps({"type": "user", "message": {"content": "hi"}})
                            + "\n" + json.dumps({"type": "assistant", "message": {
                                "content": [{"type": "text", "text": "nothing claimed"}]}})
                            + "\n")
        subprocess.run([sys.executable, os.path.join(HOOKS, "cite_guard.py")],
                       input=json.dumps({"transcript_path": tp, "session_id": "sess-42"}),
                       capture_output=True, text=True, env=e, timeout=20, cwd=d)
        rows = [json.loads(l) for l in open(yl)] if os.path.exists(yl) else []
        check("D2: the yield row carries the session id",
              any(r.get("session_id") == "sess-42" for r in rows), rows)
        # VACUITY: a clean turn must still leave a row, or there is no denominator at all.
        check("D2: a CLEAN turn leaves a `verified` row (the denominator)",
              any(r.get("event") == "verified" for r in rows),
              [r.get("event") for r in rows])

        # the rollup must COUNT the honesty events, not drop them
        spec = _il.spec_from_file_location("gate_yield",
                                           os.path.join(PLUGIN, "bin", "gate_yield.py"))
        gy = _il.module_from_spec(spec)
        spec.loader.exec_module(gy)
        check("D2: coverage events are a distinct vocabulary from gate events",
              set(gy.COVERAGE_EVENTS).isdisjoint(gy.GATE_EVENTS),
              (gy.COVERAGE_EVENTS, gy.GATE_EVENTS))
        for ev in ("capped", "blind"):
            check("D2: `{}` is an accepted coverage event (was silently dropped)".format(ev),
                  ev in gy.COVERAGE_EVENTS, gy.COVERAGE_EVENTS)

        log2 = os.path.join(d, "roll.jsonl")
        with open(log2, "w") as fh:
            for ev in ("verified", "verified", "blind", "capped"):
                fh.write(json.dumps({"gate": "cite", "event": ev, "source": "hook"}) + "\n")
        import argparse
        args = argparse.Namespace(log=log2, md=os.path.join(d, "y.md"), date="2026-08-27",
                                  response_md=os.path.join(d, "r.md"),
                                  usage_md=os.path.join(d, "u.md"))
        import io as _io
        import contextlib as _ctx
        buf = _io.StringIO()
        with _ctx.redirect_stdout(buf):
            gy.cmd_rollup(args)
        out = buf.getvalue()
        check("D2: the rollup PRINTS coverage — the numbers have a reader, not just a writer",
              "coverage: cite" in out and "verified 2" in out and "blind 1" in out, out)


def main():
    print("TDD Playbook hook calibration")
    for fn in (test_weakening, test_weakening_h5_exit_calls, test_overmock,
               test_exitcode, test_tag_guard, test_exhaustive_claim, test_snapshot,
               test_flaky, test_intent, test_tripwire_reminder, test_red_lock,
               test_fixture_guard, test_basename_roster_parity,
               test_lock_shell, test_yield_logging, test_guards_heartbeat,
               test_break_glass, test_retired_advisory_defaults,
               test_blocking_guards_prove_both_directions,
               test_guard_roster_derived_and_pinned,
               test_transcript_module, test_transcript_real_capture,
               test_cite_guard, test_tripwire_read_only_turn_misattribution,
               test_yield_instrument_carries_session_and_coverage):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
