#!/usr/bin/env python3
"""ONE reader for the session transcript, and ONE tool vocabulary.

Before this module the repo held FOUR in-code tool-name sets that already DISAGREED —
`grade_from_otel.EDIT_TOOLS` carried `NotebookEdit`, while `build_completion_reminder`,
`red_lock` and `fixture_guard` did not — plus TWO independent transcript parsers
(`build_completion_reminder.session_edited_paths`, a forward whole-file tool_use walk, and
`capture.last_assistant_text`, a bounded backward assistant-text scan). A plan proposing two
new transcript consumers would have made that five and four.

WHAT IS ACTUALLY CONVERTED, stated precisely because the first draft of this docstring said
"every other site imports from here" and that was FALSE — a claim about files, in the module
underneath the guard built to catch claims about files:
  - `build_completion_reminder.py`  -> imports (parser + EDIT_TOOLS)
  - `capture.py`                    -> imports (assistant-text parser; re-exports it)
  - `red_lock.py`                   -> imports EDIT_TOOLS (this is what fixed its missing
                                       NotebookEdit: a notebook edit to a test file was
                                       invisible to the red-lock recorder)
  - `bin/grade_from_otel.py`        -> imports READ/SEARCH/EDIT via the same sys.path shim
                                       `bin/guard_note.py` already uses
  - `fixture_guard.py`              -> imports EDIT_PAIR_TOOLS, which is a DIFFERENT
                                       concept and was never a disagreement (below)

WHY A SIBLING AND NOT `_common.py`: `_common` is the mode/emit layer. `host_contract.py`
states the layering rule this obeys — *"It does not know Claude/Codex event JSON ... those are
adapter transport concerns."*

THE DISPATCH VOCABULARY IS PINNED AGAINST REAL CAPTURES, NEVER A SELF-WRITTEN FIXTURE.
`docs/telemetry.md:31` records what this repo already paid to learn once:

    the dispatch tool is `Agent`, NOT `Task`. `grade_from_otel.py` was specified against
    `Task` and would have counted zero dispatches forever while its own fixtures passed.

The 2026-08-27 build plan reproduced that exact assumption. Measured against 40 real
transcripts: 47 of 47 dispatch records are `Agent`; ZERO are `Task`. And `subagent_type` is
namespaced in the majority (`tdd-playbook:architecture-adversary`), so an exact-match against
`agents/*.md` stems silently misses most traffic.

`Task` IS RETAINED, AND DO NOT "TIDY" IT AWAY. Stated at length because the next session to
read this will be tempted to collapse two names into one, and that would take a live host dark.

`Task` is not a Claude Code tool name and never was. It is Cheliped's own INVENTED spelling,
chosen by its author when writing `ccbridge/hook_bridge.py::transcript_tool_event`, which maps
its native `ask_<slug>` dispatch to `("Task", {"subagent_type": <un-slugified bare name>})`.
So accepting both names is not backward compatibility with an older convention — there is no
such convention. It is compatibility with one host's arbitrary choice, which is a weaker and
more forgettable reason, which is exactly why it is written down here rather than left to be
re-derived.

Two independent measurements agree that Claude Code emits ONLY `Agent`: 47 of 47 dispatches
across 40 transcripts (this repo, 2026-08-27) and 49 of 49 across 50 sessions (Cheliped's
operator, same window). The original build plan asserted `Task` for Claude Code; that was
wrong, and its author has since confirmed the error.

Net: `Agent` is the real Claude Code name, `Task` is Cheliped's chosen name, the namespacing
differs too, and a guard narrowed to either one alone goes dark on the other host. Any
Cheliped image still in service emits `Task`. `test_hooks.py::test_cite_guard` pins BOTH
spellings, so collapsing this set REDs the suite rather than silently darkening a host.

Scope stated (§12): this reads what the host wrote. It classifies a transcript; it does not
defend against a hand-edited one, any more than the yield log defends against an editor.
"""
import json
import os
import re

