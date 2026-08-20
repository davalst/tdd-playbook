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



def test_small_change_lane_cannot_be_talked_into():
    """The SMALL-CHANGE LANE — and the reason it is safe to have one.

    Origin (2026-08-18, measured): narrowing one regex cost five sequential ledger refusals,
    two ledger-entry attempts, three doc regenerations and six full gate runs. One of those
    five refusals caught something real (a fabricated SHA); the other four were schema
    friction. The recording cost is FIXED while the benefit scales with change size, so the
    same apparatus that earns its keep on a feature is pure tax on a fix. David's standing
    rule is to avoid bureaucracy that provides little or no value.

    TWO properties make the lane un-gameable, and they matter more than the lane itself:

    1. ELIGIBILITY IS COMPUTED FROM THE DIFF, never declared. The agent cannot assert
       "this is small" — `small_change_eligible` reads the changed paths and the line counts.
       There is no flag, no env var, and deliberately no --force: an override is the thing a
       motivated agent reaches for, so it does not exist.
    2. THE LANE RELAXES PAPERWORK, NEVER A CHECK. Same gate, same red-first, same
       no-weakening rules. What it removes is prose weight. So there is nothing worth
       cheating FOR — a lie that got you in would save you a paragraph and still leave every
       verification standing. That asymmetry, not the classifier, is the real defense."""
    rl = load_module()

    ok, why = rl.small_change_eligible(
        ["plugins/tdd-playbook/bin/grade_from_otel.py",
         "plugins/tdd-playbook/tests/test_grade_from_otel.py"], 20, 4)
    check("a small edit to ordinary code WITH its test is eligible", ok, why)

    # every disqualifier is a SURFACE whose change a human should read in full
    for paths, label in [
        (["plugins/tdd-playbook/skills/tdd-playbook/SKILL.md"], "doctrine"),
        (["plugins/tdd-playbook/agents/claims-verifier.md"], "an agent brief"),
        (["plugins/tdd-playbook/commands/claims.md"], "a command"),
        (["plugins/tdd-playbook/hooks/scripts/tag_guard.py"], "a guard"),
        (["capabilities.json"], "the registry"),
        (["scripts/install_into_repo.py"], "the installer"),
        (["calibration/corpus/approved/x.json"], "the plant corpus"),
        (["calibration/scenarios.json"], "an oracle"),
        (["docs/plans/gated/2026-08-17-x.md"], "a gated plan"),
        (["CLAUDE.md"], "standing instructions"),
    ]:
        ok, why = rl.small_change_eligible(paths, 3, 0)
        check("DISQUALIFIED even at 3 lines — {}".format(label), not ok, (paths, why))
        check("...and the refusal says WHICH surface: {}".format(label),
              bool(why) and paths[0].split("/")[-1][:8] in why or "surface" in (why or ""),
              why)

    # size caps: a big diff is not small however innocent its paths
    ok, why = rl.small_change_eligible(["src/a.py"], 400, 0)
    check("DISQUALIFIED by size (too many lines)", not ok, why)
    ok, why = rl.small_change_eligible(["src/%d.py" % i for i in range(12)], 10, 0)
    check("DISQUALIFIED by breadth (too many files)", not ok, why)

    # the anti-cheat itself: no override may exist anywhere in the module
    import inspect
    src = inspect.getsource(rl)
    for bad in ("--force", "force=True", "SMALL_CHANGE_OVERRIDE", "TDD_PLAYBOOK_SMALL"):
        check("no override exists for the lane: {!r}".format(bad), bad not in src)
    sig = inspect.signature(rl.small_change_eligible)
    check("the classifier takes only FACTS about the diff, no caller opinion",
          list(sig.parameters) == ["changed_paths", "insertions", "deletions"],
          list(sig.parameters))

    # a mixed diff is judged by its most dangerous path, never averaged
    ok, why = rl.small_change_eligible(
        ["README.md", "plugins/tdd-playbook/hooks/scripts/tag_guard.py"], 5, 1)
    check("one disqualifying path poisons an otherwise-small diff", not ok, why)

    # THE LANE STILL REQUIRES TDD. It reduces recording weight; it must never become a way
    # to land code without a test. A source change with no test alongside it is exactly the
    # shape that must NOT get a fast path — the §1/§6 smell the telemetry grader already
    # flags, made a precondition instead of an observation.
    ok, why = rl.small_change_eligible(["plugins/tdd-playbook/bin/grade_from_otel.py"], 15, 2)
    check("source-only change is REFUSED the lane (no test alongside)", not ok, why)
    check("...and the refusal names the missing test, not just 'ineligible'",
          "test" in (why or "").lower(), why)
    ok, why = rl.small_change_eligible(
        ["plugins/tdd-playbook/bin/grade_from_otel.py",
         "plugins/tdd-playbook/tests/test_grade_from_otel.py"], 15, 2)
    check("source + its test IS eligible (TDD preserved, paperwork reduced)", ok, why)
    ok, why = rl.small_change_eligible(["docs/notes.md"], 5, 0)
    check("a docs-only change needs no test to be eligible", ok, why)

    # and nothing about the lane may touch verification: same gate, same suites, same rules
    src2 = inspect.getsource(rl.small_change_eligible)
    for forbidden in ("skip", "bypass", "disable", "--no-verify"):
        check("the classifier never speaks of skipping anything: {!r}".format(forbidden),
              forbidden not in src2.lower())


