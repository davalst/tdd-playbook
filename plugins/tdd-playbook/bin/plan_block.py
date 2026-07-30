#!/usr/bin/env python3
"""plan_block — the author-side of the CIVerd plan-predicate seam (briefs D1).

Plans land IN the repo they govern (`docs/plans/gated/<slug>.md`) carrying exactly one
```civerd-plan``` block that the CIVerd engine parses deterministically and FAILS CLOSED.
The consumer defines the format (civerd/docs/PLAN_PREDICATE_CONTRACT.md); this tool
conforms and REFUSES in the author's hands anything the engine would red — better here
than an unexplained release refusal (the anti-normalizePatternType rule). Local rules may
drift from the engine only in the STRICT direction: we may reject what the engine accepts,
never accept what it rejects (pinned by the engine-blessed conformance corpus in
tests/fixtures/plan_block_corpus.json).

What the four predicate types ACTUALLY prove (the weaker truth — write plans against
this, not the stronger reading):
  test_passes path::name  -> the function EXISTS at the judged sha, is not skip/xfail
                             marked, and every required gate check exited 0. NOT "the
                             engine watched it run."
  symbol_referenced name  -> referenced (load/attr/import, never its own def) from >=1
                             file outside the test globs. Weak both ways: false-negative
                             on config/string wiring, false-positive in dead code. For
                             config-wired deliverables use file_exists on the config +
                             test_passes on a wiring test.
  suite_min n             -> AST-counted test FUNCTIONS under the test globs >= n.
                             Near-useless in check()-style repos like this one.
  file_exists path        -> non-symlink regular file at the judged sha.

Status is ALWAYS `active` at authoring. `satisfied` is cosmetic to the engine;
`abandoned` is David's word alone, through the root-owned store on the box — there is
deliberately NO argument path here that can emit either. Slugs are permanent
(abandonment keys on the slug hash forever): namespace by date/workstream. Research and
documentation deliverables are NOT predicates — list them in the plan's
"Unenforceable deliverables (prose)" section, never fake them with a weak file_exists.

    plan_block.py scaffold --slug 2026-07-30-thing --repo tdd-playbook \
        --predicate test_passes:tests/test_x.py::test_y [--predicate ...]
    plan_block.py validate docs/plans/gated/2026-07-30-thing.md

`validate` also shells to `civerd plan-check` when on PATH (the engine's own code path —
the author convenience the contract names); it is never the authority — the signed
verdict from the box is. Stdlib-only by repo invariant.
"""
import argparse
import datetime
import os
import posixpath
import re
import shutil
import subprocess
import sys

GATED = os.path.join("docs", "plans", "gated")
TYPES = ("test_passes", "symbol_referenced", "suite_min", "file_exists")
# Engine-exact argument grammar (from the engine; the contract is being amended to state
# these — conformance must never require internals again):
MAX_PREDICATES = 64
MAX_CHECK_NAME = 64          # "plan." + slug must fit
CHECK_PREFIX = "plan."
SLUG_RX = re.compile(r"^[A-Za-z0-9._-]+$")
IDENT_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RELPATH_RX = re.compile(r"^[A-Za-z0-9._/-]{1,255}$")
SUITEMIN_RX = re.compile(r"^\d{1,9}$")
NODEID_RX = re.compile(r"^[A-Za-z0-9._/-]{1,255}::[A-Za-z_][A-Za-z0-9_]*$")
FENCE_RX = re.compile(r"^```civerd-plan\s*$")


def _relpath_problem(value, what):
    """Mirror the engine's _safe_relpath exactly: charset cap, no absolute paths, no `..`
    component (rejected outright, never normalised). Found live: the first blessed corpus
    run turned 4 cases red because our charset regex alone accepted /etc/passwd and
    ../escapes the engine refuses — the unsafe-drift direction, in the first hour."""
    if not RELPATH_RX.match(value) or value.startswith("/"):
        return ("{} needs a repo-relative path matching [A-Za-z0-9._/-]{{1,255}}, not "
                "absolute (got {!r})".format(what, value))
    if ".." in posixpath.normpath(value).split("/") or ".." in value.split("/"):
        return "{} path escapes the repo (got {!r})".format(what, value)
    return None