# ── the ONE tool vocabulary ──────────────────────────────────────────────────
# Sets, not tuples, and frozen: a caller that mutates a shared vocabulary corrupts every
# other consumer in the same process.

#: Tools that WRITE a file. `NotebookEdit` is included: it was present in
#: `grade_from_otel.EDIT_TOOLS` and absent from all three hook-side copies, and the hook side
#: was simply wrong — a notebook edit is an edit. Unifying resolves it in that direction.
EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})

#: Tools that OPEN a file's contents.
READ_TOOLS = frozenset({"Read", "NotebookRead"})

#: Tools whose input carries EDIT PAIRS (old_string/new_string) rather than whole content.
#: NOT a narrower EDIT_TOOLS and never was: `fixture_guard` reconstructs the post-edit text
#: and must branch, because `Write` carries `content` instead. Naming it stops a real
#: distinction from reading like drift the next time someone unifies these sets.
EDIT_PAIR_TOOLS = frozenset({"Edit", "MultiEdit"})

#: Tools that SEARCH without showing a body. Explicitly NOT reads — that distinction is the
#: whole point of the citation guard, and it already existed in `grade_from_otel.SEARCH_TOOLS`.
SEARCH_TOOLS = frozenset({"Grep", "Glob"})

#: Tools that DISPATCH a subagent. Both spellings are live on real hosts — see the docstring.
DISPATCH_TOOLS = frozenset({"Agent", "Task"})

#: Shell programs that READ a file to stdout. `sed`/`perl` only rewrite in place with `-i`;
#: `lock_guard` already encodes that knowledge for the write direction.
READ_SHELL_PROGRAMS = frozenset({
    "cat", "head", "tail", "less", "more", "bat", "nl", "od", "xxd", "strings",
})

#: Programs that READ unless asked to rewrite in place.
_INPLACE_CAPABLE = frozenset({"sed", "perl", "awk"})

#: The input key each tool carries its path under.
_PATH_KEYS = ("file_path", "notebook_path", "path", "target")

DEFAULT_SCAN_CAP = 8_000_000
_CHUNK = 65_536


def scan_cap():
    """Bytes of transcript this process will read. Env-tunable so the cap path is testable in
    milliseconds against a 2 KB fixture rather than by writing 50 MB inside a 15s hook
    timeout — the shape `capture.py` already proved with TDD_PLAYBOOK_CAPTURE_SCAN_CAP."""
    try:
        return max(1, int(os.environ.get("TDD_PLAYBOOK_TRANSCRIPT_SCAN_CAP") or
                          DEFAULT_SCAN_CAP))
    except (TypeError, ValueError):
        return DEFAULT_SCAN_CAP


# ── status: a reader that cannot see must SAY so ─────────────────────────────
# Never conflate "found nothing" with "could not look". `_common.py:47-48` states the
# doctrine — absent data is UNMEASURED, never zero — and a transcript reader is exactly where
# that distinction is cheapest to lose.
COMPLETE = "complete"      # the whole requested window was read
CAPPED = "capped"          # the byte cap bit before the window was exhausted
UNREADABLE = "unreadable"  # no path, not a file, or an OS error
BLIND = "blind"            # readable, but structurally incapable of answering


class Turn(object):
    """One turn's records plus the honesty status of the read that produced them."""

    __slots__ = ("records", "status", "text")

    def __init__(self, records, status, text=None):
        self.records = records
        self.status = status
        self.text = text

    def __repr__(self):  # pragma: no cover - diagnostics only
        return "Turn(records={}, status={!r})".format(len(self.records), self.status)


def _decode(line):
    if isinstance(line, bytes):
        line = line.decode("utf-8", errors="replace")
    return line