def test_small_lane_still_demands_verification_and_the_right_adversaries():
    """The lane reduces PAPERWORK. Verification and judgment are not paperwork.

    David's correction while this was being built: "small change lane still needs the tdd
    approach and other functional bits, not just shutting off the things that work" and
    "verification is also required and potentially the appropriate adversarial agents".

    So the lane carries three POSITIVE preconditions, not merely an absence of relaxations:
      1. a test beside the source (asserted in the classifier above),
      2. a GREEN gate on the tree being recorded — verification is never the thing traded,
      3. the adversaries the DIFF calls for, derived from what it touches rather than
         remembered by whoever is tired.

    (3) is what keeps this from being blanket ceremony. A fix touching nothing sensitive
    requires no adversary at all — most small changes are that. A fix touching auth or an
    egress path requires exactly one. The cost lands on the changes that earn it, which is
    the whole difference between a control and a tax."""
    rl = load_module()

    # DERIVED, not remembered: the diff says which lens is needed
    for paths, expected, why in [
        (["src/auth/session.py", "tests/test_session.py"], "security-adversary",
         "auth is the CISO loss function"),
        (["src/net/egress.py", "tests/test_egress.py"], "security-adversary",
         "egress is the same"),
        (["src/worker/retry.py", "tests/test_retry.py"], "observability-adversary",
         "a retry path fails silently at 3am"),
        (["scripts/verify_install.sh"], "script-adversary",
         "an operator script can pass having tested nothing"),
    ]:
        got = rl.suggested_adversaries(paths)
        check("derived adversary for {} — {}".format(paths[0], why), expected in got, got)

    quiet = rl.suggested_adversaries(["plugins/tdd-playbook/bin/grade_from_otel.py",
                                      "plugins/tdd-playbook/tests/test_grade_from_otel.py"])
    check("an ordinary fix summons NO adversary (cost lands where it is earned)",
          quiet == [], quiet)

    # TEST-ONLY diffs earn the test-quality lens — and only those. Asking for it whenever a
    # test changed would summon an adversary on EVERY eligible diff, because the lane
    # requires a test beside the source: blanket ceremony, which is what this lane removes.
    # The risk worth a second pair of eyes is a test changed with no source behind it.
    check("a TEST-ONLY diff earns the test-quality lens (a weakening hides cheapest here)",
          "test-quality-adversary" in rl.suggested_adversaries(["tests/test_a.py"]),
          rl.suggested_adversaries(["tests/test_a.py"]))
    check("source + its test does NOT — that is the healthy shape, not a risk",
          "test-quality-adversary" not in rl.suggested_adversaries(
              ["src/a.py", "tests/test_a.py"]),
          rl.suggested_adversaries(["src/a.py", "tests/test_a.py"]))

    # VERIFICATION IS NOT NEGOTIABLE: a record cannot claim the lane without a green gate
    ok, why = rl.small_lane_preconditions(
        ["src/a.py", "tests/test_a.py"], 10, 2, gate_green=False, accounted=[])
    check("PLANTED: the lane is refused when the gate is not green", not ok, why)
    check("...and the refusal names the gate", "gate" in (why or "").lower(), why)

    ok, why = rl.small_lane_preconditions(
        ["src/auth/session.py", "tests/test_session.py"], 10, 2,
        gate_green=True, accounted=[])
    check("PLANTED: a security-touching diff is refused with no adversary accounted",
          not ok, why)
    check("...and the refusal NAMES the adversary it wants",
          "security-adversary" in (why or ""), why)

    ok, why = rl.small_lane_preconditions(
        ["src/auth/session.py", "tests/test_session.py"], 10, 2,
        gate_green=True, accounted=["security-adversary"])
    check("accounting for the derived adversary satisfies the lane", ok, why)

    ok, why = rl.small_lane_preconditions(
        ["plugins/tdd-playbook/bin/grade_from_otel.py",
         "plugins/tdd-playbook/tests/test_grade_from_otel.py"], 10, 2,
        gate_green=True, accounted=[])
    check("an ordinary green fix needs nothing further — THIS is the nimbleness", ok, why)


