#!/usr/bin/env python3
"""Planted contracts for generated, provenance-bound current-state documentation."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
SCRIPT = os.path.join(PLUGIN, "bin", "render_reference.py")
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
    spec = importlib.util.spec_from_file_location("render_reference", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_reference_is_current():
    rr = load_module()
    rendered = rr.render(REPO)
    target = os.path.join(REPO, "docs", "reference", "current-state.md")
    with open(target, encoding="utf-8") as fh:
        check("committed reference equals deterministic render", fh.read() == rendered)
    check("reference identifies itself as generated", "DO NOT EDIT" in rendered)
    check("reference names the full gate as authorizing",
          "sh scripts/civerd_gate.sh" in rendered and "AUTHORIZING" in rendered)
    check("reference marks affected execution non-authorizing",
          "affected --base" in rendered and "NON-AUTHORIZING" in rendered)


def test_provenance_hashes_cover_authorities():
    rr = load_module()
    rendered = rr.render(REPO)
    for path in rr.provenance_inputs(REPO):
        check("provenance includes hash for {}".format(path),
              "`{}` — `{}`".format(path, rr.file_hash(REPO, path)) in rendered)


def test_stale_or_manually_edited_output_is_refused():
    rr = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        for rel in rr.provenance_inputs(REPO):
            src = os.path.join(REPO, rel)
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        target = os.path.join(tmp, "docs", "reference", "current-state.md")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(rr.render(tmp))
        check("fresh generated output passes", rr.check(tmp) == [])
        with open(os.path.join(tmp, "capabilities.json"), "a", encoding="utf-8") as fh:
            fh.write("\n")
        check("PLANTED authority drift is refused", rr.check(tmp))
        with open(target, "a", encoding="utf-8") as fh:
            fh.write("manual current-state claim\n")
        check("PLANTED manual generated-doc edit is refused", rr.check(tmp))


def test_debt_lines_carry_the_required_what_not_a_fabricated_name():
    """H1 (v1.33.1): the renderer keyed debt lines on the OPTIONAL `id` field (present on
    4 of 55 entries) and printed `unnamed` for the rest — a label fabricated from a field
    no validator owns, while the REQUIRED `what` (_debt.py DEBT_FIELDS) went unrendered.
    The reader of current-state.md is the one person who cannot fall back to source, so
    51 anonymous debt rows were 51 facts the instrument held and refused to say.

    Contract pinned here:
      - a debt WITHOUT `id` renders its `what` first clause — never `unnamed`;
      - a debt WITH `id` keeps the `cap/id` join key (host-parity-policy.json cites three
        of those keys by value) AND gains the `what` clause — fixing the label must not
        discard the reference;
      - shortening is VISIBLE (an ellipsis), never silent (§12).
    """
    rr = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        for rel in rr.provenance_inputs(REPO):
            src = os.path.join(REPO, rel)
            dst = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        reg_path = os.path.join(tmp, "capabilities.json")
        with open(reg_path, encoding="utf-8") as fh:
            registry = json.load(fh)
        # PLANT: one capability, two debts — one id-less (the 51-row shape), one carrying
        # an id (the join-key shape host-parity-policy.json depends on).
        registry["capabilities"].append({
            "id": "h1-planted-cap",
            "summary": "planted for the H1 debt-naming contract",
            "user_facing": False,
            "surfaces": ["local"],
            "activation": {"default": "on"},
            "wired_by": ["plugins/tdd-playbook/tests/test_reference_docs.py"],
            "exercised_by": ["plugins/tdd-playbook/tests/test_reference_docs.py"],
            "integration_debt": [
                {"what": "H1PLANT NO-ID CLAUSE: the tail past the first clause boundary "
                         "must not render",
                 "owner": "david", "expires": "2099-01-01"},
                {"id": "h1-planted-key",
                 "what": "H1PLANT KEYED CLAUSE: id and what must both survive",
                 "owner": "david", "expires": "2099-01-01"},
            ],
        })
        with open(reg_path, "w", encoding="utf-8") as fh:
            json.dump(registry, fh)
        rendered = rr.render(tmp)
        planted = [l for l in rendered.splitlines() if "h1-planted-cap" in l]
        check("planted id-less debt renders its `what` clause, not `unnamed`",
              any("H1PLANT NO-ID CLAUSE" in l and "unnamed" not in l for l in planted),
              planted)
        check("planted id-less clause cut is visible (ellipsis), tail not rendered",
              any("H1PLANT NO-ID CLAUSE…" in l for l in planted)
              and not any("must not render" in l for l in planted), planted)
        # CONTROL: the keyed debt keeps its cross-file join key AND gains the clause.
        check("planted keyed debt keeps the `cap/id` join key and gains the clause",
              any("`h1-planted-cap/h1-planted-key`" in l
                  and "H1PLANT KEYED CLAUSE" in l for l in planted), planted)
        check("no debt line anywhere fabricates `unnamed`", "unnamed" not in rendered,
              [l for l in rendered.splitlines() if "unnamed" in l][:3])


def test_review_summary_is_generated_from_consumed_records():
    rr = load_module()
    rendered = rr.render(REPO)
    check("generated reference reports review packet and finding counts",
          "Review records:" in rendered and "Findings:" in rendered)
    check("review JSON participates in provenance",
          "`docs/reviews/" in rendered)


def test_agents_md_is_generated_and_current():
    """AGENTS.md is the Codex agent-instructions convention and this repo READS it
    (gate-manifest.json, hooks/scripts/intent_nudge.py). It was hand-maintained as a mirror
    of CLAUDE.md and rotted the way hand-maintained mirrors do: on 2026-08-10 it still carried
    the PRE-v1.32.0 calibration section — "calibration is not optional", the 14-day clock, the
    staleness release gate — every word of which had been reversed days earlier. A Codex
    session following it would have done the OPPOSITE of current doctrine, and nothing said so.

    Generated by CONCATENATION, not substitution: the previous mirror came from a
    Claude->Codex find-replace that produced `.Codex/settings.json` (Codex uses lowercase) and
    "a real Codex binary" where calibration needs the CLAUDE cli on every host. A prose
    transform cannot tell a host name from a product name, and it fails silently."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "render_agents", os.path.join(REPO, "plugins", "tdd-playbook", "bin", "render_agents.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    want = mod.render()
    with open(os.path.join(REPO, "AGENTS.md")) as fh:
        have = fh.read()
    check("AGENTS.md equals CLAUDE.md + HOST_NOTES (byte-exact)", have == want,
          "len have={} want={}".format(len(have), len(want)))
    check("AGENTS.md carries the generated banner so a reader knows not to edit it",
          have.startswith("<!-- GENERATED FILE"), have[:60])

    with open(os.path.join(REPO, "CLAUDE.md")) as fh:
        doctrine = fh.read()
    moved = "CALIBRATION — OPT-IN AND REACTIVE"
    check("a RECENTLY CHANGED doctrine line reaches AGENTS.md (the drift that bit)",
          moved in doctrine and moved in have, moved)

    tampered = have.replace("## What differs on Codex",
                            "## What differs on Codex (edited by hand)")
    check("PLANTED hand edit to AGENTS.md is detected", tampered != want)
    check("PLANTED: no `.Codex/` uppercase path is produced",
          ".Codex/" not in want, [l for l in want.splitlines() if ".Codex/" in l][:2])
    check("the CLAUDE cli reference SURVIVES (the substitution bug that broke the mirror)",
          "real `claude` binary" in want)
    for needle in (".codex/tdd-playbook/", "--host codex", "unavailable", "tag_guard"):
        check("host note present: " + needle, needle in want)


if __name__ == "__main__":
    # The real committed output does not exist in the red-first commit. The blessed gate
    # must therefore execute this suite and refuse before implementation can round up.
    test_generated_reference_is_current()
    test_agents_md_is_generated_and_current()
    test_provenance_hashes_cover_authorities()
    test_stale_or_manually_edited_output_is_refused()
    test_debt_lines_carry_the_required_what_not_a_fabricated_name()
    test_review_summary_is_generated_from_consumed_records()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
