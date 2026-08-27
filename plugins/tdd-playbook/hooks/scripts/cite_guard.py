#!/usr/bin/env python3
"""Stop — the ANALYSIS-turn seam: claims made without the evidence they imply.

THE GAP THIS CLOSES. All 18 of the plugin's hook bindings attach to a write, a shell
command, or a prompt/stop boundary — and 14 of the 18 bind to `Edit|MultiEdit|Write` or
`Bash`. An ANALYSIS turn (an audit, a diagnosis, a plan written as prose) writes nothing, so
it passes through every one of them untouched, and the one Stop guard that could fire
(`build_completion_reminder`) keys on `git status --porcelain`, which is empty on a read-only
turn. So the Playbook policed how you CHANGE code and not how you REASON about it — even
though §12's claims discipline is entirely about the latter.

THE MOTIVATING INCIDENT (2026-08-27). A turn produced a full §0-shaped build plan from 13
greps, 3 globs and 2 reads — zero writes, zero shell. An independent review found ten
defects, four load-bearing. The diagnostic one: the plan asserted that `doctor.py` reads a
probe's `readable` field. `grep readable doctor.py` returns five hits — "Human-readable
output", "Machine-readable JSON" — all help text. A grep-only reader lands on exactly the
wrong conclusion, which is what CLAUDE.md means by *"not 'the source mentions X' — parse it;
a grep matches your own docstring."* All 15 adversaries were installed, approved and loaded,
and none was called, while the plan PROMISED one in future tense.

TWO RULES, ONE PASS.
  A. A property claim about a file that EXISTS in the tree and that THIS TURN never opened.
     The discriminator is the intersection, not a count: 18 tool calls is plenty of
     "evidence", so a generic evidence check would have passed the motivating turn. The
     defect was 13 searches to 2 reads — and a search cannot tell you what code DOES.
  B. A `Loop closed:` self-report with no dispatch in the transcript. Keyed on the DECLARED
     TOKEN that `commands/tdd-plan.md` (and edge/mutate/probe/integration-audit) already
     mandate — never on "plan shape". A two-or-more-§0-markers detector was the original
     design and would have flagged every review turn, every quoted plan, the release turn,
     and `/readable`, whose own contract FORBIDS dispatching an adversary. "Announced is not
     executed" is the whole point: a turn that PRINTS the closure it never performed.

ADVISORY, AND SHIPPED `off` (opt-in). Three reasons, each from review:
  - `_common.py`'s exit contract routes warn (1) to the USER and block (2) back to CLAUDE.
    This guard's remedy ("open the file") is addressed to the agent, which at warn never
    sees it.
  - The original promotion condition — "a false claim caught BEFORE publication" — is
    unsatisfiable at warn, where the claim is always already published.
  - v1.32.0 retired five guards on 31 warnings and zero blocks. Shipping a sixth warn-default
    guard before the instrument that can tell a useful warning from wallpaper is how you get
    the seventh. The yield instrument (session id, clean-run denominator, honesty events)
    ships alongside precisely so this guard can EARN a promotion instead of assuming one.
  Promotion to `block` stays gated on closing the one-byte-`Read` bypass
  (`Read(f, offset=1, limit=1)` silences rule A), which a blocking gate must not have.

CALIBRATED IN BOTH DIRECTIONS (the house bar, §13), and every silent row in the suite is
paired with a one-field-mutated TWIN that must FIRE — because exit-0-and-silence is this
guard's default behaviour, so a fixture that never reaches the detector satisfies every
negative case for the wrong reason.

Scope stated (§12): this observes whether a file was OPENED, not whether the right lines
were read or understood. It is a floor on evidence, not a proof of correctness.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcript as tr  # noqa: E402
from _common import read_event, emit, log_yield_event, project_root  # noqa: E402

NAME = "cite"

#: Words that turn a file MENTION into a property CLAIM. A bare reference is not a claim —
#: "see also config.py" must stay silent, or the guard fires on every plan that lists files.
_CLAIM_VERBS = (
    r"reads?", r"writes?", r"calls?", r"returns?", r"emits?", r"parses?", r"imports?",
    r"is the only", r"is the sole", r"never", r"does not", r"doesn't", r"always",
    r"requires?", r"is unused", r"is dead", r"is unreachable", r"pinned to",
    r"defaults? to", r"is exempt", r"contains?", r"handles?", r"ignores?",
)
_CLAIM_RE = re.compile(r"\b(?:" + "|".join(_CLAIM_VERBS) + r")\b", re.I)

#: A file reference: `pkg/mod.py`, `mod.py:42`, or a bare `mod.py`.
_FILE_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.[A-Za-z][A-Za-z0-9]{0,5})"
                      r"(?::\d+)?(?![\w/])")

#: The declared loop-closure token the commands mandate.
_LOOP_RE = re.compile(r"^\s*(?:[-*>#\s]*)?\**\s*Loop\s+closed\s*:", re.I | re.M)

_FENCE_RE = re.compile(r"```.*?```", re.S)
_QUOTE_RE = re.compile(r"^\s*>.*$", re.M)
#: Split on terminal punctuation followed by WHITESPACE. Splitting on a bare `.`
#: severs every filename it is meant to find — `doctor.py` became "doctor" + ".py
#: reads ...", so the claim never formed and Rule A matched nothing. Caught by the
#: vacuity leg, which is exactly the leg that exists to catch it.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

#: Directories never worth walking to resolve a bare basename.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
              ".mypy_cache", ".pytest_cache", ".claude", ".codex", "mutants"}
_MAX_WALK = 20_000


def strip_quoted(text):
    """Remove fenced blocks and blockquotes before extracting claims.

    Assistant output routinely QUOTES other material — a pasted transcript, a CHANGELOG
    excerpt, someone else's plan, a subagent's report. A claim inside quoted content is not
    this turn's claim, and treating it as one makes the guard fire on every review.
    """
    return _QUOTE_RE.sub("", _FENCE_RE.sub("", text or ""))


def _resolve(ref, root):
    """A file reference -> an existing realpath, or None.

    A BARE basename resolves only when it is UNAMBIGUOUS in the tree. Measured in this repo,
    `_common.py` exists at eight paths and `test_hooks.py` at six (vendored + worktree
    copies, with rewritten bodies). Guessing which one a claim meant would manufacture
    findings; refusing to guess is the §12 posture.
    """
    if "/" in ref:
        p = ref if os.path.isabs(ref) else os.path.join(root, ref)
        p = os.path.realpath(p)
        return p if os.path.isfile(p) else None
    hits, seen = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if x not in _SKIP_DIRS and not x.startswith(".")]
        seen += len(filenames)
        if ref in filenames:
            hits.append(os.path.realpath(os.path.join(dirpath, ref)))
            if len(hits) > 1:
                return None  # ambiguous: refuse to guess
        if seen > _MAX_WALK:
            break
    return hits[0] if len(hits) == 1 else None


def claims_in(text, root):
    """[(reference, resolved_path, sentence)] for every PROPERTY CLAIM about a real file."""
    out, seen = [], set()
    for sentence in _SENTENCE_SPLIT.split(strip_quoted(text)):
        if not _CLAIM_RE.search(sentence):
            continue
        for ref in _FILE_RE.findall(sentence):
            resolved = _resolve(ref, root)
            if resolved and resolved not in seen:
                seen.add(resolved)
                out.append((ref, resolved, sentence.strip()))
    return out


def turn_text(turn):
    """All assistant text in this turn, concatenated."""
    parts = []
    for rec in turn.records:
        if rec.get("type") != "assistant":
            continue
        content = (rec.get("message") or {}).get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return "\n".join(p for p in parts if p)


def main():
    event = read_event()
    if event.get("stop_hook_active"):
        sys.exit(0)  # re-entry guard — never loop (both existing Stop hooks do this)

    root = project_root()
    turn = tr.current_turn(event.get("transcript_path"))

    # Honesty first: a reader that cannot see must SAY so. These exit 0 like a clean run,
    # but they leave a DIFFERENT row, so `blind`, `capped` and `verified` are three facts
    # in the record instead of one indistinguishable silence. `_common.py:47-48` — absent
    # data is UNMEASURED, never zero.
    if turn.status == tr.UNREADABLE:
        log_yield_event(NAME, "unmeasured", {"reason": "no-transcript"})
        sys.exit(0)
    turn.text = turn_text(turn)
    if turn.status == tr.CAPPED:
        log_yield_event(NAME, "capped", {"records": len(turn.records)})
        sys.exit(0)
    if tr.looks_blind(turn):
        # The pre-C1 Cheliped shim produced exactly this: a READABLE transcript of only
        # hard-coded Edit records. An absent-file fallback never fires there, so without
        # this the guard would report CLEAN on a host it cannot see — a false green.
        log_yield_event(NAME, "blind", {"records": len(turn.records)})
        sys.exit(0)

    findings = []

    # ── Rule A: a property claim about a file this turn never opened ──
    known = tr.read_paths(turn.records, root=root) | tr.edited_paths(turn.records, root=root)
    for ref, resolved, sentence in claims_in(turn.text, root):
        if resolved in known:
            continue
        findings.append(
            'claims a property of `{}` that this turn never read: "{}" — the turn searched '
            'but did not open it. A grep matches your own docstring; open the file, or mark '
            'the claim inherited.'.format(ref, sentence[:160]))

    # ── Rule B: a loop-closure self-report with no dispatch ──
    if _LOOP_RE.search(strip_quoted(turn.text)):
        sent = tr.dispatches(turn.records)
        if not sent:
            roster = tr.agents_roster(os.path.join(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "agents"))
            hint = ""
            if roster:
                want = sorted(roster & {"integration-adversary", "architecture-adversary"})
                if want:
                    hint = " The commands name {}.".format(" and ".join(
                        "`" + w + "`" for w in want))
            findings.append(
                'reports "Loop closed" but this turn dispatched no adversary — announced is '
                'not executed.{} Dispatch them, or name the earlier turn that did.'
                .format(hint))

    log_yield_event(NAME, "verified", {"claims": len(claims_in(turn.text, root)),
                                       "findings": len(findings)})
    emit(NAME, findings)


if __name__ == "__main__":
    main()
