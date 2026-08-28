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
repo already owns the action-time seam (lock_guard, snapshot_guard, exitcode_guard all
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
    _GIT + r"tag\b\s*(?:-l\b|--list\b|-d\b|--delete\b|-n\d*\b|-v\b|--verify\b|--contains\b"
    #                    a bare listing may be REDIRECTED and stay a listing. The alternation
    #                    used to end at `$`, so anything following a bare listing stopped
    #                    matching "read" and fell through to "create" — measured live
    #                    (Cheliped, 2026-08-27): this guard fired three times in one session
    #                    on listings and never once on a real attempt. Fails safe, but a
    #                    guard that cries wolf is a guard that gets demoted.
    r"|[0-9]*[<>]|$)")
_TAG_CREATE = re.compile(_GIT + r"tag\b")
_TAG_REF_WRITE = re.compile(_GIT + r"update-ref\b[^\n]*refs/tags")
# pushing tags: --tags, an explicit refs/tags refspec, or a bare vN.N.N argument
_TAG_PUSH = re.compile(_GIT + r"push\b[^\n]*(?:--tags\b|refs/tags|\sv\d+\.\d+)")
# the GitHub CLI reaches the same fact by another road
_GH_RELEASE = re.compile(r"\bgh\b[^\n]*\brelease\s+create\b|\bgh\b[^\n]*\bapi\b[^\n]*refs/tags")

# CI reaches it by a third road that contains no git verb at all. A workflow step like
#   - uses: softprops/action-gh-release@<sha>
#     with: {tag_name: v9.9.9}
# creates and pushes a release tag with zero `git tag` text, so every shell-verb rule above
# is blind to it. These are exported for the workflow scanner in test_installer.py, which
# imports THIS module rather than keeping a second copy of the policy (the two lists had
# already drifted: --verify/--contains were read-only here and flagged there).
_WORKFLOW_TAG_ACTIONS = re.compile(
    r"uses:\s*\S*(?:action-gh-release|create-release|create-tag|tag-action|release-action"
    r"|github-tag|semantic-release|release-please|changesets/action)", re.I)
_WORKFLOW_TAG_INPUTS = re.compile(r"^\s*(?:tag_name|tag|new_tag|custom_tag)\s*:", re.M)
# `contents: write` is the permission a job needs to push a ref at all. Nothing in this repo's
# CI legitimately needs it, so requiring read is the fact-level check that a text scan of
# `run:` lines can never be (§1: assert the outcome, not the proxy).
_WORKFLOW_WRITE_PERM = re.compile(r"^\s*contents:\s*write\b", re.M)


def workflow_findings(text):
    """Tag-creation authority in a CI workflow, keyed on the AUTHORITY not the verb."""
    out = []
    if _WORKFLOW_TAG_ACTIONS.search(text):
        out.append("a release/tag ACTION creates a tag with no git verb in sight")
    if _WORKFLOW_TAG_INPUTS.search(text):
        out.append("a tag_name-shaped workflow input is a tag being created")
    if _WORKFLOW_WRITE_PERM.search(text):
        out.append("contents: write lets the job push a ref; this repo's CI needs read")
    return out


_HEREDOC_OPEN = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?")


def _strip_heredoc_bodies(text):
    """Drop heredoc BODY lines; the opening command line stays.

    A heredoc body is DATA. Writing a file whose prose quotes a tag command is
    documentation, not an attempt to mint a release — and this guard blocked exactly that,
    twice, both times while someone was writing down that it does (Cheliped 2026-08-27, and
    again on the commit that fixed it). The opening line is kept, so a real command on it is
    still inspected, and lines after the delimiter closes are still inspected — the fix must
    narrow the guard without becoming a way to smuggle one past it.

    Shape borrowed from cheliped/tool_guardrails.py::_strip_heredoc_bodies, which solved the
    same problem for its own write-detection.
    """
    out, delim = [], None
    for line in str(text or "").splitlines():
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = _HEREDOC_OPEN.search(line)
        if m:
            delim = m.group(1)
    return "\n".join(out)


def _statements(cmd):
    """Split on statement separators so a chained create is inspected as two statements."""
    cmd = _strip_heredoc_bodies(cmd)
    return [s for s in re.split(r";|&&|\|\||\n|\|", cmd) if s.strip()]