def test_records_are_optional_evidence_not_a_per_commit_toll():
    """Records are OPT-IN evidence. A commit without one is not a violation.

    Removed 2026-08-18. `coverage_problems` required every non-metadata commit to be covered by
    a closed implementation review whose tail touched only docs/reviews/ or current-state.md.
    It was the single obligation that fired on EVERY commit, and its output was unconsumed: 205
    findings, 57% keyed, 12 UNBUILT-GUARD keys, and zero guards built from any of them.

    Stated cost, with eyes open: `recurrence` may become sporadic or purely historical. There is
    no replacement trigger and this test does not pretend otherwise — the six authoring briefs
    say "Review record output (when these findings land in docs/reviews/)", i.e. they specify
    FIELDS when a record is written and never require one. An earlier draft of this change
    claimed those briefs were a live trigger; that was unverified and wrong.

    What is NOT relaxed, and this test's real job: a record that IS written still gets the full
    schema teeth. Optional never means unchecked."""
    rl = load_module()

    check("the per-commit coverage rule is GONE, not merely unwired",
          not hasattr(rl, "coverage_problems"),
          "coverage_problems still exists — dead tested code preserves the old policy")

    # the live repo: HEAD carries no covering record and that is now fine
    problems = rl.validate_repository(REPO)
    coverage = [p for p in problems if "not covered by a closed implementation review" in p]
    check("an UNCOVERED HEAD is no longer a violation", coverage == [], coverage)
    check("this repo validates clean with records optional", problems == [], problems[:3])

    # ...and the schema still bites on a record that IS written
    bad = record([finding("open", "P1")])
    check("an INVALID opt-in record still fails (optional is not unchecked)",
          rl.validate_record(bad, "plant.json", lambda _s: True) != [],
          "schema teeth were lost with the toll")

    # Removing the rule removed the test that proved it — and two IMMUTABLE records cite that
    # test as closure evidence for findings that were defects IN the rule. History cannot be
    # edited to follow the code, so the retirement is NAMED rather than tolerated generally.
    retired = ("plugins/tdd-playbook/tests/test_review_ledger.py::"
               "test_preimplementation_review_cannot_cover_candidate")
    check("closed history citing the retired test stays valid",
          rl.closure_evidence_exists(REPO, retired))
    check("the retirement is NAMED with its reason, not a silent allowance",
          retired in rl.RETIRED_EVIDENCE and "2026-08-18" in rl.RETIRED_EVIDENCE[retired])
    check("PLANTED: an unnamed missing evidence target still FAILS",
          not rl.closure_evidence_exists(REPO, "tests/test_ghost.py::test_nothing"))

    # the reader survives the producer becoming optional
    recs = rl._records(os.path.join(REPO, "docs", "reviews"))
    check("recurrence still runs on whatever records exist",
          any("recurrence:" in line for line in rl.recurrence_report(recs)))