def parse_line(line):
    """One transcript line -> dict, or None when it is not parseable JSON. Malformed lines
    are SKIPPED, never fatal: a real transcript can carry a partially-flushed tail."""
    try:
        obj = json.loads(_decode(line))
    except (ValueError, UnicodeDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def is_user_turn_start(obj):
    """True for a record that begins a HUMAN turn.

    The trap this exists to avoid, measured on a real transcript: tool RESULTS are stored as
    `type:"user"` records too (39 of 52 user records in the sample; 12 were real text, 1 was a
    text block). So "everything after the last user line" yields a window containing one tool
    result and no reads — which would make a citation guard flag every turn it ever saw. A
    turn starts at a user record carrying actual TEXT.
    """
    if not isinstance(obj, dict) or obj.get("type") != "user":
        return False
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text"
                   and str(b.get("text") or "").strip() for b in content)
    return False


def assistant_text_of_record(obj):
    """The concatenated text blocks of one PARSED assistant record, or None.

    The record-level half, so `assistant_text_of` (line-level), `current_turn` (filling
    Turn.text) and any guard all share ONE extractor. Splitting these was how a third copy
    of this concat appeared in cite_guard while this module's thesis was that two parsers
    had become one.
    """
    if not isinstance(obj, dict) or obj.get("type") != "assistant":
        return None
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return None


def assistant_text_of(line):
    """The concatenated text blocks of one assistant LINE, or None. Moved from `capture.py`,
    which imports it from here."""
    return assistant_text_of_record(parse_line(line))


def last_assistant_text(path, cap=None):
    """Backward chunked scan for the LAST COMPLETE assistant line -> (text, truncated).

    Behaviour preserved EXACTLY from `capture.last_assistant_text`, including the live-found
    2026-07-30 case: tool_use-only assistant lines concatenate to "" and are not a final.
    """
    cap = scan_cap() if cap is None else cap
    # RAISES on a missing/unreadable path, deliberately — `capture._run` relies on the
    # OSError propagating so a missing transcript lands in its sidecar error log instead of
    # vanishing. Swallowing it here turned "capture could not read the transcript" into
    # "there was nothing to capture", which its own suite caught. `current_turn` guards with
    # os.path.isfile and returns UNREADABLE instead; the two callers want different things.
    size = os.path.getsize(path)
    buf = b""
    pos = size
    with open(path, "rb") as fh:
        while pos > 0 and len(buf) < cap:
            step = min(_CHUNK, pos, cap - len(buf))
            pos -= step
            fh.seek(pos)
            buf = fh.read(step) + buf
            lines = buf.split(b"\n")
            complete = lines if pos == 0 else lines[1:]
            for ln in reversed(complete):
                if not ln.strip():
                    continue
                text = assistant_text_of(ln)
                if text:
                    return text, False
    if pos == 0:
        return None, False
    return buf.decode("utf-8", errors="replace"), True