def predicate_problem(ptype, arg):
    if ptype not in TYPES:
        return ("unknown predicate type '{}' — the grammar is closed ({}); a locally "
                "invented type produces an engine RED, not a feature".format(
                    ptype, ", ".join(TYPES)))
    if ptype == "test_passes":
        if not NODEID_RX.match(arg):
            return "test_passes needs <path>::<test_name> (got {!r})".format(arg)
        return _relpath_problem(arg.split("::", 1)[0], "test_passes")
    if ptype == "symbol_referenced" and not IDENT_RX.match(arg):
        return "symbol_referenced needs a Python identifier (got {!r})".format(arg)
    if ptype == "file_exists":
        return _relpath_problem(arg, "file_exists")
    if ptype == "suite_min" and not SUITEMIN_RX.match(arg):
        return "suite_min needs an integer of 1-9 digits (got {!r})".format(arg)
    return None


def slug_problem(slug):
    if not SLUG_RX.match(slug or ""):
        return "slug must match [A-Za-z0-9._-]+ (got {!r})".format(slug)
    if len(CHECK_PREFIX) + len(slug) > MAX_CHECK_NAME:
        return ("'{}{}' exceeds the engine's {}-char check-name cap (slug max {} chars)"
                .format(CHECK_PREFIX, slug, MAX_CHECK_NAME,
                        MAX_CHECK_NAME - len(CHECK_PREFIX)))
    return None


def build_block(repo, predicates):
    lines = ["```civerd-plan", "version: 1", "repo: {}".format(repo), "status: active",
             "predicates:"]
    for ptype, arg in predicates:
        lines.append("  - {}: {}".format(ptype, arg))
    lines.append("```")
    return "\n".join(lines)


def parse_block(text):
    """(block_text, parsed) or raises ValueError — strict, closed, fail-closed."""
    lines = text.splitlines()
    fences = [i for i, ln in enumerate(lines) if FENCE_RX.match(ln)]
    if len(fences) != 1:
        raise ValueError("expected exactly one ```civerd-plan fence, found {}".format(
            len(fences)))
    start = fences[0]
    try:
        end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "```")
    except StopIteration:
        raise ValueError("civerd-plan fence never closed")
    body = lines[start + 1:end]
    parsed = {"predicates": []}
    in_preds = False
    for ln in body:
        if not ln.strip():
            raise ValueError("blank line inside the block")
        if ln.startswith("  - "):
            if not in_preds:
                raise ValueError("predicate list before 'predicates:' key")
            item = ln[4:]
            if ": " not in item:
                raise ValueError("malformed predicate line: {!r}".format(ln))
            ptype, arg = item.split(": ", 1)
            prob = predicate_problem(ptype.strip(), arg.strip())
            if prob:
                raise ValueError(prob)
            parsed["predicates"].append((ptype.strip(), arg.strip()))
            continue
        if ": " not in ln and not ln.endswith(":"):
            raise ValueError("malformed line: {!r}".format(ln))
        if ln.strip() == "predicates:":
            in_preds = True
            continue
        key, val = ln.split(":", 1)
        key, val = key.strip(), val.strip()
        if key not in ("version", "repo", "status"):
            raise ValueError("unknown field {!r} — the field set is closed".format(key))
        parsed[key] = val
    if parsed.get("version") != "1":
        raise ValueError("version must be 1 (never 'assume latest')")
    if not parsed.get("repo"):
        raise ValueError("repo is required")
    if parsed.get("status") not in ("active", "satisfied", "abandoned"):
        raise ValueError("status must be active|satisfied|abandoned")
    if not parsed["predicates"]:
        raise ValueError("empty predicate list — a plan that promises nothing is not a plan")
    if len(parsed["predicates"]) > MAX_PREDICATES:
        raise ValueError("{} predicates exceeds the engine cap of {}".format(
            len(parsed["predicates"]), MAX_PREDICATES))
    block = "\n".join(lines[start:end + 1])
    return block, parsed


