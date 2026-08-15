#!/usr/bin/env python3
"""PreToolUse — warn when an EXPECTED ANSWER in a test-data file is rewritten or removed.

The gap this closes (observed in a private calibration run, 2026-08-15; artifact archived
privately): test_weakening_guard watches test CODE (assert/skip/tautology counts) and is
structurally blind to test DATA — a `test_cases.json` / fixtures / golden file. An agent
under pressure can rewrite an expected value, or delete a failing case, to green a suite
without touching code. TEST-LOCK covers it only when a human named the file; default
posture did not watch it at all.

Design (David's call — resolves warning fatigue): warn ONLY when an expected value changes
or a case is removed. Adding a new case, or editing an unrelated field, is silent — a
warn on every fixture edit is noise you learn to ignore, and an ignored warn is worse than
no guard. Mode: WARN (advisory; promote to block on yield evidence, retire on silence).

  - Edit/MultiEdit/Write (PreToolUse — the on-disk file is still the OLD version): the full
    new text is reconstructed and diffed against the old. A leaf value changed, or a
    dict key / list element removed, warns; pure additions are silent. When old/new can't
    be parsed (malformed JSON, or YAML with no stdlib parser), fall back to a size-shrink
    heuristic so an unparseable value-removal still warns while a malformed-legit-reformat
    stays silent.
  - Bash: delete / overwrite / move / rename / copy-over / `git rm` / `git mv` of an
    existing test-data file — reusing test_lock_guard's cd-aware `segments` + FP-calibrated
    `_seg_writes`, plus git rm/mv (not a revert, so not covered there).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, file_path_of, edit_pairs, is_test_file  # noqa: E402
from snapshot_guard import snapshot_path  # noqa: E402  (its territory; do not double-warn)
from test_lock_guard import segments, _seg_writes  # noqa: E402  (FP-calibrated shell writes)

NAME = "fixtureguard"

_DATA_EXT = (".json", ".yaml", ".yml")
_FIXTURE_TOKEN = re.compile(r"[\w./~-]+\.(?:json|ya?ml)\b")
_GIT_RM_MV = re.compile(r"\bgit\s+(?:rm|mv)\b")
# A FIELD whose value is an expected answer (test_cases.json's `output`, etc.). A scalar
# change under such a key warns; a change to `input`/metadata does not.
_ANSWER_KEY = re.compile(r"output|expected|answer|result|oracle", re.I)
# A FILE that is answers all the way down (a bare golden/expected file with no answer key
# to signal on) — its whole content is treated as answer context.
_ANSWER_PATH = re.compile(r"/golden/|golden|expected|oracle", re.I)


def is_fixture_data(path):
    """A test-DATA file: a data-extension file under a test path or a fixtures/golden dir,
    excluding snapshot territory (snapshot_guard owns .snap/.ambr/__snapshots__)."""
    p = (path or "").replace("\\", "/")
    if not p.lower().endswith(_DATA_EXT):
        return False
    if snapshot_path(p):
        return False
    return is_test_file(p) or "/fixtures/" in p or "/golden/" in p


def _parse(path, text):
    """Parsed structure, or None when it cannot be parsed here (malformed, or YAML with no
    stdlib parser — PyYAML is not guaranteed in a hook's environment)."""
    low = (path or "").lower()
    try:
        if low.endswith(".json"):
            return json.loads(text)
        if low.endswith((".yaml", ".yml")):
            import yaml  # optional; absent -> structural fallback
            return yaml.safe_load(text)
    except Exception:
        return None
    return None


def _suspicious(old, new, answer=False):
    """True iff a case was REMOVED (always suspicious) or an ANSWER value changed. Pure
    additions (new keys, appended elements) and edits to non-answer fields (`input`,
    metadata) are silent — David's scoping to keep the signal rare and real. `answer` is
    carried down through answer-like keys (and set at the root for golden/expected files)."""
    if type(old) is not type(new):
        return True                       # a value/case reshaped in place
    if isinstance(old, dict):
        for k in old:
            if k not in new:
                return True               # removal — always suspicious
            if _suspicious(old[k], new[k], answer or bool(_ANSWER_KEY.search(str(k)))):
                return True
        return False                      # new keys = additions
    if isinstance(old, list):
        # Multiset match, not positional — a prepend/append/reorder must read as authoring,
        # not "every element changed". An old element is PRESERVED if some new element
        # differs from it only in non-answer ways; an old element with no such counterpart
        # was removed or had its answer rewritten.
        return any(all(_suspicious(oe, ne, answer) for ne in new) for oe in old)
    if old == new:
        return False
    return answer                         # changed scalar: suspicious only under an answer


def _value_change(path, old_text, new_text):
    """(changed, reason). Parsed comparison when possible; size-shrink fallback otherwise."""
    o, n = _parse(path, old_text), _parse(path, new_text)
    if o is not None and n is not None:
        if _suspicious(o, n, answer=bool(_ANSWER_PATH.search((path or "").lower()))):
            return True, "an expected answer was changed or a case removed"
        return False, ""
    if len(new_text.strip()) < len(old_text.strip()):
        return True, "test-data file shrank (a value/case removed; unparseable — size-based)"
    return False, ""


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _bash_findings(cmd, root):
    hits = []
    for seg, _cwd in segments(cmd, root):
        fixtures = [t for t in set(_FIXTURE_TOKEN.findall(seg)) if is_fixture_data(t)]
        if not fixtures:
            continue
        git_rmmv = bool(_GIT_RM_MV.search(seg))
        for t in fixtures:
            if git_rmmv or _seg_writes(seg, t):
                hits.append(t)
    if not hits:
        return []
    return [
        "test-data file written/removed via shell: {} (delete / overwrite / move / rename "
        "of an existing answer key)".format(", ".join(sorted(set(hits)))),
        "adding cases is fine; removing or rewriting expected answers is a human "
        "disposition (a test-wrong unlock), not an inline fix",
    ]


def main():
    event = read_event()
    tool = event.get("tool_name", "")
    if tool == "Bash":
        cmd = (event.get("tool_input", {}) or {}).get("command", "")
        emit(NAME, _bash_findings(cmd, os.getcwd()))
        return
    path = file_path_of(event)
    if not is_fixture_data(path):
        emit(NAME, [])
        return
    old_text = _read(path)
    if not old_text:                         # new file (creation) or unreadable -> silent
        emit(NAME, [])
        return
    if tool in ("Edit", "MultiEdit"):
        new_text = old_text
        for old_s, new_s in edit_pairs(event):
            new_text = new_text.replace(old_s, new_s, 1)
    elif tool == "Write":
        new_text = (event.get("tool_input", {}) or {}).get("content", "")
    else:
        emit(NAME, [])
        return
    changed, reason = _value_change(path, old_text, new_text)
    emit(NAME, [
        "test-data value change in {}: {}".format(os.path.basename(path), reason),
        "if the expected answer is wrong, that is a human disposition (a test-wrong "
        "unlock), not an inline fix — change the code, or say why the fixture is wrong",
    ] if changed else [])


if __name__ == "__main__":
    main()
