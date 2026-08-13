#!/usr/bin/env python3
"""Planted-input calibration for gate_yield (R4-lean: the retirement instrument).

The doctrine only ever measured whether gates are strong enough — never whether they still
earn their friction. gate_yield derives per-gate yield from the ONE event log the hooks and
the lock already write, rolls it up once per calibration cycle into a COMMITTED record, and
prints retirement candidates only from >=2 committed cycles (a fresh clone must never make a
healthy gate look like a zero-yield candidate). Absent data is UNMEASURED, never a fabricated
zero. Self-contained, no pytest. Run: python3 tests/test_gate_yield.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
GY = os.path.join(PLUGIN, "bin", "gate_yield.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


# Response-record isolation (the G5 class again, found 2026-08-06). `run_gy` strips every
# TDD_PLAYBOOK_* var, and only 2 of 7 rollup call sites passed --response-md, so
# default_response_md() fell through to the REPO's real docs/calibration/guard_response.md
# and this suite wrote 64 fabricated rows into a committed instrument record. Redirect it
# unconditionally here rather than relying on every future call site remembering the flag.
_RESP_ISO = tempfile.mkdtemp(prefix="gy-resp-iso-")
_REPO_RESPONSE_MD = os.path.join(REPO, "docs", "calibration", "guard_response.md")
_REPO_RESPONSE_BEFORE = (open(_REPO_RESPONSE_MD, "rb").read()
                         if os.path.isfile(_REPO_RESPONSE_MD) else None)


def run_gy(*args, env_extra=None):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["TDD_PLAYBOOK_RESPONSE_MD"] = os.path.join(_RESP_ISO, "guard_response.md")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, GY, *args], capture_output=True, text=True,
                          env=env, timeout=60)


GN = os.path.join(PLUGIN, "bin", "guard_note.py")


def run_gn(*args, env_extra=None):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, GN, *args], capture_output=True, text=True,
                          env=env, timeout=60)


def seed_raw(path, lines):
    with open(path, "w") as fh:
        for ln in lines:
            fh.write((json.dumps(ln) if isinstance(ln, dict) else ln) + "\n")


def test_guard_response():
    """v1.28 — guard interactions must be AUDITABLE from a record, not reconstructed from a
    transcript. David's question ('is the model skirting the guards, or complying?') could
    only be answered by me hand-auditing a journal, git history and four transcript moments.
    That is not a control.

    The three-clause record — what the guard objected to · whether the action was performed
    by another route · what was dropped — is self-reported, so it is only worth anything
    because of the pairing: the HOOK writes the block count (mechanically, via emit()), the
    agent writes only the responses. Self-report cannot inflate the denominator, so silence
    shows up as UNACCOUNTED rather than as absence of evidence."""
    print("\n[guard response log (v1.28)]")
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        md = os.path.join(d, "gate_yield.md")
        rmd = os.path.join(d, "guard_response.md")
        env = {"TDD_PLAYBOOK_YIELD_LOG": raw}

        # the CLI writes through the SAME single write path the hooks use
        p = run_gn("record", "--gate", "testlock", "--objected", "lockstate basename in a "
                   "command that also wrote an unrelated file",
                   "--performed-elsewhere", "no",
                   "--dropped", "the bash heredoc channel; used the structured edit path",
                   env_extra=env)
        check("guard_note: a well-formed record exits 0", p.returncode == 0,
              (p.returncode, p.stderr[:120]))
        rows = [json.loads(l) for l in open(raw)] if os.path.isfile(raw) else []
        resp = [r for r in rows if r.get("event") == "response"]
        check("guard_note: writes ONE response row carrying all three clauses",
              len(resp) == 1 and resp[0].get("gate") == "testlock"
              and resp[0].get("performed_elsewhere") == "no"
              and "unrelated file" in (resp[0].get("objected") or "")
              and "structured edit path" in (resp[0].get("dropped") or ""), resp)
        check("guard_note: the row is attributed to the AGENT, never to the hook "
              "(a self-report must be labelled as one)",
              resp and resp[0].get("source") == "agent", resp)

        # usage errors are exit 2 — never a silently dropped record
        p = run_gn("record", "--gate", "testlock", "--objected", "x",
                   "--performed-elsewhere", "maybe", "--dropped", "y", env_extra=env)
        check("guard_note: performed-elsewhere must be yes|no -> exit 2 (usage)",
              p.returncode == 2, (p.returncode, p.stderr[:120]))

    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        md = os.path.join(d, "gate_yield.md")
        rmd = os.path.join(d, "guard_response.md")
        # 3 blocks (hook-written), 2 responses (agent-written) -> 1 UNACCOUNTED
        seed_raw(raw, [{"gate": "testlock", "event": "block"}] * 3
                 + [{"source": "agent", "gate": "testlock", "event": "response",
                     "performed_elsewhere": "no", "objected": "o", "dropped": "d"}] * 2)
        p = run_gy("rollup", "--log", raw, "--md", md, "--response-md", rmd,
                   "--date", "2026-08-06")
        body = open(rmd).read() if os.path.isfile(rmd) else "<missing>"
        check("response rollup: one committed row per gate (blocks, accounted, unaccounted)",
              p.returncode == 0 and "| 2026-08-06 | testlock | 3 | 2 | 1 | 0 |" in body,
              (p.returncode, body, p.stdout))
        check("response rollup: UNACCOUNTED is reported, not buried",
              "UNACCOUNTED" in p.stdout and "testlock" in p.stdout, p.stdout)
        check("response rollup: the gate_yield row schema is UNCHANGED (7 cols)",
              "| 2026-08-06 | testlock | 3 | 0 | 0 | 0 | 0 |" in open(md).read(),
              open(md).read())
        check("response record carries a schema stamp (a counting change must be a "
              "conscious migration, per the dataflow precedent)",
              "schema:" in body, body)

    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        rmd = os.path.join(d, "guard_response.md")
        # PLANTED: the bypass signal itself — an action performed by another route
        seed_raw(raw, [{"gate": "testlock", "event": "block"},
                       {"source": "agent", "gate": "testlock", "event": "response",
                        "performed_elsewhere": "yes", "objected": "o",
                        "dropped": "nothing — I ran it another way"}])
        p = run_gy("rollup", "--log", raw, "--md", os.path.join(d, "g.md"),
                   "--response-md", rmd, "--date", "2026-08-06")
        check("response rollup: performed-elsewhere=yes is ALARMED loudly (this is the "
              "bypass signal the whole record exists to surface)",
              "PERFORMED ELSEWHERE" in p.stdout, p.stdout)
        check("response rollup: and it is counted in the committed row",
              "| 2026-08-06 | testlock | 1 | 1 | 0 | 1 |" in open(rmd).read(),
              open(rmd).read())


def test_header_migration():
    """v1.32.0 §13 guard-calibration: replayed against the MOTIVATING ARTIFACT.

    The committed gate_yield.md carried the SUPERSEDED v1.26 header for four cycles because
    the header was only ever written on file creation — v1.27's correction lived in code and
    never reached the artifact anyone reads. A later reader took the stale definition at face
    value and concluded testlock had 20 false positives when the measured number is 0.

    Three separate defects are frozen here, each found by replaying the real thing:
      1. the migration sat AFTER the no-events early return, so on a quiet cycle — exactly
         how a header goes stale — the repair never ran;
      2. its row predicate (`startswith("| 2")`) was narrower than parse_md_rows', silently
         dropping a 1999-dated row AND the operator's DEMOTION JOURNAL note, which is the
         note this very tool instructs them to write;
      3. it truncated in place with no temp+rename, so a crash destroyed the record."""
    print("\n[gate_yield header migration]")
    import importlib.util as _il
    _sp = _il.spec_from_file_location("gate_yield", GY)
    mod = _il.module_from_spec(_sp); _sp.loader.exec_module(mod)
    stale = ("# OLD TITLE\n\nsuperseded prose about overrides.\n\n"
             "| date | gate | blocks | warns | overrides | suppressed |\n|---|---|---|---|---|---|\n"
             "| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |\n"
             "| 1999-01-01 | legacygate | 1 | 0 | 0 | 0 |\n"
             "DEMOTION JOURNAL: operator note that must survive\n")
    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "gate_yield.md")
        open(md, "w").write(stale)
        # QUIET CYCLE: no event log at all — the case the first version could not reach
        changed = mod.migrate_header(md)
        out = open(md).read()
        check("migration runs on a QUIET cycle (no events)", changed is True, changed)
        check("the corrected header replaces the superseded one",
              out.startswith(mod.MD_HEADER), out[:80])
        check("the stale prose is gone", "superseded prose" not in out, out[:200])
        check("a 2026 row survives byte-for-byte",
              "| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |" in out)
        check("a NON-2026 row survives (predicate matches parse_md_rows, not '| 2')",
              "legacygate" in out, out)
        check("the operator's own journal note survives",
              "DEMOTION JOURNAL" in out, out)
        check("migration is idempotent — a rollup is not a destructive rewrite",
              mod.migrate_header(md) is False)
        check("no temp file is left behind (atomic replace)",
              not os.path.isfile(md + ".migrating"), os.listdir(d))
        # and the rows are still parseable by the module's own parser afterwards
        rows = mod.parse_md_rows(md)
        check("parse_md_rows still reads every migrated row", len(rows) == 2, rows)


def main():
    print("gate_yield calibration")
    if not os.path.isfile(GY):
        check("bin/gate_yield.py exists", False, "missing")
        print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        md = os.path.join(d, "gate_yield.md")

        # rollup aggregates the raw log into one committed row per gate, then drains it
        seed_raw(raw, [
            {"ts": "t", "source": "hook", "gate": "testweaken", "event": "block",
             "findings": 1},
            {"ts": "t", "source": "hook", "gate": "testweaken", "event": "block",
             "findings": 2},
            {"ts": "t", "source": "hook", "gate": "flaky", "event": "warn", "findings": 1},
            {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
             "findings": 1},
            "this line is not json (PLANTED corruption)",
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "the testlock guard blocked an edit it had no business blocking",
             "reason_class": "gate-wrong"},
            {"ts": "t", "source": "hook", "gate": "snapshotguard", "event": "suppressed",
             "findings": 1},
        ])
        p = run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-07-27")
        body = open(md).read() if os.path.isfile(md) else ""
        check("rollup: exit 0 with per-gate rows (v1.27: 7 cells, fp last)",
              p.returncode == 0 and "| 2026-07-27 | testweaken | 2 | 0 | 0 | 0 | 0 |" in body
              and "| 2026-07-27 | testlock | 1 | 0 | 1 | 0 | 1 |" in body
              and "| 2026-07-27 | flaky | 0 | 1 | 0 | 0 | 0 |" in body
              and "| 2026-07-27 | snapshotguard | 0 | 0 | 0 | 1 | 0 |" in body,
              (p.returncode, body, p.stdout, p.stderr))
        check("rollup: PLANTED corrupt line skipped with a warning, run not failed",
              "corrupt" in (p.stdout + p.stderr).lower()
              or "skipped" in (p.stdout + p.stderr).lower(), (p.stdout, p.stderr))
        check("rollup: raw log drained (cycles stay disjoint)",
              not os.path.isfile(raw) or open(raw).read().strip() == "",
              open(raw).read() if os.path.isfile(raw) else "gone")

        # a second cycle appends (committed record only GROWS)
        seed_raw(raw, [
            {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
             "findings": 1},
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "the testlock guard blocked an edit it had no business blocking",
             "reason_class": "gate-wrong"},
        ])
        run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-08-10")
        body = open(md).read()
        check("rollup: second cycle appends, first cycle intact",
              "| 2026-07-27 | testweaken |" in body
              and "| 2026-08-10 | testlock | 1 | 0 | 1 | 0 | 1 |" in body, body)

        # candidates: testlock has 2 cycles of friction where every block was adjudicated a
        # false positive (fp, i.e. --class gate-wrong) -> candidate; testweaken has friction
        # but no adjudication -> NOT a candidate; a gate absent from the record is UNMEASURED.
        # v1.27 (pre-fix sha 119e2de): this pin previously seeded a CLASSLESS override and
        # asserted the flag, which pinned the DEFECT — every unlock read as an adjudicated
        # false positive. The fixtures now carry reason_class, so the TRUE half of the old
        # semantics (genuine FPs DO flag) survives under the corrected mechanism.
        p = run_gy("candidates", "--md", md)
        check("candidates: 2 cycles all-adjudicated-gate-wrong -> retirement candidate",
              p.returncode == 0 and "RETIREMENT CANDIDATE" in p.stdout
              and "testlock" in p.stdout, (p.returncode, p.stdout, p.stderr))
        check("candidates: unadjudicated friction is NOT a candidate",
              "RETIREMENT CANDIDATE: testweaken" not in p.stdout, p.stdout)
        check("candidates: absent gates stated as unmeasured, not zero",
              "unmeasured" in p.stdout.lower(), p.stdout)
        check("candidates: suppressed findings surfaced LOUDLY (muzzled gate detection)",
              "SUPPRESSED" in p.stdout and "snapshotguard" in p.stdout, p.stdout)

    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "gate_yield.md")
        with open(md, "w") as fh:
            fh.write("| date | gate | blocks | warns | overrides | suppressed | fp |\n"
                     "|---|---|---|---|---|---|---|\n"
                     "| 2026-08-10 | testlock | 3 | 0 | 3 | 0 | 3 |\n")
        p = run_gy("candidates", "--md", md)
        check("candidates: ONE cycle is never enough (fresh-clone protection)",
              p.returncode == 0 and "RETIREMENT CANDIDATE" not in p.stdout, p.stdout)

        p = run_gy("candidates", "--md", os.path.join(d, "nope.md"))
        check("candidates: no committed record -> unmeasured, exit 0",
              p.returncode == 0 and "unmeasured" in p.stdout.lower(),
              (p.returncode, p.stdout))

        p = run_gy("rollup", "--log", os.path.join(d, "nope.jsonl"), "--md", md,
                   "--date", "2026-08-11")
        check("rollup: no raw log -> unmeasured note, exit 0, record untouched",
              p.returncode == 0 and "unmeasured" in p.stdout.lower()
              and "2026-08-11" not in open(md).read(), (p.returncode, p.stdout))

    # run_calibration carries the candidate report on the existing cadence (never fails the
    # run): a stubbed scenario run must end with a yield section either way
    with tempfile.TemporaryDirectory() as d:
        stub = os.path.join(d, "claude-stub")
        with open(stub, "w") as fh:
            fh.write("#!/bin/sh\ncat <<'EOF'\n**VERDICT: REFUTED** — authorize() is called "
                     "at cli.py:15 and cli.py:21.\nClaims checked: 1 · confirmed: 0 · "
                     "refuted: 1\nRecommendation: revise.\nEOF\n")
        os.chmod(stub, 0o755)
        md = os.path.join(d, "gate_yield.md")
        with open(md, "w") as fh:
            fh.write("| date | gate | blocks | warns | overrides | suppressed | fp |\n"
                     "|---|---|---|---|---|---|---|\n"
                     "| 2026-07-27 | testlock | 3 | 0 | 3 | 0 | 3 |\n"
                     "| 2026-08-10 | testlock | 2 | 0 | 2 | 0 | 2 |\n")
        env = dict(os.environ)
        env["TDD_PLAYBOOK_YIELD_MD"] = md
        # isolation: never drain a developer's real raw log through this test
        env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(d, "no-raw.jsonl")
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, "calibration", "run_calibration.py"),
             "--scenario", "false-negative-claim", "--claude-bin", stub, "--history", "",
             "--repeat", "1"],
            capture_output=True, text=True, env=env, timeout=300)
        check("run_calibration: prints the retirement-candidate mirror of DECAY WARNING",
              p.returncode == 0 and "RETIREMENT CANDIDATE" in p.stdout and
              "testlock" in p.stdout, (p.returncode, p.stdout[-600:]))
        env["TDD_PLAYBOOK_YIELD_MD"] = os.path.join(d, "absent.md")
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, "calibration", "run_calibration.py"),
             "--scenario", "false-negative-claim", "--claude-bin", stub, "--history", "",
             "--repeat", "1"],
            capture_output=True, text=True, env=env, timeout=300)
        check("run_calibration: absent yield record -> unmeasured line, run still green",
              p.returncode == 0 and "unmeasured" in p.stdout.lower(),
              (p.returncode, p.stdout[-400:]))

    test_usage_record_and_gate_roster()
    test_override_reason_class()
    test_replay_motivating_artifact()
    test_dataflow_rollup_and_trend()
    test_dataflow_producer_consumer_seam()
    test_guard_response()
    test_header_migration()

    # PLANTED-BY-CONSTRUCTION (2026-08-06): this suite drove the real gate_yield.py 7 times
    # and must have left the repo's committed instrument records byte-identical. It did not,
    # for two days, and nobody noticed because nothing asserted it — the same shape as the
    # 2026-07-28 G5 incident one file over. An instrument whose own record is test exhaust
    # measures nothing.
    after = (open(_REPO_RESPONSE_MD, "rb").read()
             if os.path.isfile(_REPO_RESPONSE_MD) else None)
    check("suite left the repo's real guard_response.md untouched",
          after == _REPO_RESPONSE_BEFORE,
          "committed record was written by the test suite")

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def _md(path, rows, header=True):
    """Write a committed-record fixture. rows are raw '| ... |' strings."""
    with open(path, "w") as fh:
        if header:
            fh.write("| date | gate | blocks | warns | overrides | suppressed | fp |\n"
                     "|---|---|---|---|---|---|---|\n")
        fh.write("\n".join(rows) + "\n")


def test_usage_record_and_gate_roster():
    """v1.34.0 D5 — the usage record, and the roster/counting split that makes it safe.

    PROVEN-BY-EXECUTION origin (readable-surface plan re-review, both adversaries
    independently): cmd_rollup registered the per_gate key BEFORE inspecting the event
    name, so ANY non-gate producer riding the one write path minted a phantom zero-yield
    gate row in the retirement instrument — three `invocation` events produced
    `| readable-surface | 0 | 0 | 0 | 0 | 0 |`, and `candidates` then counted a non-gate
    in its measured denominator. The fix separates the ROSTER decision (closed GATE_EVENTS
    vocabulary) from the COUNTING decision, and routes usage events to their own per-cycle
    table — same shape as the three sibling records, append-only, no per-invocation id.
    """
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        md = os.path.join(d, "gate_yield.md")
        usage = os.path.join(d, "usage.md")
        seed_raw(raw, [
            {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
             "findings": 1},
            # PLANT (the phantom-row shape): machine usage events from the facts tool
            {"ts": "t", "source": "cli", "gate": "readable-surface", "event": "usage",
             "scenario": "S17", "rows_surfaced": 12, "host": "claude"},
            {"ts": "t", "source": "cli", "gate": "readable-surface", "event": "usage",
             "scenario": "S17", "rows_surfaced": 12, "host": "claude"},
            {"ts": "t", "source": "cli", "gate": "readable-surface", "event": "usage",
             "scenario": "full", "rows_surfaced": 40, "host": "claude"},
            # the agent's note rides the same log as an EVENT (guard_note pattern),
            # never an edit — append-only is the data model
            {"ts": "t", "source": "agent", "gate": "readable-surface",
             "event": "usage-note", "scenario": "S17", "dispatched": "yes",
             "changed_a_decision": "yes"},
            # PLANT (orphan): a note for a scenario with no machine use this cycle
            {"ts": "t", "source": "agent", "gate": "readable-surface",
             "event": "usage-note", "scenario": "S99", "dispatched": "yes",
             "changed_a_decision": "no"},
            # CONTROL: a genuinely unknown event still mints nothing anywhere
            {"ts": "t", "source": "hook", "gate": "mystery-tool", "event": "mystery"},
        ])
        p = run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-08-12",
                   env_extra={"TDD_PLAYBOOK_USAGE_MD": usage})
        check("usage rollup: exits 0", p.returncode == 0, (p.returncode, p.stderr))
        gate_text = open(md).read() if os.path.isfile(md) else ""
        # the phantom-row regression, BOTH directions
        check("roster split: real gate event still lands its row",
              "| testlock |" in gate_text.replace("2026-08-12", "").replace("  ", " ")
              or "testlock" in gate_text, gate_text)
        check("roster split: usage producer mints NO gate row (the phantom-row fix)",
              "readable-surface" not in gate_text, gate_text)
        check("roster split: unknown event mints NO gate row (old tolerance preserved)",
              "mystery-tool" not in gate_text, gate_text)
        usage_text = open(usage).read() if os.path.isfile(usage) else ""
        check("usage table: S17 row carries uses=2 dispatched=1 changed=1",
              "| 2026-08-12 | S17 | 2 | 1 | 1 |" in usage_text, usage_text)
        check("usage table: full row carries uses=1 and untouched note cells",
              "| 2026-08-12 | full | 1 | 0 | 0 |" in usage_text, usage_text)
        check("usage table: orphan note is REPORTED, never a denominator row",
              "S99" not in usage_text and "ORPHAN" in p.stdout.upper(),
              (usage_text, p.stdout))
        check("usage table: drain happened once (raw log gone)",
              not os.path.isfile(raw))

        # anti-gaming, now true by construction: a forged note alone creates NO row
        seed_raw(raw, [
            {"ts": "t", "source": "agent", "gate": "readable-surface",
             "event": "usage-note", "scenario": "S17", "dispatched": "yes",
             "changed_a_decision": "yes"},
        ])
        usage2 = os.path.join(d, "usage2.md")
        p = run_gy("rollup", "--log", raw, "--md", os.path.join(d, "g2.md"),
                   "--date", "2026-08-13", env_extra={"TDD_PLAYBOOK_USAGE_MD": usage2})
        check("forged note alone: no usage row minted (denominator is machine-only)",
              p.returncode == 0 and (not os.path.isfile(usage2)
                                     or "S17" not in open(usage2).read()),
              (p.returncode, os.path.isfile(usage2)))

    # the sibling-path contract (one instrument, one seam): every harness that isolates
    # TDD_PLAYBOOK_YIELD_MD isolates the usage record too — the G5 leak class
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        seed_raw(raw, [
            {"ts": "t", "source": "cli", "gate": "readable-surface", "event": "usage",
             "scenario": "full", "rows_surfaced": 3, "host": "claude"},
        ])
        p = run_gy("rollup", "--log", raw, "--md", os.path.join(d, "gate_yield.md"),
                   "--date", "2026-08-12",
                   env_extra={"TDD_PLAYBOOK_YIELD_MD": os.path.join(d, "gate_yield.md")})
        sibling = os.path.join(d, "usage.md")
        check("default_usage_md derives from TDD_PLAYBOOK_YIELD_MD's dirname (sibling)",
              p.returncode == 0 and os.path.isfile(sibling)
              and "| full | 1 |" in open(sibling).read(),
              (p.returncode, os.listdir(d)))

    # usage-note subcommand: an EVENT appender in the guard_note shape — refuses bad args
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        p = run_gy("usage-note", "--scenario", "S17", "--dispatched", "yes",
                   "--changed-a-decision", "no",
                   env_extra={"TDD_PLAYBOOK_YIELD_LOG": raw})
        rows = [json.loads(l) for l in open(raw)] if os.path.isfile(raw) else []
        check("usage-note: appends a source=agent event on the ONE write path",
              p.returncode == 0 and len(rows) == 1 and rows[0]["event"] == "usage-note"
              and rows[0]["source"] == "agent" and rows[0]["scenario"] == "S17",
              (p.returncode, rows))
        p = run_gy("usage-note", "--scenario", "S17", "--dispatched", "maybe",
                   "--changed-a-decision", "no",
                   env_extra={"TDD_PLAYBOOK_YIELD_LOG": raw})
        check("usage-note: refuses a non-yes/no answer (exit 2, usage never proof)",
              p.returncode == 2, p.returncode)


def test_override_reason_class():
    """PLANTED (v1.27, pre-fix sha 119e2de): gate_yield counted EVERY journaled unlock as a
    block adjudicated a false positive, so four cycles of the normal red-first
    lock/implement/unlock rhythm printed `RETIREMENT CANDIDATE: testlock` with zero real
    false positives — the instrument recommending retirement of the strongest anti-gaming
    defense there is. Only an unlock journaled `--class gate-wrong` adjudicates a block.

    Every plant below is paired with the clean control that MUST still flag: a fix that
    simply stopped flagging would be the same defect with the sign flipped."""
    print("\n[override reason-class (v1.27)]")
    with tempfile.TemporaryDirectory() as d:
        # 1. the motivating shape: friction fully overridden, but all PHASE-class
        for klass, should_flag in (("phase", False), ("feature-end", False),
                                   ("test-wrong", False), ("gate-wrong", True)):
            raw, md = os.path.join(d, "raw.jsonl"), os.path.join(d, klass + ".md")
            for date in ("2026-09-01", "2026-09-02"):
                seed_raw(raw, [
                    {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
                     "findings": 1},
                    {"ts": "t", "source": "testlock", "gate": "testlock",
                     "event": "override", "reason": "x" * 40, "reason_class": klass},
                ])
                run_gy("rollup", "--log", raw, "--md", md, "--date", date)
            p = run_gy("candidates", "--md", md)
            flagged = "RETIREMENT CANDIDATE" in p.stdout
            check("candidates: all-{} overrides -> {}".format(
                      klass, "candidate" if should_flag else "NO candidate"),
                  p.returncode == 0 and flagged == should_flag, (klass, p.stdout))

        # 2. rollup keeps `overrides` as the TOTAL and `fp` as the adjudicating subset;
        #    a class-less override (old vendored lock) counts as an override, never an fp
        raw, md = os.path.join(d, "mix.jsonl"), os.path.join(d, "mix.md")
        seed_raw(raw, [
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "x" * 40, "reason_class": "phase"},
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "x" * 40, "reason_class": "gate-wrong"},
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "no class at all (old vendored caller)"},
        ])
        run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-09-03")
        check("rollup: overrides counts ALL 3, fp counts only the gate-wrong one",
              "| 2026-09-03 | testlock | 0 | 0 | 3 | 0 | 1 |" in open(md).read(),
              open(md).read())

        # 3. FABRICATION GUARD: legacy 6-cell rows are UNMEASURED, never fp=0-by-default.
        #    A record of only legacy rows can never produce a candidate, and says why.
        legacy = os.path.join(d, "legacy.md")
        _md(legacy, ["| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |",
                     "| 2026-08-03 | testlock | 3 | 0 | 5 | 0 |"])
        p = run_gy("candidates", "--md", legacy)
        check("candidates: PLANTED legacy-only record -> no candidate (unmeasured, not zero)",
              "RETIREMENT CANDIDATE" not in p.stdout, p.stdout)
        check("candidates: legacy record says UNCLASSIFIED HISTORY out loud",
              "UNCLASSIFIED HISTORY" in p.stdout and "testlock" in p.stdout, p.stdout)

        # 4. mixed history: the verdict rests on the CLASSIFIED cycles only — one classified
        #    cycle is below min_cycles even though the record holds three dates
        mixed = os.path.join(d, "mixed.md")
        _md(mixed, ["| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |",
                    "| 2026-08-03 | testlock | 3 | 0 | 5 | 0 |",
                    "| 2026-09-03 | testlock | 1 | 0 | 1 | 0 | 1 |"])
        p = run_gy("candidates", "--md", mixed)
        check("candidates: PLANTED mixed history -> 1 classified cycle is not enough",
              "RETIREMENT CANDIDATE" not in p.stdout, p.stdout)
        check("candidates: mixed history cites the classified count, not the row count",
              "2 committed cycle(s) predate" in p.stdout, p.stdout)

        # 5. CONTROL: two classified cycles, fp >= blocks -> the flag MUST return
        good = os.path.join(d, "good.md")
        _md(good, ["| 2026-09-03 | testlock | 1 | 0 | 1 | 0 | 1 |",
                   "| 2026-09-04 | testlock | 2 | 0 | 2 | 0 | 2 |"])
        p = run_gy("candidates", "--md", good)
        check("candidates: CONTROL 2 classified cycles, fp>=blocks -> candidate returns",
              "RETIREMENT CANDIDATE: testlock" in p.stdout, p.stdout)

        # 6. legacy blocks must NOT inflate the denominator against post-fix fp (the same
        #    bug sign-flipped: a real candidate silently suppressed forever)
        infl = os.path.join(d, "inflate.md")
        _md(infl, ["| 2026-07-30 | testlock | 99 | 0 | 0 | 0 |",
                   "| 2026-09-03 | testlock | 1 | 0 | 1 | 0 | 1 |",
                   "| 2026-09-04 | testlock | 1 | 0 | 1 | 0 | 1 |"])
        p = run_gy("candidates", "--md", infl)
        check("candidates: PLANTED 99 legacy blocks do NOT suppress a real candidate",
              "RETIREMENT CANDIDATE: testlock" in p.stdout, p.stdout)


def test_replay_motivating_artifact():
    """§13 v1.25 guard calibration: replay the fix against the artifact that MOTIVATED it.

    Pre-fix sha 119e2de. The four rows below are a verbatim freeze of
    `git show 119e2de:docs/calibration/gate_yield.md` (testlock rows) — frozen inline rather
    than shelled out, so the test is self-contained in a shallow clone; provenance lives
    here. The paired journal artifact is `git show 119e2de:.claude/tdd-lock-journal.jsonl`
    (22 unlocks, overwhelmingly phase-boundary rhythm).

    Red-first alone proves a guard CAN fail, not that it fails for the reason it was built.
    Leg (c) is what makes this real: re-materialize the identical numbers as classified rows
    and the flag must REAPPEAR — without it this whole test passes for a candidates() that
    never flags anything."""
    print("\n[replay: the motivating artifact (pre-fix 119e2de)]")
    FROZEN = ["| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |",
              "| 2026-08-03 | testlock | 3 | 0 | 5 | 0 |",
              "| 2026-08-04 | testlock | 3 | 0 | 2 | 0 |",
              "| 2026-08-05 | testlock | 1 | 0 | 0 | 0 |"]
    with tempfile.TemporaryDirectory() as d:
        pre = os.path.join(d, "prefix.md")
        _md(pre, FROZEN)
        p = run_gy("candidates", "--md", pre)
        check("(a) replay: the pre-fix record no longer flags testlock for retirement",
              p.returncode == 0 and "RETIREMENT CANDIDATE" not in p.stdout, p.stdout)
        check("(b) replay: the retraction is as visible as the spurious flag was",
              "UNCLASSIFIED HISTORY" in p.stdout, p.stdout)

        # (c) NEGATIVE CONTROL — same numbers, now classified: the flag must come back,
        #     proving (a) is a correct verdict and not a guard that stopped working.
        ctl = os.path.join(d, "control.md")
        _md(ctl, [r + " {} |".format(r.strip().strip("|").split("|")[4].strip())
                  for r in FROZEN])
        p = run_gy("candidates", "--md", ctl)
        check("(c) replay NEGATIVE CONTROL: identical numbers classified -> flag returns",
              "RETIREMENT CANDIDATE: testlock" in p.stdout, p.stdout)


def test_dataflow_rollup_and_trend():
    """v1.24 (D13b): the §6c sweep summaries join the SAME instrument — one committed row
    per sweep per calibration cycle, and a mechanical trend check on the excluded share.
    'A growing excluded share' is a TREND claim — undetectable from one run's summary line;
    it needs committed rows and a comparator (exactly like F5 needed check_staleness.py,
    not a reminder). Absent data is UNMEASURED, never zero."""
    print("\n[test_dataflow_rollup_and_trend]")
    line1 = ("dataflow_sweeps render-pairing: checked 40 · violations 0 · "
             "exempted 2 · unresolvable 1")
    line2 = ("dataflow_sweeps ghost-gates: checked 12 · violations 3 · "
             "exempted 0 · unresolvable 0")
    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "dataflow_yield.md")
        p = run_gy("dataflow-rollup", "--md", md, "--date", "2026-08-03",
                   "--line", line1, "--line", line2)
        body = open(md).read() if os.path.isfile(md) else "<missing>"
        check("dataflow-rollup: appends one committed row per sweep",
              p.returncode == 0
              and "| 2026-08-03 | render-pairing | 40 | 0 | 2 | 1 |" in body
              and "| 2026-08-03 | ghost-gates | 12 | 3 | 0 | 0 |" in body,
              (p.returncode, body, p.stdout, p.stderr))
        p = run_gy("dataflow-rollup", "--md", md, "--date", "2026-08-17", "--line", line1)
        body = open(md).read() if os.path.isfile(md) else "<missing>"
        check("dataflow-rollup: second cycle appends, first intact",
              "| 2026-08-03 | render-pairing |" in body
              and "| 2026-08-17 | render-pairing |" in body, body)
        p = run_gy("dataflow-rollup", "--md", md, "--date", "2026-08-18",
                   "--line", "not a summary line at all")
        body = open(md).read() if os.path.isfile(md) else ""
        check("dataflow-rollup: unparsable line REFUSED loudly, never a fabricated row",
              p.returncode != 0 and "2026-08-18" not in body,
              (p.returncode, p.stdout, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "dataflow_yield.md")
        # PLANTED: excluded share grows 3 consecutive cycles -> the trend check flags
        with open(md, "w") as fh:
            fh.write("| date | sweep | checked | violations | exempted | unresolvable |\n"
                     "|---|---|---|---|---|---|\n"
                     "| 2026-08-03 | render-pairing | 40 | 0 | 1 | 0 |\n"
                     "| 2026-08-17 | render-pairing | 40 | 0 | 3 | 0 |\n"
                     "| 2026-08-31 | render-pairing | 40 | 0 | 6 | 0 |\n")
        p = run_gy("dataflow-trend", "--md", md)
        check("dataflow-trend: planted grown share -> flagged, nonzero exit",
              p.returncode != 0 and "DATAFLOW TREND" in p.stdout
              and "render-pairing" in p.stdout, (p.returncode, p.stdout, p.stderr))
        # CONTROL: a held/shrinking share does not flag
        with open(md, "w") as fh:
            fh.write("| date | sweep | checked | violations | exempted | unresolvable |\n"
                     "|---|---|---|---|---|---|\n"
                     "| 2026-08-03 | render-pairing | 40 | 0 | 3 | 0 |\n"
                     "| 2026-08-17 | render-pairing | 40 | 0 | 3 | 0 |\n"
                     "| 2026-08-31 | render-pairing | 44 | 0 | 3 | 0 |\n")
        p = run_gy("dataflow-trend", "--md", md)
        check("dataflow-trend: held/shrinking share control -> no flag, exit 0",
              p.returncode == 0 and "DATAFLOW TREND" not in p.stdout,
              (p.returncode, p.stdout))
        p = run_gy("dataflow-trend", "--md", os.path.join(d, "nope.md"))
        check("dataflow-trend: absent record -> unmeasured, exit 0, never zero",
              p.returncode == 0 and "unmeasured" in p.stdout.lower(),
              (p.returncode, p.stdout))

    # v1.25 arch-F4: the series is versioned AT THE CONTRACT — a rollup against a record
    # whose schema stamp differs from the producer's REFUSES (a semantics change must be
    # a conscious migration, never a prose note the comparator ignores)
    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "dataflow_yield.md")
        with open(md, "w") as fh:
            fh.write("# Dataflow-sweep yield record\nschema: 1\n\n"
                     "| date | sweep | checked | violations | exempted | unresolvable |\n"
                     "|---|---|---|---|---|---|\n"
                     "| 2026-08-03 | render-pairing | 152 | 0 | 0 | 0 |\n")
        line = ("dataflow_sweeps render-pairing: checked 40 · violations 0 · "
                "exempted 2 · unresolvable 1")
        p = run_gy("dataflow-rollup", "--md", md, "--date", "2026-08-17", "--line", line)
        check("F4: schema-mismatched record REFUSES the rollup, nothing appended",
              p.returncode != 0 and "schema" in p.stdout.lower()
              and "2026-08-17" not in open(md).read(),
              (p.returncode, p.stdout, p.stderr))
        # CONTROL: a fresh record created by the rollup carries the current stamp and
        # accepts subsequent rollups
        md2 = os.path.join(d, "fresh.md")
        p = run_gy("dataflow-rollup", "--md", md2, "--date", "2026-08-17", "--line", line)
        body = open(md2).read() if os.path.isfile(md2) else "<missing>"
        check("F4: fresh record stamped with the current schema and accepts rows",
              p.returncode == 0 and "schema: 2" in body
              and "| 2026-08-17 | render-pairing |" in body, (p.returncode, body))


def test_dataflow_producer_consumer_seam():
    """v1.24 fold (arch-adversary F3 + tripwire D13b): the summary-line contract is
    exercised at the JOINT — a REAL dataflow_sweeps run's stdout feeds a REAL
    dataflow-rollup, and the run_calibration tail actually lands a committed row in
    the (isolated) record. Four regex dialects with no producer->consumer test was the
    drift surface; this closes it with live plumbing, not re-typed strings."""
    print("\n[test_dataflow_producer_consumer_seam]")
    ds = os.path.join(PLUGIN, "bin", "dataflow_sweeps.py")
    with tempfile.TemporaryDirectory() as d:
        # real producer run on a tiny fixture
        src = os.path.join(d, "src")
        os.makedirs(src)
        with open(os.path.join(src, "clean.py"), "w") as fh:
            fh.write('Z = "{k}".format(k=2)\n')
        cfgp = os.path.join(d, "sweeps.json")
        with open(cfgp, "w") as fh:
            json.dump({"render_pairing": {"scan": ["src"]}}, fh)
        p = subprocess.run([sys.executable, ds, "render-pairing", "--config", cfgp],
                           capture_output=True, text=True, timeout=60)
        lines = [ln for ln in p.stdout.splitlines()
                 if ln.startswith("dataflow_sweeps ") and "checked" in ln]
        check("seam: producer emitted exactly one summary line", len(lines) == 1,
              (p.returncode, p.stdout))
        md = os.path.join(d, "dataflow_yield.md")
        p2 = run_gy("dataflow-rollup", "--md", md, "--date", "2026-08-03",
                    "--line", lines[0] if lines else "<none>")
        body = open(md).read() if os.path.isfile(md) else "<missing>"
        check("seam: real producer line accepted by the real consumer, row landed",
              p2.returncode == 0 and "| 2026-08-03 | render-pairing | 1 | 0 | 0 | 0 |" in body,
              (p2.returncode, body, p2.stdout, p2.stderr))

    # the run_calibration tail exercises the WHOLE seam: stub model run -> sweeps ->
    # rollup row in the ISOLATED sibling record (never the repo's committed file).
    # Isolation is proven by the real record being UNCHANGED (it legitimately exists
    # since the first live calibration cycle, 2026-08-03 — absence was a fixture-era
    # assumption, not the invariant).
    repo_record = os.path.join(REPO, "docs", "calibration", "dataflow_yield.md")
    record_before = open(repo_record).read() if os.path.isfile(repo_record) else None
    with tempfile.TemporaryDirectory() as d:
        stub = os.path.join(d, "claude-stub")
        with open(stub, "w") as fh:
            fh.write("#!/bin/sh\ncat <<'EOF'\n**VERDICT: REFUTED** — authorize() is called "
                     "at cli.py:15 and cli.py:21.\nClaims checked: 1 · confirmed: 0 · "
                     "refuted: 1\nRecommendation: revise.\nEOF\n")
        os.chmod(stub, 0o755)
        env = dict(os.environ)
        env["TDD_PLAYBOOK_YIELD_MD"] = os.path.join(d, "gate_yield.md")
        env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(d, "no-raw.jsonl")
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, "calibration", "run_calibration.py"),
             "--scenario", "false-negative-claim", "--claude-bin", stub, "--history", "",
             "--repeat", "1"],
            capture_output=True, text=True, env=env, timeout=300)
        sibling = os.path.join(d, "dataflow_yield.md")
        check("seam: run_calibration tail lands a committed row in the isolated record",
              p.returncode == 0 and os.path.isfile(sibling)
              and "render-pairing" in open(sibling).read(),
              (p.returncode, p.stdout[-400:], os.path.isfile(sibling)))
        check("seam: run_calibration prints the dataflow yield section",
              "dataflow" in p.stdout.lower(), p.stdout[-400:])
        record_after = open(repo_record).read() if os.path.isfile(repo_record) else None
        check("seam: the repo's real record was NOT touched by the test run",
              record_before == record_after, repo_record)


if __name__ == "__main__":
    main()