def current_turn(path, cap=None):
    """The records of the CURRENT turn — from the last human message to the end of file.

    This primitive did not exist before. Both prior readers were SESSION-scoped: the forward
    walk accumulated every edit in the file, and the backward scan found only the final
    assistant line. A citation guard needs neither — it needs "did THIS turn open that file",
    because the defect it hunts (13 searches, 2 reads) is a per-turn ratio, and a session-wide
    read-set means one Read at hour zero silences the guard for a ten-hour session.

    Returns a Turn. Status is never silently partial: a cap hit yields CAPPED with whatever
    was read, so the caller can abstain loudly instead of publishing half a verdict.
    """
    cap = scan_cap() if cap is None else cap
    if not path or not os.path.isfile(path):
        return Turn([], UNREADABLE)
    try:
        size = os.path.getsize(path)
    except OSError:
        return Turn([], UNREADABLE)

    buf = b""
    pos = size
    hit_cap = False
    try:
        with open(path, "rb") as fh:
            while pos > 0:
                if len(buf) >= cap:
                    hit_cap = True
                    break
                step = min(_CHUNK, pos, cap - len(buf))
                pos -= step
                fh.seek(pos)
                buf = fh.read(step) + buf
                lines = buf.split(b"\n")
                complete = lines if pos == 0 else lines[1:]
                if any(is_user_turn_start(parse_line(ln)) for ln in complete if ln.strip()):
                    break
    except OSError:
        return Turn([], UNREADABLE)

    lines = buf.split(b"\n")
    if pos != 0:
        lines = lines[1:]  # the head line may be truncated mid-record

    records = []
    for ln in lines:
        if not ln.strip():
            continue
        obj = parse_line(ln)
        if obj is None:
            continue
        if is_user_turn_start(obj):
            records = []  # start of the current turn: drop anything earlier
            continue
        records.append(obj)

    # The HOST may have truncated before we ever read a byte. Cheliped's shim caps at 400
    # tool records and says so with {"type":"system","subtype":"truncated"}; treating that
    # as a complete read is the silent partial verdict CAPPED exists to refuse — and it
    # would make the citation guard flag a claim whose read record the HOST dropped. Our own
    # byte cap and the host's record cap are two ways to see less than everything.
    host_truncated = any(r.get("type") == "system" and r.get("subtype") == "truncated"
                         for r in records)
    status = CAPPED if ((hit_cap and pos != 0) or host_truncated) else COMPLETE
    # Fill `text` HERE. It used to be an out-param the consumer filled, so any caller
    # writing the obvious `looks_blind(current_turn(p))` got text=None and every edit-only
    # turn read BLIND — the one reader delegating its own discriminator's input back out.
    text = "\n".join(x for x in (assistant_text_of_record(r) for r in records) if x)
    return Turn(records, status, text or None)


def tool_uses(records):
    """Every `tool_use` block in these records, as {name, input, agent}.

    Walks nested structures because a tool_use lives inside `message.content[]`, and hosts
    differ in how deeply they nest. `_agent` is Cheliped's marker distinguishing a parent's
    call from a subagent's; absent on Claude Code, where subagent calls are in a separate
    sidecar file entirely.
    """
    out = []
    stack = list(records)
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("type") == "tool_use" and cur.get("name"):
                inp = cur.get("input")
                inp = inp if isinstance(inp, dict) else {}
                out.append({"name": str(cur.get("name")),
                            "input": inp,
                            "agent": str(inp.get("_agent") or "") or None,
                            "id": cur.get("id")})
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return out


def errored_tool_ids(records):
    """`tool_use_id`s whose RESULT reported an error.

    A denied permission, a file-too-large refusal and a binary-read failure all leave a
    `tool_use` record behind. Crediting those as reads would let the guard certify a claim on
    evidence the permission system actually refused.
    """
    bad = set()
    stack = list(records)
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if cur.get("type") == "tool_result" and cur.get("is_error"):
                if cur.get("tool_use_id"):
                    bad.add(str(cur["tool_use_id"]))
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return bad


def _path_of(inp):
    for key in _PATH_KEYS:
        val = inp.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _norm(path, root=None):
    """realpath, not abspath: macOS tempdirs are symlinked (/var -> /private/var) and a
    mismatch silently empties every set intersection downstream. Relative paths resolve
    against the project root, never the hook process's cwd."""
    if not path:
        return None
    if not os.path.isabs(path) and root:
        path = os.path.join(root, path)
    try:
        return os.path.realpath(path)
    except (OSError, ValueError):  # pragma: no cover - defensive
        return None


# Read-shaped shell command detection. A heredoc write (`cat > f <<EOF`) begins with `cat`
# and must NEVER be recorded as a read of the file it just clobbered.
_REDIRECT = re.compile(r"(?<![0-9<>])>{1,2}(?!&)")


