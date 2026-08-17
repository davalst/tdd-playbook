#!/usr/bin/env python3
"""Planted contracts for stable, consumed adversarial-review findings."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
SCRIPT = os.path.join(PLUGIN, "bin", "review_ledger.py")
TOTAL = PASSED = 0


def check(label, condition, detail=""):
    global TOTAL, PASSED
    TOTAL += 1
    if condition:
        PASSED += 1
        print("PASS", label)
    else:
        print("FAIL", label, detail)


def load_module():
    spec = importlib.util.spec_from_file_location("review_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finding(status="incorporated", severity="P1"):
    row = {
        "id": "ARCH-1",
        "severity": severity,
        "summary": "one resolver must own full and affected plans",
        "evidence": ["scripts/civerd_gate.sh:19-72"],
        "status": status,
    }
    if status == "incorporated":
        row["disposition"] = "D1 uses one shared resolver"
    if status == "rejected":
        row["rationale"] = "Evidence disproved by composition-root trace"
    if status == "verified_closed":
        row.update(remediation_commit="a" * 40,
                   closure_review="architecture-adversary",
                   closure_evidence=["test_gate_runner.py::test_full_plan_discovers_live_roster"])
    return row


def record(findings=None):
    return {
        "schema_version": 1,
        "id": "2026-08-07-streamlining-plan-review",
        "kind": "plan",
        "plan": "docs/plans/gated/2026-08-07-assurance-pipeline-streamlining.md",
        "review_range": {"base": "b" * 40, "head": "c" * 40},
        "reviewers": ["architecture-adversary", "integration-adversary"],
        "findings": findings or [finding()],
    }


def test_unresolved_blocker_refused():
    rl = load_module()
    problems = rl.validate_record(record([finding("open", "P1")]), "plant.json",
                                  lambda _sha: True)
    check("PLANTED unresolved P1 is refused", any("unresolved blocker" in p for p in problems), problems)
    control = rl.validate_record(record(), "control.json", lambda _sha: True)
    check("clean incorporated control passes", control == [], control)


def test_false_closure_and_scope_refused():
    rl = load_module()
    closed = finding("verified_closed")
    closed.pop("closure_evidence")
    problems = rl.validate_record(record([closed]), "plant.json", lambda _sha: True)
    check("PLANTED evidence-free closure is refused", any("closure_evidence" in p for p in problems), problems)
    bad = record()
    bad["review_range"]["head"] = "not-a-sha"
    problems = rl.validate_record(bad, "plant.json", lambda _sha: False)
    check("PLANTED invalid review SHA is refused", any("review_range.head" in p for p in problems), problems)


def test_terminal_closure_evidence_and_range_are_executable():
    rl = load_module()
    closed = record([finding("verified_closed")])
    closed["kind"] = "implementation"
    closed["findings"][0]["closure_review"] = "not-a-registered-reviewer"
    closed["findings"][0]["closure_evidence"] = ["not-a-test-or-citation"]
    problems = rl.validate_record(closed, "plant.json", lambda _sha: True,
                                  lambda _target: False)
    check("PLANTED unregistered closure reviewer is refused",
          any("registered reviewer" in p for p in problems), problems)
    check("PLANTED nonexistent closure evidence is refused",
          any("closure_evidence target" in p for p in problems), problems)
    check("PLANTED existing documentation line is not executable closure evidence",
          not rl.closure_evidence_exists(REPO, "README.md:1"))
    check("PLANTED existing but non-dispatched helper is not closure evidence",
          not rl.closure_evidence_exists(
              REPO, "plugins/tdd-playbook/tests/test_review_ledger.py::finding"))
    check("real tuple-dispatched blessed test is executable closure evidence",
          rl.closure_evidence_exists(
              REPO,
              "plugins/tdd-playbook/tests/test_gate_runner.py::test_full_plan_discovers_live_roster"))
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "tests"))
        with open(os.path.join(tmp, "gate-manifest.json"), "w") as fh:
            json.dump({"suite_glob": "tests/test_*.py"}, fh)
        with open(os.path.join(tmp, "tests", "test_hidden.py"), "w") as fh:
            fh.write("def test_hidden():\n    pass\n\n"
                     "def main():\n    if False:\n        test_hidden()\n")
        check("PLANTED blessed test behind if False is not executable evidence",
              not rl.closure_evidence_exists(tmp, "tests/test_hidden.py::test_hidden"))
        with open(os.path.join(tmp, "tests", "test_negated.py"), "w") as fh:
            fh.write("def test_negated():\n    pass\n\n"
                     "if __name__ != '__main__':\n    test_negated()\n")
        check("PLANTED test behind negated main guard is not executable evidence",
              not rl.closure_evidence_exists(tmp, "tests/test_negated.py::test_negated"))
    topology = rl.topology_problems([closed], lambda _base, _head: False)
    check("PLANTED non-ancestral review range is refused",
          any("base is not an ancestor" in p for p in topology), topology)


def test_directory_consumes_records_and_rejects_duplicate_ids():
    rl = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "one.json"), "w") as fh:
            json.dump(record(), fh)
        second = record()
        second["id"] = "another-review"
        with open(os.path.join(tmp, "two.json"), "w") as fh:
            json.dump(second, fh)
        problems = rl.validate_directory(tmp, lambda _sha: True)
        check("PLANTED duplicate finding ID across packets is refused",
              any("duplicate finding id" in p for p in problems), problems)


def test_preimplementation_review_cannot_cover_candidate():
    rl = load_module()
    plan_only = record()
    problems = rl.coverage_problems([plan_only], "d" * 40,
                                    lambda _base, _head: True, [])
    check("PLANTED old plan-only review does not cover implementation candidate",
          any("implementation review" in p for p in problems), problems)
    implementation = record([finding("verified_closed")])
    implementation["id"] = "implementation-review"
    implementation["kind"] = "implementation"
    implementation["review_range"] = {"base": "b" * 40, "head": "c" * 40}
    control = rl.coverage_problems([implementation], "d" * 40,
                                   lambda _base, _head: True,
                                   ["docs/reviews/implementation.json",
                                    "docs/reference/current-state.md"])
    check("verified implementation review plus metadata-only tail covers candidate",
          control == [], control)


def test_append_only_index_refuses_deleted_record():
    rl = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name in ("one.json", "two.json"):
            path = os.path.join(tmp, name)
            with open(path, "w") as fh:
                json.dump(record(), fh)
            paths.append(path)
        index = {"schema_version": 1, "records": [
            {"path": os.path.basename(path), "sha256": rl.file_hash(path)} for path in paths
        ]}
        check("append-only index clean control passes",
              rl.validate_index(tmp, index, []) == [])
        os.unlink(paths[0])
        problems = rl.validate_index(tmp, index, [])
        check("PLANTED deletion of one valid review record is refused",
              any("missing indexed review" in p for p in problems), problems)


def test_repository_review_records_are_valid():
    rl = load_module()
    problems = rl.validate_repository(REPO)
    check("repository review records are consumed and valid", problems == [], problems)


# --------------------------------------------------- D-A: taxonomy + recurrence (2026-08-14)

def _dated_record(record_id, findings):
    row = record(findings)
    row["id"] = record_id
    return row


def _keyed(fid, cls, key, catalog_row=None, status="incorporated"):
    row = finding(status)
    row["id"] = fid
    if cls is not None:
        row["class"] = cls
    if key is not None:
        row["recurrence_key"] = key
    if catalog_row is not None:
        row["catalog_row"] = catalog_row
    return row


def test_taxonomy_required_after_ship_date():
    """Every finding says what KIND of miss it was — mechanically catchable
    (`deterministic`) or needing a mind (`judgment`) — plus a short recurrence key.
    Required for records dated on/after TAXONOMY_SHIP_DATE; earlier append-only history
    stays untouched (optional, validated when present)."""
    rl = load_module()
    post = rl.TAXONOMY_SHIP_DATE + "-post-ship-review"

    bare = rl.validate_record(_dated_record(post, [finding()]), "plant.json", lambda _s: True)
    check("PLANTED post-ship finding without class is refused",
          any(".class" in p for p in bare), bare)
    check("PLANTED post-ship finding without recurrence_key is refused",
          any(".recurrence_key" in p for p in bare), bare)

    good = rl.validate_record(
        _dated_record(post, [_keyed("ARCH-1", "deterministic", "grep-counts-docstrings")]),
        "control.json", lambda _s: True)
    check("post-ship finding WITH class + key passes", good == [], good)

    # boundary: dated exactly the ship date -> required (>=, not >)
    boundary = rl.validate_record(_dated_record(post, [finding()]), "plant.json", lambda _s: True)
    check("ship-date boundary: record dated exactly TAXONOMY_SHIP_DATE requires the fields",
          any(".class" in p for p in boundary), boundary)

    # pre-ship history: optional (the real 88-finding corpus is the standing control,
    # test_repository_review_records_are_valid), but VALIDATED when present
    pre_bad = rl.validate_record(
        _dated_record("2026-08-07-old-review", [_keyed("ARCH-1", "vibes", "some-key")]),
        "plant.json", lambda _s: True)
    check("PLANTED unknown class value is refused even pre-ship",
          any(".class" in p for p in pre_bad), pre_bad)

    for bad_key in ("Grep Counts", "a\nb", "pipe|key", "UPPER-CASE", "-leading", ""):
        problems = rl.validate_record(
            _dated_record(post, [_keyed("ARCH-1", "deterministic", bad_key)]),
            "plant.json", lambda _s: True)
        check("PLANTED malformed recurrence_key {!r} is refused (keys reach report lines)"
              .format(bad_key), any(".recurrence_key" in p for p in problems), problems)

    cat_bad = rl.validate_record(
        _dated_record(post, [_keyed("ARCH-1", "deterministic", "k-one", catalog_row="X9")]),
        "plant.json", lambda _s: True)
    check("PLANTED malformed catalog_row is refused", any("catalog_row" in p for p in cat_bad),
          cat_bad)
    cat_ok = rl.validate_record(
        _dated_record(post, [_keyed("ARCH-1", "deterministic", "k-one", catalog_row="H11")]),
        "control.json", lambda _s: True)
    check("H-row catalog_row passes", cat_ok == [], cat_ok)

    # arch F9: shape is not membership — H99 must not print as though it names a row
    phantom_row = rl.validate_record(
        _dated_record(post, [_keyed("ARCH-1", "deterministic", "k-one", catalog_row="H99")]),
        "plant.json", lambda _s: True, catalog_exists=lambda _row: False)
    check("PLANTED catalog_row naming no real map row is refused",
          any("not a row" in p for p in phantom_row), phantom_row)
    rows = rl.catalog_rows(REPO)
    check("the real catalog parses to a non-vacuous row set containing H11 (§4a)",
          rows is not None and "H11" in rows and len(rows) >= 10,
          sorted(rows or [])[:5])
    with tempfile.TemporaryDirectory() as tmp:
        check("a tree without the catalog degrades to None (shape-only), stated not silent",
              rl.catalog_rows(tmp) is None)

    undated = rl.validate_record(_dated_record("no-date-prefix", [finding()]),
                                 "plant.json", lambda _s: True)
    check("PLANTED record id without a YYYY-MM-DD prefix is refused (not a crash)",
          any("YYYY-MM-DD" in p for p in undated), undated)

    check("FINDING_CLASSES is the one machine owner (deterministic|judgment)",
          rl.FINDING_CLASSES == ("deterministic", "judgment"), rl.FINDING_CLASSES)


def test_recurrence_report():
    """A recurrence_key in >=2 DISTINCT records at class deterministic is an UNBUILT
    GUARD — a machine could have caught it twice and none exists. Recurring judgment is
    not a missing guard. Output feeds the HACK_CATALOG Guard <-> entry map, never a
    parallel list."""
    rl = load_module()
    twice = [
        _dated_record("2026-08-15-first", [_keyed("A-1", "deterministic",
                                                  "grep-counts-docstrings")]),
        _dated_record("2026-08-16-second", [_keyed("B-1", "deterministic",
                                                   "grep-counts-docstrings")]),
    ]
    lines = rl.recurrence_report(twice)
    unbuilt = [l for l in lines if "UNBUILT GUARD" in l]
    check("deterministic key in 2 records -> exactly one UNBUILT GUARD line",
          len(unbuilt) == 1 and "grep-counts-docstrings" in unbuilt[0], lines)
    check("...that names no catalog row -> proposes one",
          "propose" in unbuilt[0], unbuilt)

    judgment = [
        _dated_record("2026-08-15-first", [_keyed("A-1", "judgment", "scope-taste")]),
        _dated_record("2026-08-16-second", [_keyed("B-1", "judgment", "scope-taste")]),
    ]
    check("judgment key in 2 records -> NO unbuilt-guard line (recurring judgment is not a missing guard)",
          not any("UNBUILT GUARD" in l for l in rl.recurrence_report(judgment)),
          rl.recurrence_report(judgment))

    single = [_dated_record("2026-08-15-first", [_keyed("A-1", "deterministic", "once-only")])]
    check("single occurrence -> silent", not any("once-only" in l and "UNBUILT" in l
                                                 for l in rl.recurrence_report(single)))

    same_record = [_dated_record("2026-08-15-first", [
        _keyed("A-1", "deterministic", "same-rec-key"),
        _keyed("A-2", "deterministic", "same-rec-key")])]
    check("same key twice in ONE record counts as one record -> no unbuilt-guard",
          not any("UNBUILT GUARD" in l for l in rl.recurrence_report(same_record)),
          rl.recurrence_report(same_record))

    mixed = twice + [_dated_record("2026-08-17-third", [_keyed("C-1", "judgment",
                                                               "grep-counts-docstrings")])]
    check("mixed classes: the deterministic leg alone triggers",
          any("UNBUILT GUARD" in l for l in rl.recurrence_report(mixed)))

    rowed = [
        _dated_record("2026-08-15-first", [_keyed("A-1", "deterministic", "k-two", "H11")]),
        _dated_record("2026-08-16-second", [_keyed("B-1", "deterministic", "k-two")]),
    ]
    check("a catalog_row in the group is surfaced on the UNBUILT GUARD line",
          any("UNBUILT GUARD" in l and "H11" in l for l in rl.recurrence_report(rowed)),
          rl.recurrence_report(rowed))

    # A7 coverage ratio: denominator is ALL findings — re-keying cannot shrink it
    ratio_fixture = [
        _dated_record("2026-08-15-first", [_keyed("A-1", "deterministic", "k-one"),
                                           finding()]),
        _dated_record("2026-08-16-second", [_keyed("B-1", "judgment", "k-three"),
                                            finding()]),
    ]
    lines = rl.recurrence_report(ratio_fixture)
    check("denominator line: records + findings + keyed-of-total ratio",
          any("records 2" in l and "findings 4" in l and "keyed 2 of 4" in l for l in lines),
          lines)


def test_recurrence_verb_vacuity_and_usage_event():
    """The verb through the real script: vacuous refusal (exit 3) on zero records — a
    reader must never mistake an empty scan for a clean one (§4a) — and ONE machine
    usage event through the single write path, so the usage denominator moves without
    anyone remembering to report (§6b)."""
    import subprocess, sys as _sys
    rl = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        env = {k: v for k, v in os.environ.items() if not k.startswith("TDD_PLAYBOOK")}
        env["CLAUDE_PROJECT_DIR"] = tmp
        os.makedirs(os.path.join(tmp, "docs", "reviews"))
        p = subprocess.run([_sys.executable, SCRIPT, "recurrence"], capture_output=True,
                           text=True, env=env, timeout=30)
        check("zero records -> exit 3 vacuous refusal, stated", p.returncode == 3
              and "VACUOUS" in (p.stderr + p.stdout).upper(), (p.returncode, p.stderr))

        for name, rec in (("one.json", _dated_record(
                "2026-08-15-first", [_keyed("A-1", "deterministic", "k-live")])),
                          ("two.json", _dated_record(
                "2026-08-16-second", [_keyed("B-1", "deterministic", "k-live")]))):
            with open(os.path.join(tmp, "docs", "reviews", name), "w") as fh:
                json.dump(rec, fh)
        ylog = os.path.join(tmp, "yield.jsonl")
        env["TDD_PLAYBOOK_YIELD_LOG"] = ylog
        p = subprocess.run([_sys.executable, SCRIPT, "recurrence"], capture_output=True,
                           text=True, env=env, timeout=30)
        check("recurrence over real records exits 0 and prints the unbuilt-guard line",
              p.returncode == 0 and "UNBUILT GUARD" in p.stdout, (p.returncode, p.stdout))
        rows = ([json.loads(x) for x in open(ylog)] if os.path.isfile(ylog) else [])
        check("ONE machine usage event lands via the single write path",
              any(r.get("gate") == "review-ledger" and r.get("event") == "usage"
                  for r in rows), rows[:3])


def test_reviewer_vocabulary_bound_to_roster():
    """D3 (2026-08-17 adversary-accountability): `reviewers` is bound to the real agent
    roster plus an explicit non-agent vocabulary, so a typo or a stale name is refused
    instead of recorded.

    Pre-fix shape (§13 guard calibration): `reviewers` was checked only by
    `_strings(record.get("reviewers"))` — non-empty list of non-empty strings — so
    `sekurity-adversary`, a renamed agent, or any invented name validated clean. Every
    participation count read off that field was therefore only as good as its spelling.

    TWO-PART compatibility contract, because the cutoff alone does NOT survive later
    renames (the defect Codex caught in review):
      (1) cutoff — records dated before REVIEWER_VOCAB_SHIP_DATE keep append-only history
          valid across the rollout;
      (2) agent filenames are CANONICAL IDS and are not renamed — already enforced at
          test_agents.py:111 and :588 — with a renamed ID joining NON_AGENT_REVIEWERS as
          a historical alias if that ever becomes necessary."""
    rl = load_module()
    post = rl.REVIEWER_VOCAB_SHIP_DATE + "-reviewer-vocab-review"
    roster = {"architecture-adversary", "integration-adversary"}
    known = lambda name: name in roster or name in rl.NON_AGENT_REVIEWERS

    def dated(rid, reviewers):
        row = record([_keyed("ARCH-1", "deterministic", "reviewer-field-unbound")])
        row["id"] = rid
        row["reviewers"] = reviewers
        return row

    good = rl.validate_record(dated(post, ["architecture-adversary"]), "control.json",
                              lambda _s: True, reviewer_known=known)
    check("post-cutoff record naming a real agent passes", good == [], good)

    token = rl.validate_record(dated(post, ["self-review"]), "control.json",
                               lambda _s: True, reviewer_known=known)
    check("post-cutoff record naming a non-agent token passes", token == [], token)

    for bad in ("sekurity-adversary", "architecture_adversary", "Architecture-Adversary",
                "dogfooding"):
        problems = rl.validate_record(dated(post, [bad]), "plant.json",
                                      lambda _s: True, reviewer_known=known)
        check("PLANTED unrecognised reviewer {!r} is refused".format(bad),
              any("reviewers" in p for p in problems), problems)
        # adoption rule: an error that names the problem must name the next step
        check("PLANTED {!r} refusal enumerates the accepted vocabulary".format(bad),
              any("self-review" in p for p in problems), problems)

    grandfathered = rl.validate_record(dated("2026-08-07-old-review", ["whoever-reviewed-this"]),
                                       "control.json", lambda _s: True, reviewer_known=known)
    check("pre-cutoff history with an unknown reviewer is untouched",
          grandfathered == [], grandfathered)

    boundary = rl.validate_record(dated(post, ["not-an-agent"]), "plant.json",
                                  lambda _s: True, reviewer_known=known)
    check("cutoff boundary: dated exactly REVIEWER_VOCAB_SHIP_DATE is BOUND (>=, not >)",
          any("reviewers" in p for p in boundary), boundary)

    # rename escape hatch: a former canonical ID carried as a historical alias
    alias = rl.validate_record(dated(post, ["retired-adversary"]), "control.json",
                               lambda _s: True,
                               reviewer_known=lambda n: known(n) or n == "retired-adversary")
    check("a historical alias keeps immutable history valid through a rename",
          alias == [], alias)

    # downstream degradation: no roster to bind to (codex vendoring carries no agents/)
    degraded = rl.validate_record(dated(post, ["anything-at-all"]), "control.json",
                                  lambda _s: True)
    check("roster absent -> shape-only, NEVER a crash (the catalog_rows contract)",
          degraded == [], degraded)

    empty = rl.validate_record(dated(post, []), "plant.json", lambda _s: True,
                               reviewer_known=known)
    check("an EMPTY reviewers list is still refused (vocabulary never relaxes shape)",
          any("reviewers" in p for p in empty), empty)


def test_participation_report():
    """D4 (2026-08-17 adversary-accountability): RECORDED REVIEW PARTICIPATION — for every
    agent in the roster, how many indexed records NAME it.

    What it does not claim, deliberately: `reviewers` is hand-authored, so this can only
    show what was RECORDED, never that an agent ran. The plan's first draft called this
    "usage"/"dispatch" and proposed the finding key
    `adversary-built-registered-never-dispatched`; both were dropped in review because the
    machine cannot establish "never dispatched," and a gate on a hand-typed field would
    reward name-stuffing.

    No partition and no exemption list: earlier drafts split the roster judgment-vs-
    mechanical and three reviewers flagged that as an Nth-copy classification and an
    unpinned darkness hatch. Printing the WHOLE roster deletes the problem instead of
    relocating it — nothing is flagged, so nothing can be false-flagged
    (run_calibration.py:55-59: "the roster stays DERIVED, never a second hand-maintained
    list")."""
    rl = load_module()

    def rec(rid, reviewers):
        return {"id": rid, "reviewers": reviewers, "findings": []}

    records = [rec("2026-08-01-a", ["architecture-adversary", "self-review"]),
               rec("2026-08-02-b", ["architecture-adversary"]),
               rec("2026-08-03-c", ["integration-adversary"])]
    roster = {"architecture-adversary", "integration-adversary", "observability-adversary"}
    producers = {"architecture-adversary", "integration-adversary"}

    lines = rl.participation_report(records, roster, producers)
    body = "\n".join(lines)

    check("counts the records that NAME each agent",
          any("architecture-adversary" in l and "2" in l for l in lines), lines)
    check("an agent named in no record is shown, not omitted",
          "observability-adversary" in body, lines)
    check("zero is worded as NOT NAMED, never as unused/never-dispatched",
          "not named in any indexed review" in body
          and "dispatch" not in body.lower() and "never used" not in body.lower(), lines)
    check("record-authoring briefs are marked so a real zero is legible",
          any("observability-adversary" in l and "authors records" not in l for l in lines)
          and any("architecture-adversary" in l and "authors records" in l for l in lines),
          lines)
    check("non-agent reviewer tokens are not counted as roster participation",
          "self-review" not in body, lines)

    # the §4a invariant: counts reconcile with the (record, reviewer) pairs they summarise
    pairs = sum(1 for r in records for name in r["reviewers"] if name in roster)
    counted = sum(int(tok) for l in lines for tok in [l.rsplit(" ", 1)[-1]] if tok.isdigit())
    check("PROPERTY: counts sum to the (record, reviewer) pairs inside the roster",
          counted == pairs, (counted, pairs))

    empty = "\n".join(rl.participation_report([], roster, producers))
    check("zero records -> unmeasured, never a vacuous 100%",
          "unmeasured" in empty, empty)

    # vacuity guard on the enumerator (§6c, mandatory) — an empty roster must not pass
    # green having enumerated nothing
    vacuous = "\n".join(rl.participation_report(records, set(), producers))
    check("VACUITY: an empty roster refuses rather than printing an empty clean list",
          "unmeasured" in vacuous or "vacuous" in vacuous, vacuous)

    # downstream: no roster to enumerate (codex vendoring carries no agents/)
    absent = "\n".join(rl.participation_report(records, None, producers))
    check("roster None -> the block states WHY it is absent, never silently empty",
          "roster" in absent.lower() and absent.strip() != "", absent)

    # §1 seam rule: assert at the seam this code does NOT own. The producer emitting a
    # block proves nothing about whether anyone reads it — and the whole reason this
    # deliverable exists is that its first design had only an opt-in reader. So read the
    # ALWAYS-ON surface: docs/reference/current-state.md, regenerated at every release.
    committed = open(os.path.join(REPO, "docs", "reference", "current-state.md"),
                     encoding="utf-8").read()
    check("the participation block REACHES the always-on reference surface",
          "participation:" in committed, "not found in committed current-state.md")
    real_roster = rl.agents_roster(REPO)
    check("every roster member is accounted for on that surface (no silent narrowing)",
          real_roster and all(name in committed for name in real_roster),
          sorted(n for n in (real_roster or ()) if n not in committed))


def _vendor_bin(real):
    """Mirror the REAL vendored layout: install_into_repo copies bin/ as a whole tree,
    so review_ledger.py always ships beside its dataflow_sweeps/_debt/host_parity
    siblings — a test tree with the script alone would be a layout the installer cannot
    produce. host_parity joined the roster when D3 (2026-08-17) made the reviewer field
    resolve canonical agent IDs through it."""
    import shutil
    os.makedirs(os.path.join(real, ".claude", "bin"))
    for sibling in ("review_ledger.py", "dataflow_sweeps.py", "_debt.py", "host_parity.py"):
        shutil.copy2(os.path.join(PLUGIN, "bin", sibling),
                     os.path.join(real, ".claude", "bin", sibling))
    return os.path.join(real, ".claude", "bin", "review_ledger.py")


def test_root_resolution_vendored_and_canonical():
    """A12 — pre-existing shipped defect: four dirname hops resolve to the repo's PARENT
    from a vendored `.claude/bin/`. Pre-fix shape (§13 guard calibration — the sha is the
    anchor): `git show ba16fe4:plugins/tdd-playbook/bin/review_ledger.py` line 328,
    `os.path.dirname(` ×4 over `__file__`. Fix order (arch F1/F2):
    TDD_PLAYBOOK_PROJECT_ROOT (the Codex adapter contract) → CLAUDE_PROJECT_DIR → walk
    up to the dir holding docs/reviews → REFUSE (None) — the old four-hop fallback
    reproduced the defect and is gone."""
    rl = load_module()
    saved = {var: os.environ.pop(var, None)
             for var in ("CLAUDE_PROJECT_DIR", "TDD_PLAYBOOK_PROJECT_ROOT")}
    try:
        check("in-repo layout resolves to the repo root",
              os.path.realpath(rl.resolve_root()) == os.path.realpath(REPO),
              rl.resolve_root())
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.realpath(tmp)
            vendored = _vendor_bin(real)
            os.makedirs(os.path.join(real, "docs", "reviews"))
            spec = importlib.util.spec_from_file_location("review_ledger_vendored", vendored)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            check("vendored .claude/bin layout resolves to the HOST repo root, not its parent",
                  os.path.realpath(module.resolve_root()) == real, module.resolve_root())
            os.environ["CLAUDE_PROJECT_DIR"] = os.path.join(real, "docs")
            check("CLAUDE_PROJECT_DIR wins when set",
                  os.path.realpath(module.resolve_root()) ==
                  os.path.realpath(os.path.join(real, "docs")), module.resolve_root())
            os.environ["TDD_PLAYBOOK_PROJECT_ROOT"] = real
            check("TDD_PLAYBOOK_PROJECT_ROOT (the adapter contract) outranks it",
                  os.path.realpath(module.resolve_root()) == real, module.resolve_root())
            del os.environ["CLAUDE_PROJECT_DIR"]
            del os.environ["TDD_PLAYBOOK_PROJECT_ROOT"]
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.realpath(tmp)
            vendored = _vendor_bin(real)  # NO docs/reviews anywhere up the tree
            spec = importlib.util.spec_from_file_location("review_ledger_stranded", vendored)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            check("exhausted walk-up REFUSES (None) instead of guessing a parent",
                  module.resolve_root() is None, module.resolve_root())
            import subprocess, sys as _sys
            env = {k: v for k, v in os.environ.items() if k not in
                   ("CLAUDE_PROJECT_DIR", "TDD_PLAYBOOK_PROJECT_ROOT")}
            p = subprocess.run([_sys.executable, vendored, "recurrence"],
                               capture_output=True, text=True, env=env, timeout=30)
            check("...and the verb states the real problem (exit 2, names the env vars)",
                  p.returncode == 2 and "CLAUDE_PROJECT_DIR" in p.stderr,
                  (p.returncode, p.stderr))
    finally:
        for var, value in saved.items():
            if value is not None:
                os.environ[var] = value


if __name__ == "__main__":
    test_unresolved_blocker_refused()
    test_false_closure_and_scope_refused()
    test_terminal_closure_evidence_and_range_are_executable()
    test_directory_consumes_records_and_rejects_duplicate_ids()
    test_preimplementation_review_cannot_cover_candidate()
    test_append_only_index_refuses_deleted_record()
    test_repository_review_records_are_valid()
    test_taxonomy_required_after_ship_date()
    test_reviewer_vocabulary_bound_to_roster()
    test_participation_report()
    test_recurrence_report()
    test_recurrence_verb_vacuity_and_usage_event()
    test_root_resolution_vendored_and_canonical()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
