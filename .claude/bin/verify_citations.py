#!/usr/bin/env python3
"""verify_citations — the mechanical half of the §12 claims discipline.

`/claims` doctrine says "no claim before resolving evidence" and "a self-reported N/N is
narration with a colon in it." This tool makes the evidence check ACTUAL CODE: given a
findings document, it resolves every `file:line` citation against the real source and (when
the finding quotes the line) checks the quote actually matches. Findings whose citation is
UNRESOLVED or MISMATCH must be demoted to leads — they cannot carry a severity.

It is language-agnostic and standalone (no dependency on any host repo). It is a fresh
implementation of the citation-checking idea, not an import of any repo's private tooling.

CITATION FORMAT it recognizes in the findings doc:
    path/to/file.ext:LINE                      → resolve file + line exists
    path/to/file.ext:START-END                 → resolve file + range in bounds
    path/to/file.ext:LINE:COL                  → COL ignored for resolution
  Optionally followed (same line) by a quoted snippet to verify against that line:
    ... `src/auth.py:42`: "return False"       → also check the quote is on line 42
    ... src/auth.py:42 — "return False"        → same
  Quote match is whitespace-normalized substring (the finding may quote part of the line).

USAGE:
    verify_citations.py FINDINGS.md [--base DIR] [--quiet]
    cat FINDINGS.md | verify_citations.py - [--base DIR]
Exit 0 = every citation VERIFIED (or none present). Exit 1 = any UNRESOLVED / MISMATCH.
Exit 2 = bad invocation.
"""
import argparse
import os
import re
import sys

# path must contain a dot-extension so prose like "step 3:1" doesn't masquerade as a citation
_CITE = re.compile(
    r"(?P<path>[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+):(?P<start>\d+)(?:-(?P<end>\d+))?(?::\d+)?"
)
# a quote appearing shortly after the citation (straight or smart quotes); skip any closing
# markdown backtick + separators (`, :, -, —, –) between the cite and the quote
_QUOTE_AFTER = re.compile(r'^[\s:\-—–`]*["“‘](?P<q>[^"”’]+)["”’]')


# ABSENCE CLAIMS (2026-08-18). §12 demands MORE evidence for a negative than a positive —
# "never called / unreachable" needs an exhaustive sweep — but until now a negative cited
# NOTHING, so this tool had nothing to resolve and could not see the claim at all. Doctrine
# strictest, mechanism absent. The live incident that closed the gap: "MemStruct has no
# capability registry", asserted from unrelated missing tooling, never checked; it has ten.
#
# `(absent: <path>)` makes the negative citable. The tool RE-RUNS the check and REFUTES the
# finding if the path is there — the inverse of what it already does for presence, at the
# same seam. A directory counts as present: "no docs/reviews/" is the same claim shape.
_ABSENT = re.compile(r"\(\s*absent:\s*(?P<path>[^)\n]+?)\s*\)", re.I)


def find_absence_claims(text):
    for m in _ABSENT.finditer(text or ""):
        yield {"path": m.group("path").strip().strip("`"), "raw": m.group(0)}


def check_absence(claim, base):
    """VERIFIED when the path is genuinely absent; REFUTED when it is right there."""
    target = os.path.join(base, claim["path"])
    if os.path.exists(target):
        kind = "directory" if os.path.isdir(target) else "file"
        return "REFUTED", "the {} EXISTS at {} — the claim of absence is disproven".format(
            kind, claim["path"])
    return "VERIFIED", ""


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def find_citations(text):
    """Yield dicts {path,start,end,quote,raw} for each citation in the doc."""
    for m in _CITE.finditer(text):
        start = int(m.group("start"))
        end = int(m.group("end")) if m.group("end") else start
        tail = text[m.end():m.end() + 200]
        qm = _QUOTE_AFTER.match(tail)
        yield {
            "path": m.group("path"),
            "start": start,
            "end": end,
            "quote": qm.group("q") if qm else None,
            "raw": m.group(0),
        }