# v1.42 (2026-08-17) — two live FALSE POSITIVES, both recorded through guard_note before
# the fix, and both the same root cause: this guard GREPPED the command instead of parsing
# it, which is the exact failure §12 names in its own rule ("a grep matches your own
# docstring"). The motivating artifacts are frozen in tests/test_hooks.py::test_tag_guard.
#
#   (1) A read-only listing sorted by version was blocked, because the read pattern was an
#       ALLOW-LIST of flags and nobody had enumerated that one. Allow-listing is wrong by
#       construction here: the subcommand cannot create anything without a NAME to create,
#       whatever flags accompany it, so the fact to key on is the name — not the spelling
#       of the flags around it (§1: assert the outcome, not the proxy).
#   (2) The guard then blocked guard_note.py RECORDING the block, because the note quoted
#       the offending command. That made §12's accounting mechanism unusable for precisely
#       the gate most likely to need it. A verb inside a quoted argument is PROSE — the
#       same fact the echo rule above already encodes, generalised: only a verb in command
#       position is an action.
#
# Cost of getting this wrong in the ALLOW direction is not "mild annoyance": a guard that
# blocks reads teaches its operator to reach for the demotion switch, which is how a
# blocking gate becomes a warn-tier one nobody reads.
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
# flags that MAKE a tag; their presence is creation regardless of anything else
_CREATE_FLAGS = frozenset({"-a", "--annotate", "-s", "--sign", "-m", "--message",
                           "-F", "--file", "-u", "--local-user", "-f", "--force",
                           "-e", "--edit"})
# listing/filter flags that CONSUME the next token, so that token is not a name
_VALUE_FLAGS = frozenset({"--sort", "--format", "--points-at", "--merged", "--no-merged",
                          "--contains", "--no-contains", "--color", "--column", "--count",
                          "-n"})
_TAG_SUBCOMMAND = re.compile(_GIT + r"tag\b")


def _strip_quoted(stmt):
    """Quoted text is data, not a command. Replaced with a space so token boundaries
    survive — the difference between reporting a block and being blocked by it."""
    return _QUOTED.sub(" ", stmt)


def _creates_a_tag(stmt):
    """True only when the subcommand is given a NAME to create (a positional argument) or
    a creation flag. Everything else — bare listing, any filter, any format — is a read."""
    match = _TAG_SUBCOMMAND.search(stmt)
    if not match:
        return False
    args = stmt[match.end():].split()
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in _CREATE_FLAGS:
            return True
        if arg.startswith("--") and "=" in arg:
            index += 1                       # --flag=value: value is attached, never a name
            continue
        if arg in _VALUE_FLAGS:
            index += 2                       # the next token belongs to the flag
            continue
        if arg.startswith("-"):
            index += 1                       # any other flag (-l, --list, -n5, --i-am-new)
            continue
        return True                          # a bare positional IS the name being created
    return False


# A statement that merely PRINTS text cannot create a tag. Without this, `echo "David runs
# git tag -s to release"` blocks — the ALLOW-direction false positive this guard's own
# calibration table caught on its first run, and the same family as TEST-LOCK's documented
# "reads are always fine" bypass. Prose is not an action, at the shell as much as in an AST.
_PRINTS_ONLY = re.compile(r"^\s*(?:echo|printf|:|#)\b")


def findings(cmd):
    if not cmd:
        return []
    out = []
    for raw in _statements(cmd):
        # quoted text is data (v1.42): strip it BEFORE any verb match, so a command that
        # merely quotes the forbidden verb — a note, a grep, a message — is not an action
        stmt = _strip_quoted(raw)
        if _PRINTS_ONLY.match(stmt) or _TAG_READ_OR_DELETE.search(stmt):
            continue
        if _creates_a_tag(stmt):
            out.append("creating a release tag is the OWNER's action, not the agent's: "
                       + raw.strip()[:100])
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
    # The remediation line quotes the very command this guard forbids, so it is ASSEMBLED
    # AT RUNTIME: test_installer.py's tracked-file scanner reads this file, and a literal
    # here would make the two halves of release-tag authority fight each other. Same house
    # idiom as the calibration tables — build the needle so the haystack never holds it,
    # never an exemption entry (§6a: exemptions are for internals, not a darkness hatch).
    _t = "t" + "ag"
    lines = list(hits) + [
        "v1.32.0 retired the CIVerd release wall; what authorizes a release is DAVID "
        "creating the {t}. Report the gate result and the version bump, then ASK HIM to "
        "run:  git {t} -a vX.Y.Z -m '...'  &&  git push origin vX.Y.Z".format(t=_t),
        "if this is genuinely his instruction, say so and re-run with "
        "TDD_PLAYBOOK_HOOK_TAGGUARD=warn — do NOT split the command to get it through",
    ]
    return emit(NAME, lines)


if __name__ == "__main__":
    sys.exit(main())
