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
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "hooks", "scripts")

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


# ---------------------------------------------------------------- test_weakening_guard
def test_weakening():
    s = "test_weakening_guard.py"
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
    s = "test_weakening_guard.py"
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

    # PLANTED — the exact shapes that bit, frozen
    rc, _o, e = run(s, ev("sh scripts/civerd_gate.sh > /tmp/g.out 2>&1 | tail -2"))
    check("exitcode: piped gate run is flagged", rc == 1 and "swallowed by a pipe" in e,
          (rc, e[:120]))
    rc, _o, e = run(s, ev("python3 plugins/tdd-playbook/tests/test_hooks.py 2>&1 | grep FAIL"))
    check("exitcode: piped suite run is flagged", rc == 1 and "discarded truth" in e,
          (rc, e[:120]))
    rc, _o, e = run(s, ev("pytest -q | tail -1"))
    check("exitcode: piped pytest is flagged", rc == 1, (rc, e[:120]))
    # v1.32.0: release_verify.py left _VERIFIER with the release wall. verify_verdict.py
    # STAYS (archival reader, still a verdict-bearing exit code) — and until now it was
    # named in the pattern but never exercised, so nothing would have noticed if the
    # deletion had taken it too. A roster entry with no test is a comment (§4a).
    rc, _o, e = run(s, ev(
        "python3 plugins/tdd-playbook/bin/verify_verdict.py --sha abc123 | tail -1"))
    check("exitcode: piped archival verdict read is flagged", rc == 1, (rc, e[:120]))
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
            ("prose in an echo", "echo 'David runs git {T} -s to release'")]:
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
    s = "test_weakening_guard.py"
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
    import importlib.util as _il
    spec = _il.spec_from_file_location("_common", os.path.join(HOOKS, "_common.py"))
    common = _il.module_from_spec(spec)
    spec.loader.exec_module(common)

    for name in ("exitcode", "overmock", "exhaustive", "flaky", "redlock"):
        check("retired-to-opt-in: {} defaults OFF".format(name),
              common._DEFAULT_MODES.get(name) == "off", common._DEFAULT_MODES.get(name))
    for name in ("testweaken", "testlock", "snapshotguard", "tagguard"):
        check("KEPT BLOCKING: {} (evidence, not sentiment)".format(name),
              common._DEFAULT_MODES.get(name) == "block", common._DEFAULT_MODES.get(name))

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

        # 4. the LOCKED file is now defended by test_lock_guard (end-to-end) —
        # ANY edit to a locked file is blocked, so neutral strings suffice.
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "test_lock_guard.py")],
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


def test_lock_shell():
    """F1 (shell channel) + F2 (lock self-protection) for test_lock_guard.py.

    A locked test the agent can rewrite with `sed -i` / `> file` / `git checkout`, or a lock
    file it can `rm`, is a lock in name only. These planted bypasses MUST block; reads and the
    sanctioned unlock MUST pass (a guard that wedges legitimate work is the adoption killer)."""
    s = "test_lock_guard.py"

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
        allow("lock/sh: cat locked test is allowed", d, bash_ev("cat tests/test_pay.py"))
        allow("lock/sh: run locked test is allowed", d, bash_ev("python -m pytest tests/test_pay.py -q"))
        allow("lock/sh: run + redirect OUTPUT elsewhere is allowed", d, bash_ev("pytest tests/test_pay.py -q > /tmp/out.log"))
        allow("lock/sh: git checkout a branch is allowed", d, bash_ev("git checkout main"))
        # F1 — verifier surface + enforcement via shell
        block("lock/sh: sed -i on conftest blocks (H5)", d, bash_ev("sed -i 's/a/b/' conftest.py"))
        block("lock/sh: rm on a guard hook blocks", d, bash_ev("rm .claude/hooks/scripts/test_lock_guard.py"))
        # F2 — the lock's own state cannot be removed/rewritten to self-unlock
        block("lock/sh: rm tdd-lock.json blocks (F2)", d, bash_ev("rm .claude/tdd-lock.json"))
        block("lock/sh: overwrite tdd-lock.json blocks (F2)", d, bash_ev("echo '{}' > .claude/tdd-lock.json"))
        block("lock/sh: truncate the journal blocks (F2)", d, bash_ev("truncate -s0 .claude/tdd-lock-journal.jsonl"))
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
    s = "test_weakening_guard.py"
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

    # PLANTED (hole 2): this repo's committed settings must carry no standing demotions —
    # an env-block demotion is the persistent, invisible variant of the kill switch
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HOOKS))))
    demotions = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        sp = os.path.join(repo_root, rel)
        if os.path.isfile(sp):
            try:
                envblock = json.load(open(sp)).get("env", {}) or {}
            except ValueError:
                envblock = {}
            demotions += ["{}: {}={}".format(rel, k, v) for k, v in envblock.items()
                          if k.startswith("TDD_PLAYBOOK_HOOK")]
    check("no standing guard demotions in committed settings env blocks",
          demotions == [], demotions)


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


def main():
    print("TDD Playbook hook calibration")
    for fn in (test_weakening, test_weakening_h5_exit_calls, test_overmock,
               test_exitcode, test_tag_guard, test_exhaustive_claim, test_snapshot,
               test_flaky, test_intent, test_tripwire_reminder, test_red_lock,
               test_lock_shell, test_yield_logging, test_guards_heartbeat,
               test_break_glass, test_retired_advisory_defaults):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
