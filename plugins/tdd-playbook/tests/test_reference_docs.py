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


def test_review_summary_is_generated_from_consumed_records():
    rr = load_module()
    rendered = rr.render(REPO)
    check("generated reference reports review packet and finding counts",
          "Review records:" in rendered and "Findings:" in rendered)
    check("review JSON participates in provenance",
          "`docs/reviews/" in rendered)


if __name__ == "__main__":
    # The real committed output does not exist in the red-first commit. The blessed gate
    # must therefore execute this suite and refuse before implementation can round up.
    test_generated_reference_is_current()
    test_provenance_hashes_cover_authorities()
    test_stale_or_manually_edited_output_is_refused()
    test_review_summary_is_generated_from_consumed_records()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