def check(cite, base):
    """Return (status, detail): status in VERIFIED / UNRESOLVED / MISMATCH."""
    fpath = cite["path"] if os.path.isabs(cite["path"]) else os.path.join(base, cite["path"])
    if not os.path.isfile(fpath):
        return "UNRESOLVED", "no such file"
    try:
        with open(fpath, "r", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        return "UNRESOLVED", "unreadable ({})".format(e)
    if cite["start"] < 1 or cite["end"] > len(lines) or cite["start"] > cite["end"]:
        return "UNRESOLVED", "line out of range (file has {} lines)".format(len(lines))
    if cite["quote"]:
        q = _norm(cite["quote"])
        span = _norm("\n".join(lines[cite["start"] - 1:cite["end"]]))
        if q not in span:
            return "MISMATCH", 'quoted text not on cited line(s)'
        # quality notes (do not flip the gate, but a weak quote is weak evidence):
        notes = []
        if len(q) < 10:
            notes.append("weak quote (<10 chars — a fragment this short proves little; "
                         "cite a longer span)")
        else:
            hits = sum(1 for ln in lines if q in _norm(ln))
            if hits > 1:
                notes.append("weak quote (matches {} lines in the file — not uniquely "
                             "identifying)".format(hits))
        return "VERIFIED", "; ".join(notes)
    return "VERIFIED", ""


def run(text, base, quiet=False):
    cites = list(find_citations(text))
    absences = list(find_absence_claims(text))
    absent_bad = []
    for a in absences:
        status, detail = check_absence(a, base)
        if status == "REFUTED":
            absent_bad.append((a, detail))
        if not quiet:
            mark = "✓" if status == "VERIFIED" else "✗"
            sys.stdout.write("  {} {}{}\n".format(
                mark, a["raw"], (" — " + detail) if detail else ""))
    counts = {"VERIFIED": 0, "UNRESOLVED": 0, "MISMATCH": 0}
    bad, weak = [], 0
    for c in cites:
        status, detail = check(c, base)
        counts[status] += 1
        if status != "VERIFIED":
            bad.append((c, status, detail))
        elif "weak quote" in detail:
            weak += 1
        if not quiet:
            mark = {"VERIFIED": "✓", "UNRESOLVED": "✗", "MISMATCH": "≠"}[status]
            line = "  {} {}{}".format(mark, c["raw"], (" — " + detail) if detail else "")
            sys.stdout.write(line + "\n")
    if absences:
        sys.stdout.write("Absence claims: {} · verified {} · REFUTED {}\n".format(
            len(absences), len(absences) - len(absent_bad), len(absent_bad)))
        if absent_bad:
            sys.stdout.write(
                "DEMOTE these findings to leads (absence DISPROVEN — the thing is there): "
                + ", ".join(a["path"] for a, _d in absent_bad) + "\n")
    if not cites:
        if not absences:
            sys.stdout.write("Citations: 0 — no `file:line` citations found to verify.\n")
        return 1 if absent_bad else 0
    sys.stdout.write(
        "Citations: {} · verified {} · unresolved {} · mismatch {}{}\n".format(
            len(cites), counts["VERIFIED"], counts["UNRESOLVED"], counts["MISMATCH"],
            " · weak-quote {}".format(weak) if weak else "")
    )
    if bad:
        sys.stdout.write(
            "DEMOTE these findings to leads (citation not proven): "
            + ", ".join(c["raw"] for c, _s, _d in bad) + "\n"
        )
    return 1 if (bad or absent_bad) else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Verify file:line citations in a findings doc.")
    ap.add_argument("findings", help="path to findings doc, or - for stdin")
    ap.add_argument("--base", default=os.getcwd(), help="base dir for relative paths (default: cwd)")
    ap.add_argument("--quiet", action="store_true", help="summary only")
    args = ap.parse_args(argv)
    if args.findings == "-":
        text = sys.stdin.read()
    else:
        if not os.path.isfile(args.findings):
            sys.stderr.write("verify_citations: no such findings file: {}\n".format(args.findings))
            return 2
        with open(args.findings, "r", errors="replace") as fh:
            text = fh.read()
    return run(text, args.base, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