# ------------------------------------- D1: the epoch reset + the forward guard answer (2026-08-20)

def _guarded(fid, cls, key, guard, status="incorporated"):
    row = _keyed(fid, cls, key, status=status)
    if guard is not None:
        row["guard"] = guard
    return row


def test_recurrence_epoch_retires_the_old_list():
    """PLANTED (v1.45, 2026-08-20): the recurrence list could not see a guard that had been
    BUILT, so it nagged forever; one of its keys was a junk drawer of five unrelated
    findings; and the field linking a defect to its check was present on 6 of 205 findings,
    two of the three load-bearing ones pointing at the wrong catalog row.

    Retroactively classifying that history needs judgment nobody can supply honestly
    (David is non-technical; the agent cannot invent what an old defect meant). So the
    history is RETIRED WHOLESALE at an epoch and the answer moves to authoring time.

    The records are NOT deleted -- they are the evidence that produced this diagnosis.
    They stop driving the verdict, which is a different thing, and the difference is what
    the historical summary line below exists to keep visible."""
    rl = load_module()
    check("the epoch is a named constant, not a literal buried in a branch",
          getattr(rl, "RECURRENCE_EPOCH", None) == "2026-08-20",
          getattr(rl, "RECURRENCE_EPOCH", None))

    pre = [_dated_record("2026-08-15-first", [_keyed("A-1", "deterministic", "old-key")]),
           _dated_record("2026-08-16-second", [_keyed("B-1", "deterministic", "old-key")])]
    lines = rl.recurrence_report(pre)
    check("PLANTED: two PRE-epoch findings on one key are no longer counted",
          not any("UNBUILT" in l for l in lines), lines)
    check("...but history is REPORTED, not silently dropped (silence reads as 'no history')",
          any(l.startswith("historical:") and "2" in l for l in lines), lines)
    check("...and the historical line points at where the records still live",
          any("docs/reviews" in l for l in lines if l.startswith("historical:")), lines)


def test_guard_answer_required_and_resolved_after_the_epoch():
    """The forward rule that makes the tracker self-resolving: a finding recorded on/after
    the epoch must answer WHAT WOULD HAVE CAUGHT THIS -- a hook, a test, or an explicit
    `none` with a reason. Asked of the AUTHOR while they still know, never of a reader
    months later. `none` is a first-class answer; the BLANK was what poisoned the list."""
    rl = load_module()
    check("the answer vocabulary has ONE machine owner",
          getattr(rl, "GUARD_KINDS", None) == ("hook", "test", "none"),
          getattr(rl, "GUARD_KINDS", None))

    def problems(record_id, guard):
        rec = _dated_record(record_id, [_guarded("A-1", "deterministic", "k", guard)])
        return rl.validate_record(rec, "t.json", lambda _s: True,
                                  plan_exists=lambda _p: True)

    check("PLANTED: a POST-epoch finding with no guard answer is REFUSED",
          any("guard" in p for p in problems("2026-08-20-x", None)),
          problems("2026-08-20-x", None))
    check("...and a PRE-epoch finding without one is untouched (the epoch IS the difference)",
          not any("guard" in p for p in problems("2026-08-19-x", None)),
          problems("2026-08-19-x", None))
    check("`none` is accepted when it carries a reason",
          not any("guard" in p for p in
                  problems("2026-08-20-x", {"kind": "none", "why": "needed a mind"})),
          problems("2026-08-20-x", {"kind": "none", "why": "needed a mind"}))
    check("PLANTED: bare `none` with no reason is REFUSED -- an unexplained 'nothing "
          "guards this' is the blank we just retired, wearing a label",
          any("guard" in p for p in problems("2026-08-20-x", {"kind": "none"})),
          problems("2026-08-20-x", {"kind": "none"}))
    check("PLANTED: an unknown kind is REFUSED",
          any("guard" in p for p in problems("2026-08-20-x", {"kind": "vibes"})))
    check("PLANTED: a hook ref naming no registered hook is REFUSED (loud, never a silent "
          "GUARDED)",
          any("guard" in p for p in
              problems("2026-08-20-x", {"kind": "hook", "ref": "no_such_guard"})),
          problems("2026-08-20-x", {"kind": "hook", "ref": "no_such_guard"}))
    check("a hook ref naming a REAL registered hook resolves",
          not any("guard" in p for p in
                  problems("2026-08-20-x", {"kind": "hook", "ref": "testweaken"})),
          problems("2026-08-20-x", {"kind": "hook", "ref": "testweaken"}))