SKELETON = """# Plan — {slug}

Authored {date} via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

<assumptions, alternative readings, the simpler-approach check — per Playbook §0>

## Deliverables

<per-deliverable behavior, edge cases, integration surface — the prose humans review>

## Unenforceable deliverables (prose)

<research, documentation, decision write-ups — NOT predicates; never faked with a weak
file_exists. This section exists so they are listed, not laundered.>

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

{block}
"""


def cmd_scaffold(args):
    prob = slug_problem(args.slug)
    if prob:
        sys.stderr.write("plan_block: REFUSED — {}\n".format(prob))
        return 1
    if not args.predicate:
        sys.stderr.write("plan_block: REFUSED — empty predicate list: a plan that "
                         "promises nothing is not a plan. Research/docs deliverables "
                         "belong in the prose section, not as fake predicates.\n")
        return 1
    if len(args.predicate) > MAX_PREDICATES:
        sys.stderr.write("plan_block: REFUSED — {} predicates exceeds the engine cap of "
                         "{}\n".format(len(args.predicate), MAX_PREDICATES))
        return 1
    predicates = []
    for raw in args.predicate:
        if ":" not in raw:
            sys.stderr.write("plan_block: REFUSED — predicate needs TYPE:ARG "
                             "(got {!r})\n".format(raw))
            return 1
        ptype, arg = raw.split(":", 1)
        prob = predicate_problem(ptype, arg)
        if prob:
            sys.stderr.write("plan_block: REFUSED — {}\n".format(prob))
            return 1
        predicates.append((ptype, arg))
    path = os.path.join(GATED, args.slug + ".md")
    if os.path.exists(path):
        sys.stderr.write("plan_block: REFUSED — slug collides with existing {} (slugs "
                         "are permanent; pick a new one)\n".format(path))
        return 1
    os.makedirs(GATED, exist_ok=True)
    block = build_block(args.repo, predicates)
    with open(path, "w") as fh:
        fh.write(SKELETON.format(slug=args.slug,
                                 date=datetime.date.today().isoformat(), block=block))
    # self-check: what we wrote must round-trip through our own strict parser
    reparsed_block, _ = parse_block(open(path).read())
    if reparsed_block != block:
        sys.stderr.write("plan_block: INTERNAL — emitted block failed round-trip\n")
        return 1
    print("plan_block: wrote {} (status: active; validate before committing)".format(path))
    return 0


def cmd_validate(args):
    try:
        text = open(args.file).read()
    except OSError as e:
        sys.stderr.write("plan_block: cannot read {}: {}\n".format(args.file, e))
        return 1
    try:
        block, parsed = parse_block(text)
    except ValueError as e:
        sys.stderr.write("plan_block: INVALID — {}\n".format(e))
        return 1
    re_emitted = build_block(parsed["repo"], parsed["predicates"])
    if parsed.get("status") == "active" and re_emitted != block:
        sys.stderr.write("plan_block: INVALID — block does not round-trip byte-identical "
                         "(non-canonical formatting)\n")
        return 1
    print("plan_block: {} OK — {} predicate(s), repo {}, status {} "
          "(author convenience — the signed verdict from the box is the authority)".format(
              args.file, len(parsed["predicates"]), parsed["repo"], parsed["status"]))
    if shutil.which("civerd"):
        p = subprocess.run(["civerd", "plan-check", args.file, "--repo", parsed["repo"]],
                           capture_output=True, text=True, timeout=60)
        print("civerd plan-check: exit {}\n{}".format(p.returncode,
                                                      (p.stdout + p.stderr).strip()))
        return p.returncode
    print("civerd plan-check: engine parser unavailable on PATH — shape pre-check only")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold", help="write docs/plans/gated/<slug>.md")
    sc.add_argument("--slug", required=True)
    sc.add_argument("--repo", required=True,
                    help="the ENGINE'S name for this repo (repos.yml) — required because "
                         "any local guess (a worktree dirname doubly so) is a proxy")
    sc.add_argument("--predicate", action="append", default=[],
                    metavar="TYPE:ARG")
    va = sub.add_parser("validate", help="strict author-side check + engine plan-check "
                                         "when available")
    va.add_argument("file")
    args = ap.parse_args(argv)
    return cmd_scaffold(args) if args.cmd == "scaffold" else cmd_validate(args)


if __name__ == "__main__":
    sys.exit(main())