def read_paths_from_shell(command, root=None):
    """Paths a shell command READ. Splits on statement separators so `cd x && cat y` and
    `cat a; cat b` are each classified on their own."""
    found = set()
    if not command:
        return found
    for stmt in re.split(r"(?:\|\||&&|[;\n|])", str(command)):
        stmt = stmt.strip()
        if not stmt or _REDIRECT.search(stmt):
            continue  # any redirection makes this a write statement, not a read
        try:
            parts = stmt.split()
        except Exception:  # pragma: no cover - defensive
            continue
        if not parts:
            continue
        prog = os.path.basename(parts[0])
        if prog in _INPLACE_CAPABLE:
            # sed/perl only REWRITE with -i; without it they are readers. `lock_guard`
            # encodes the same fact for the write direction.
            if any(a == "-i" or a.startswith("-i") for a in parts[1:]):
                continue
        elif prog not in READ_SHELL_PROGRAMS:
            continue
        for arg in parts[1:]:
            if arg.startswith("-"):
                continue
            p = _norm(arg, root)
            if p and os.path.isfile(p):
                found.add(p)
    return found


def read_paths(records, root=None, include_shell=True):
    """Absolute realpaths this turn OPENED. Searches never count — that is the point."""
    bad = errored_tool_ids(records)
    out = set()
    for tu in tool_uses(records):
        if tu["id"] and str(tu["id"]) in bad:
            continue  # a refused or failed read is not evidence of a read
        if tu["name"] in READ_TOOLS:
            p = _norm(_path_of(tu["input"]), root)
            if p:
                out.add(p)
        elif include_shell and tu["name"] == "Bash":
            out |= read_paths_from_shell(tu["input"].get("command"), root)
    return out


def edited_paths(records, root=None):
    """Absolute realpaths this turn WROTE. Writing implies knowledge of the file."""
    out = set()
    for tu in tool_uses(records):
        if tu["name"] in EDIT_TOOLS:
            p = _norm(_path_of(tu["input"]), root)
            if p:
                out.add(p)
    return out


def normalize_agent_name(name):
    """`tdd-playbook:architecture-adversary` -> `architecture-adversary`.

    Claude Code namespaces the majority of real dispatches; Cheliped's shim emits the bare
    hyphenated name. Matching either against a roster of `agents/*.md` stems requires
    stripping the prefix, or most real traffic reads as no-dispatch.
    """
    s = str(name or "").strip()
    return s.split(":", 1)[1] if ":" in s else s


def dispatches(records):
    """Subagent types dispatched this turn, prefix-stripped. Empty set = none dispatched."""
    out = set()
    for tu in tool_uses(records):
        if tu["name"] in DISPATCH_TOOLS:
            st = tu["input"].get("subagent_type")
            if st:
                out.add(normalize_agent_name(st))
    return out


def agents_roster(agents_dir):
    """The LIVE adversary roster from `agents/*.md` stems — never a hard-coded list, so a new
    adversary is covered the day it is added. None when the directory is absent (UNMEASURED:
    a missing roster is not an empty one)."""
    if not agents_dir or not os.path.isdir(agents_dir):
        return None
    names = {f[:-3] for f in os.listdir(agents_dir)
             if f.endswith(".md") and not f.startswith(".")}
    return names or None


def looks_blind(turn):
    """True when the transcript is readable but structurally incapable of answering.

    The motivating host is Cheliped before its C1 change: `synthesize_transcript` fabricated a
    file containing ONLY hard-coded `Edit` records and no assistant text, and `bridged_stop`
    handed it over as a normal readable transcript — so an "absent transcript" fallback never
    fired and both guards would have reported CLEAN. That is a false green wearing the shape
    of health, which is the exact defect class these guards exist to catch.

    Deliberately narrow: a turn with no assistant text AND no non-edit tool records cannot
    supply either input a claims guard needs. A genuine Claude turn that only edited files
    still HAS assistant text, so it is not blind.
    """
    if not turn.records:
        return True
    if turn.text and turn.text.strip():
        return False
    # `all([])` is already True, so the old trailing `or not tool_uses(...)` was unreachable.
    return all(tu["name"] in EDIT_TOOLS for tu in tool_uses(turn.records))