def test_guard_state_is_computed_from_shipped_defaults():
    """The verdict, computed rather than curated -- and computed from the SHIPPED default,
    never from resolve_mode(). resolve_mode reads per-hook env vars, the global env var and
    break-glass state, and this inventory is rendered into a COMMITTED file whose test
    asserts committed == rendered. Keyed on resolve_mode, the same tree would render
    differently on two machines and fail the gate for whoever had a var set."""
    rl = load_module()

    def two(guard_a, guard_b):
        return [_dated_record("2026-08-20-first", [_guarded("A-1", "deterministic", "k", guard_a)]),
                _dated_record("2026-08-21-second", [_guarded("B-1", "deterministic", "k", guard_b)])]

    none_a = {"kind": "none", "why": "needed a mind"}
    lines = rl.recurrence_report(two(none_a, dict(none_a)))
    check("NEGATIVE CONTROL: two post-epoch findings that BOTH answer `none` still print "
          "UNBUILT -- a reset that merely silenced the report is the same defect, sign flipped",
          any("UNBUILT" in l and "k" in l for l in lines), lines)

    live = rl.recurrence_report(two({"kind": "hook", "ref": "testweaken"}, dict(none_a)))
    check("a member naming a LIVE hook -> GUARDED, never UNBUILT",
          any("GUARDED" in l for l in live) and not any("UNBUILT" in l for l in live), live)

    dark = rl.recurrence_report(two({"kind": "hook", "ref": "overmock"}, dict(none_a)))
    check("PLANTED: a hook that SHIPS OFF is GUARD DARK, not GUARDED -- file-existence "
          "would have called overmock_guard built while it ships off",
          any("GUARD DARK" in l for l in dark), dark)

    # purity: the committed inventory must be a pure function of the tree
    import os as _os
    saved = {k: _os.environ.get(k) for k in ("TDD_PLAYBOOK_HOOK_OVERMOCK",
                                             "TDD_PLAYBOOK_HOOK_MODE")}
    try:
        _os.environ["TDD_PLAYBOOK_HOOK_OVERMOCK"] = "block"
        _os.environ["TDD_PLAYBOOK_HOOK_MODE"] = "block"
        again = rl.recurrence_report(two({"kind": "hook", "ref": "overmock"}, dict(none_a)))
        check("PURITY: an env override does NOT change the report (a generated artifact is "
              "a pure function of the tree)", again == dark, (dark, again))
    finally:
        for key, value in saved.items():
            if value is None:
                _os.environ.pop(key, None)
            else:
                _os.environ[key] = value


if __name__ == "__main__":
    test_unresolved_blocker_refused()
    test_false_closure_and_scope_refused()
    test_terminal_closure_evidence_and_range_are_executable()
    test_directory_consumes_records_and_rejects_duplicate_ids()
    test_append_only_index_refuses_deleted_record()
    test_repository_review_records_are_valid()
    test_records_are_optional_evidence_not_a_per_commit_toll()
    test_taxonomy_required_after_ship_date()
    test_reviewer_vocabulary_bound_to_roster()
    test_participation_report()
    test_small_change_lane_cannot_be_talked_into()
    test_small_lane_still_demands_verification_and_the_right_adversaries()
    test_recurrence_report()
    test_recurrence_verb_vacuity_and_usage_event()
    test_root_resolution_vendored_and_canonical()
    test_recurrence_epoch_retires_the_old_list()
    test_guard_answer_required_and_resolved_after_the_epoch()
    test_guard_state_is_computed_from_shipped_defaults()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
