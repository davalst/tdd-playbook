#!/usr/bin/env python3
"""PreToolUse(Bash) — a release TAG is the owner's signature, not an agent action (v1.32.0).

v1.32.0 deleted the CIVerd signed-verdict release wall. The security argument for deleting
rather than shrinking it is that with no verdict in the release path there is nothing to
forge — and what authorizes a release becomes David creating the tag. That argument only
holds while the model cannot create one.

`test_installer.py::test_no_script_creates_a_release_tag` covers committed SCRIPTS and CI
workflows. It cannot cover the way tags are actually cut in this repo: a session typing

    git tag -s v1.32.0 && git push origin v1.32.0

into a single Bash call. No file scan can ever observe that — the population it inspects
(tracked .py/.sh/.yml) is disjoint from the population that cuts tags. Two fresh-context
adversaries found this independently on the v1.32.0 diff, and both named the same fix: this
repo already owns the action-time seam (test_lock_guard, snapshot_guard, exitcode_guard all
match PreToolUse/Bash), and a sibling guard belongs there. `git for-each-ref` confirms the
concern is not hypothetical — v1.29.0/v1.30.0/v1.31.0 were all created through ordinary
Bash on 2026-08-09, and no artifact distinguishes David's `git tag` from the model's.

BLOCKING, and deliberately so. This is the one gate whose whole purpose is to reserve an
action for the human; a warning that can be read past reserves nothing. It is also the only
half of the story that ships: hooks/scripts/ is vendored by install_into_repo.py's
COPY_TREES, so every downstream repo inherits it, whereas tests/ is not vendored.

Escape hatch, by design: David is not blocked, because David is not the one running through
this hook. If a session genuinely must tag (a backfill, a repair), the sanctioned exit is
TDD_PLAYBOOK_HOOK_TAGGUARD=warn for that command with the reason stated — the same demotion
contract every other guard here has, recorded by _common.emit as a `suppressed` event so a
muzzled gate stays distinguishable from a quiet one.

WHAT THIS DOES NOT CLAIM. It binds the agent's Bash tool. It cannot bind a human at a
terminal, and it cannot bind an actor who edits the hook — a repo-side check never can.
The binding control for those is a GitHub `v*` ruleset restricting tag creation to davalst,
tracked as dated debt on the `release-tag-authority` capability until armed. Stating the
limit is the point; a guard that overclaims is worse than one that is merely narrow.

CALIBRATED IN BOTH DIRECTIONS (the house bar, §13): it must BLOCK creation/push of a tag
AND stay silent on every read-only tag use — `git describe --tags`, `git tag -l`,
`git tag -d` on a local scratch tag, `git ls-remote --tags`, ordinary branch pushes. Both
halves are pinned in tests/test_hooks.py::test_tag_guard.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit  # noqa: E402

NAME = "tagguard"

# `git [-C path] [-c k=v] tag ...` — the SUBCOMMAND position. Anchoring here rather than
# "git ... tag loose on a line" is what keeps prose and --help text out: the sibling scanner
# in test_installer.py matched check_scoreboard_integrity's own help string ("git rev of the
# trusted baseline ... the previous release tag") before it was anchored this way.
_GIT = r"\bgit\b(?:\s+-[A-Za-z-]+(?:[= ]\S+)?)*\s+"
# Reading tags is free. Deleting a local tag is allowed: it cannot mint a release, and
# refusing it would block ordinary test cleanup.
_TAG_READ_OR_DELETE = re.compile(
    _GIT + r"tag\b\s*(?:-l\b|--list\b|-d\b|--delete\b|-n\d*\b|-v\b|--verify\b|--contains\b|$)")
_TAG_CREATE = re.compile(_GIT + r"tag\b")
_TAG_REF_WRITE = re.compile(_GIT + r"update-ref\b[^\n]*refs/tags")
# pushing tags: --tags, an explicit refs/tags refspec, or a bare vN.N.N argument
_TAG_PUSH = re.compile(_GIT + r"push\b[^\n]*(?:--tags\b|refs/tags|\sv\d+\.\d+)")
# the GitHub CLI reaches the same fact by another road
_GH_RELEASE = re.compile(r"\bgh\b[^\n]*\brelease\s+create\b|\bgh\b[^\n]*\bapi\b[^\n]*refs/tags")


def _statements(cmd):
    """Split on statement separators so `a && git tag v1` is inspected as two statements."""
    return [s for s in re.split(r";|&&|\|\||\n|\|", cmd) if s.strip()]


# A statement that merely PRINTS text cannot create a tag. Without this, `echo "David runs
# git tag -s to release"` blocks — the ALLOW-direction false positive this guard's own
# calibration table caught on its first run, and the same family as TEST-LOCK's documented
# "reads are always fine" bypass. Prose is not an action, at the shell as much as in an AST.
_PRINTS_ONLY = re.compile(r"^\s*(?:echo|printf|:|#)\b")


def findings(cmd):
    if not cmd:
        return []
    out = []
    for stmt in _statements(cmd):
        if _PRINTS_ONLY.match(stmt) or _TAG_READ_OR_DELETE.search(stmt):
            continue
        if _TAG_CREATE.search(stmt):
            out.append("creating a release tag is the OWNER's action, not the agent's: "
                       + stmt.strip()[:100])
        elif _TAG_REF_WRITE.search(stmt):
            out.append("writing refs/tags/* creates a tag by another name: "
                       + stmt.strip()[:100])
        elif _TAG_PUSH.search(stmt):
            out.append("pushing a tag publishes a release: " + stmt.strip()[:100])
        elif _GH_RELEASE.search(stmt):
            out.append("`gh release create` creates a tag: " + stmt.strip()[:100])
    return out


def main():
    event = read_event()
    if (event.get("tool_name") or "") != "Bash":
        return 0
    cmd = (event.get("tool_input") or {}).get("command") or ""
    hits = findings(cmd)
    if not hits:
        return 0
    lines = list(hits) + [
        "v1.32.0 retired the CIVerd release wall; what authorizes a release is DAVID "
        "creating the tag. Report the gate result and the version bump, then ASK HIM to "
        "run: git tag -a vX.Y.Z && git push origin vX.Y.Z",
        "if this is genuinely his instruction, say so and re-run with "
        "TDD_PLAYBOOK_HOOK_TAGGUARD=warn — do NOT split the command to get it through",
    ]
    return emit(NAME, lines)


if __name__ == "__main__":
    sys.exit(main())
