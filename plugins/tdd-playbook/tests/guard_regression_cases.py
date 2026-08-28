#!/usr/bin/env python3
"""Regressions for three defects found by USING the plugin (Cheliped report, 2026-08-27).

Each was verified in this repo before it was accepted — a secondhand report is an
unverified claim (SS12) — and each is pinned red-first with a TWIN, because all three
fixes NARROW a guard, and narrowing a guard is not amnesty (SS13): the half that must
survive every narrowing is the half that still blocks.

R1 - the HOST's truncation marker was ignored. transcript.py had a `capped` status for its
     OWN byte cap and was blind to the host saying "I truncated": Cheliped's shim caps at
     400 tool records and emits {"type":"system","subtype":"truncated"}. A partial
     transcript therefore read COMPLETE, so a claim whose read record had been truncated
     away would be flagged as unread - a false positive AND the silent partial verdict the
     `capped` status exists to refuse.

R2 - tag_guard blocked a READ-ONLY listing as soon as anything followed it: the
     read-allowance alternation ended at an end-of-string anchor, so a listing with a
     redirect stopped matching "read" and fell through to "create". Fails safe, so it is
     annoyance not exposure - but the guard fired three times in one session on listings
     and never once on a real attempt, and a guard that cries wolf gets demoted.
     SCOPE: the reporter's table also listed the pipe form as blocked; verified NOT to
     block end-to-end (the pipe splits the statement), so only the redirect form is pinned.

R4 - PreToolUse Bash guards HUNG until the 15s hook timeout. Root cause is not slowness:
     every guard runs in 35-90ms. `read_event` called sys.stdin.read(), which blocks until
     EOF, so an invocation whose stdin is an open pipe carrying no data waits forever and is
     killed as hook_cancelled/timedOut - blocking the user's loop on every Bash call it
     fires on. Raising the timeout would have treated the symptom. Failing open FAST is also
     strictly safer than hanging: a cancelled hook did not block either, and it cost 15s.

R3 - tag_guard matched inside HEREDOC BODIES, so writing a file whose PROSE quotes the
     command was blocked. Found, both times, by the guard blocking the act of documenting
     it - including on this very commit.
"""
import json
import os
import subprocess
import sys
import tempfile

TRIG = "git " + "tag"
PUSH = "git push --" + "tags"


def register(check, run, HOOKS, YIELD_TMP, helpers):
    _user, _tool_use, _assistant_text, _write_transcript, _cite_run = helpers
    import importlib.util as _il
    spec = _il.spec_from_file_location("transcript", os.path.join(HOOKS, "transcript.py"))
    tr = _il.module_from_spec(spec)
    spec.loader.exec_module(tr)

    with tempfile.TemporaryDirectory() as d:
        lines = [_user("audit it"),
                 _tool_use("Grep", {"pattern": "readable", "_agent": "cheli"}, "g1"),
                 json.dumps({"type": "system", "subtype": "truncated",
                             "note": "tool records capped at 400"}),
                 _assistant_text("doctor.py reads the readable field.")]
        turn = tr.current_turn(_write_transcript(d, lines, "trunc.jsonl"))
        check("R1: a HOST truncation marker yields CAPPED, never COMPLETE",
              turn.status == tr.CAPPED, turn.status)
        turn2 = tr.current_turn(_write_transcript(
            d, [lines[0], lines[1], lines[3]], "ok.jsonl"))
        check("R1 twin: the same turn WITHOUT the marker still reads COMPLETE",
              turn2.status == tr.COMPLETE, turn2.status)

        open(os.path.join(d, "doctor.py"), "w").write("# Human-readable output\n")
        yl = os.path.join(YIELD_TMP, "trunc-yield.jsonl")
        rc, err = _cite_run(d, lines, env_extra={"TDD_PLAYBOOK_YIELD_LOG": yl},
                            name="trunc2.jsonl")
        rows = [json.loads(l) for l in open(yl)] if os.path.exists(yl) else []
        check("R1: the guard ABSTAINS on a host-truncated turn and logs `capped`",
              rc == 0 and any(r.get("event") == "capped" for r in rows),
              (rc, [r.get("event") for r in rows]))

    def tag(cmd):
        return run("tag_guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}})

    for cmd in (TRIG, TRIG + " 2>/dev/null", TRIG + " | tail -5", TRIG + " --list",
                TRIG + " -l 2>/dev/null", TRIG + " -n1 --list v1.0", TRIG + " -d v1.0",
                TRIG + " --list > /tmp/tags.txt"):
        rc, _, err = tag(cmd)
        check("R2: read-only listing is ALLOWED - `{}`".format(cmd), rc == 0, (rc, err[:90]))

    for cmd in (TRIG + " -a v1.0 -m x", TRIG + " v1.0", PUSH,
                "git push origin v1.0", "gh release create v1.0",
                "git update-ref refs/tags/v1.0 HEAD"):
        rc, _, err = tag(cmd)
        check("R2 twin: a real CREATION is still BLOCKED - `{}`".format(cmd),
              rc == 2, (rc, err[:90]))

    # ── R4: no guard may block on stdin ──
    for g in ("lock_guard.py", "fixture_guard.py", "tag_guard.py", "snapshot_guard.py"):
        proc = subprocess.Popen([sys.executable, os.path.join(HOOKS, g)],
                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                env=dict(os.environ, TDD_PLAYBOOK_STDIN_WAIT="1"))
        try:
            proc.wait(timeout=8)
            hung = False
        except subprocess.TimeoutExpired:
            proc.kill()
            hung = True
        check("R4: `{}` fails open FAST on an open-but-silent stdin, "
              "never hanging to the hook timeout".format(g),
              not hung and proc.returncode == 0, (g, hung, proc.returncode))

    heredoc = ("cat > notes.md <<'EOF'\n"
               "To release, run: " + TRIG + " -a v1.0 -m msg\n"
               "then: " + PUSH + "\n"
               "EOF\n")
    rc, _, err = tag(heredoc)
    check("R3: a heredoc BODY quoting the command is prose, not an attempt",
          rc == 0, (rc, err[:120]))
    rc, _, err = tag(heredoc + TRIG + " -a v1.0 -m real\n")
    check("R3 twin: a real command AFTER the heredoc closes still BLOCKS "
          "(the fix must not become a bypass)", rc == 2, (rc, err[:120]))
