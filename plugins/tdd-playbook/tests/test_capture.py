#!/usr/bin/env python3
"""Planted-input calibration for hooks/scripts/capture.py — deliberation capture (briefs D3).

Capture is EVIDENCE COLLECTION, never enforcement: fail open (always exit 0), NEVER stdout
(UserPromptSubmit stdout becomes injected context; Stop exit 2 blocks the turn). The store is
append-only per-day JSONL under TDD_PLAYBOOK_DELIBERATION_DIR (default ~/.claude/deliberation)
with a closed field whitelist — NO status field (effective status derives from closure records
appended only by bin/deliberation.py). sha256 is computed over POST-redaction text only, so the
append-only store never keeps a crackable hash of a "redacted" credential. Env off BEATS the
enrollment marker — the named answer-key protection: David's machine is exactly the one that is
both enrolled and runs live calibration.

Self-contained, no pytest. Run: python3 tests/test_capture.py
"""
import glob
import hashlib
import json
import os
import stat as statmod
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
CAP = os.path.join(PLUGIN, "hooks", "scripts", "capture.py")
DELIB = os.path.join(PLUGIN, "bin", "deliberation.py")
HOOKS_JSON = os.path.join(PLUGIN, "hooks", "hooks.json")

REQUIRED_FIELDS = {"ts", "session_id", "cwd", "repo", "sha", "direction", "text",
                   "sha256", "schema", "redactions"}
OPTIONAL_FIELDS = {"truncated"}

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def clean_env(store, extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("TDD_PLAYBOOK_")}
    env["TDD_PLAYBOOK_DELIBERATION_DIR"] = store
    env.update(extra or {})
    return env


def run_cap(event_arg, payload, store, extra_env=None):
    return subprocess.run([sys.executable, CAP, "--event", event_arg],
                          input=json.dumps(payload), capture_output=True, text=True,
                          env=clean_env(store, extra_env), timeout=60)


def records(store):
    out = []
    for path in sorted(glob.glob(os.path.join(store, "????-??-??.jsonl"))):
        with open(path) as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
    return out


def prompt_payload(text, session="sess-1", cwd=None):
    return {"hook_event_name": "UserPromptSubmit", "session_id": session,
            "cwd": cwd or os.getcwd(), "prompt": text}


def stop_payload(transcript, session="sess-1", active=False, cwd=None):
    return {"hook_event_name": "Stop", "session_id": session, "cwd": cwd or os.getcwd(),
            "transcript_path": transcript, "stop_hook_active": active}


def assistant_line(text, blocks=None):
    content = blocks or [{"type": "text", "text": text}]
    return json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                        "content": content}})


ON = {"TDD_PLAYBOOK_HOOK_CAPTURE": "on"}


def test_capture_writes_a_record():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        p = run_cap("UserPromptSubmit", prompt_payload("hello playbook"), store, ON)
        check("capture: exit 0", p.returncode == 0, (p.returncode, p.stderr))
        check("capture: NEVER stdout (would inject context)", p.stdout == "", p.stdout[:200])
        recs = records(store)
        check("capture: exactly one record written", len(recs) == 1, recs)
        if not recs:
            return
        r = recs[0]
        check("record: direction human + text verbatim",
              r.get("direction") == "human" and r.get("text") == "hello playbook", r)
        check("record: field whitelist exact — no status, nothing extra",
              REQUIRED_FIELDS <= set(r) <= (REQUIRED_FIELDS | OPTIONAL_FIELDS), sorted(r))
        check("record: redactions present and 0 when none", r.get("redactions") == 0, r)
        check("record: sha256 over the stored text",
              r.get("sha256") == hashlib.sha256(r["text"].encode()).hexdigest(), r)
        mode = statmod.S_IMODE(os.stat(store).st_mode)
        fmode = statmod.S_IMODE(os.stat(glob.glob(
            os.path.join(store, "????-??-??.jsonl"))[0]).st_mode)
        check("store: dir 0700, file 0600", mode == 0o700 and fmode == 0o600,
              (oct(mode), oct(fmode)))


def test_activation_default_off_without_enrollment():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        p = run_cap("UserPromptSubmit", prompt_payload("x"), store)
        check("no env, no marker (a stranger's install): NO record, exit 0",
              p.returncode == 0 and not records(store), records(store))
        os.makedirs(store, 0o700, exist_ok=True)
        open(os.path.join(store, "ENABLED"), "w").close()
        run_cap("UserPromptSubmit", prompt_payload("y"), store)
        check("enrollment marker alone turns capture ON", len(records(store)) == 1,
              records(store))


def test_env_off_beats_enrollment_marker():
    """THE answer-key protection (CIVerd-CTO amendment 2), explicit and named: the one
    machine that is both enrolled and runs live calibration is David's — marker-wins would
    silently void the calibration exclusion exactly there."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        os.makedirs(store, 0o700)
        open(os.path.join(store, "ENABLED"), "w").close()
        p = run_cap("UserPromptSubmit", prompt_payload("the answer key"), store,
                    {"TDD_PLAYBOOK_HOOK_CAPTURE": "off"})
        check("ENABLED marker present AND env off -> NO record (env off wins)",
              p.returncode == 0 and not records(store), records(store))


def test_unwritable_store_never_blocks_the_prompt():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        os.makedirs(store, 0o700)
        os.chmod(store, 0o000)
        try:
            p = run_cap("UserPromptSubmit", prompt_payload("x"), store, ON)
            check("unwritable store: exit 0, silent on stdout (fail OPEN)",
                  p.returncode == 0 and p.stdout == "", (p.returncode, p.stdout))
        finally:
            os.chmod(store, 0o700)


def test_hooks_json_registers_capture():
    cfg = json.load(open(HOOKS_JSON))
    found = {}
    for bucket in ("UserPromptSubmit", "Stop"):
        for entry in cfg["hooks"].get(bucket, []):
            for h in entry.get("hooks", []):
                if "capture.py" in h.get("command", ""):
                    found[bucket] = h
    check("hooks.json: capture registered on BOTH UserPromptSubmit and Stop",
          set(found) == {"UserPromptSubmit", "Stop"}, sorted(found))
    check("hooks.json: registration carries the explicit --event arg (the fact; payload "
          "hook_event_name is only a cross-check)",
          all("--event {}".format(b) in found.get(b, {}).get("command", "")
              for b in ("UserPromptSubmit", "Stop")), found)
    check("hooks.json: capture entries carry a timeout",
          all(isinstance(h.get("timeout"), int) for h in found.values()), found)


def test_redaction_and_post_redaction_hash():
    secret_prompt = "deploy with key AKIAABCDEFGHIJKLMNOP and password=hunter2secret ok"
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        run_cap("UserPromptSubmit", prompt_payload(secret_prompt), store, ON)
        recs = records(store)
        check("redaction: record written for a secret-bearing prompt", len(recs) == 1, recs)
        if not recs:
            return
        r = recs[0]
        check("redaction: secrets replaced, count > 0",
              "AKIAABCDEFGHIJKLMNOP" not in r["text"] and "hunter2secret" not in r["text"]
              and "[REDACTED" in r["text"] and r["redactions"] >= 2, r)
        check("redaction: sha256 is over POST-redaction text ONLY",
              r["sha256"] == hashlib.sha256(r["text"].encode()).hexdigest(), r)
        raw = open(glob.glob(os.path.join(store, "????-??-??.jsonl"))[0]).read()
        raw_hash = hashlib.sha256(secret_prompt.encode()).hexdigest()
        check("redaction: raw text's hash appears NOWHERE (no crackable residue)",
              raw_hash not in raw and "AKIAABCDEFGHIJKLMNOP" not in raw, raw_hash)


def test_stop_captures_assistant_final():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        tr = os.path.join(d, "t.jsonl")
        with open(tr, "w") as fh:
            fh.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
            fh.write(assistant_line("", blocks=[{"type": "text", "text": "part one. "},
                                               {"type": "text", "text": "part two."}]) + "\n")
        run_cap("Stop", stop_payload(tr), store, ON)
        recs = records(store)
        check("stop: one assistant record", len(recs) == 1
              and recs[0].get("direction") == "assistant", recs)
        check("stop: text is the CONCATENATED final assistant blocks",
              recs and recs[0].get("text") == "part one. part two.", recs)


def test_stop_backward_scan_recovers_a_long_final():
    """CIVerd-CTO amendment 3: a fixed-N tail-seek silently truncates long finals — a
    200KB final behind 300KB of later padding lines must come back COMPLETE."""
    big = "review finding line. " * 10000  # ~210KB
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        tr = os.path.join(d, "t.jsonl")
        with open(tr, "w") as fh:
            fh.write(json.dumps({"type": "user", "message": {"content": "go"}}) + "\n")
            fh.write(assistant_line(big) + "\n")
            for _ in range(300):
                fh.write(json.dumps({"type": "system", "note": "x" * 1000}) + "\n")
        run_cap("Stop", stop_payload(tr), store, ON)
        recs = records(store)
        check("stop: long final fully recovered through trailing non-assistant lines",
              len(recs) == 1 and recs[0].get("text") == big
              and not recs[0].get("truncated"),
              (len(recs), recs[0].get("truncated") if recs else None,
               len(recs[0].get("text", "")) if recs else 0))


def test_stop_truncation_is_flagged_never_silent():
    big = "y" * 20000
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        tr = os.path.join(d, "t.jsonl")
        with open(tr, "w") as fh:
            fh.write(assistant_line(big) + "\n")
        run_cap("Stop", stop_payload(tr), store,
                dict(ON, TDD_PLAYBOOK_CAPTURE_SCAN_CAP="4096"))
        recs = records(store)
        check("stop: scan cap hit -> record carries truncated: true (never a partial "
              "presented as the full turn)",
              len(recs) == 1 and recs[0].get("truncated") is True, recs)


def test_stop_reentry_guard():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        tr = os.path.join(d, "t.jsonl")
        with open(tr, "w") as fh:
            fh.write(assistant_line("final") + "\n")
        p = run_cap("Stop", stop_payload(tr, active=True), store, ON)
        check("stop_hook_active re-entry: exit 0, NO record",
              p.returncode == 0 and not records(store), records(store))


def test_event_mismatch_writes_nothing():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        p = run_cap("Stop", prompt_payload("x"), store, ON)
        check("payload/arg mismatch: exit 0, nothing written",
              p.returncode == 0 and not records(store), (p.returncode, records(store)))
        p = run_cap("SubagentStop", prompt_payload("x"), store, ON)
        check("unknown --event: exit 0, nothing written (fail open, no argparse blast)",
              p.returncode == 0 and not records(store), (p.returncode, p.stderr[:200]))


def test_double_registration_dedupe_but_not_repeats():
    """CIVerd-CTO amendment 4: the plugin+vendored double-registration must collapse to ONE
    record, but a deliberately repeated identical prompt is a legitimate turn — sha-based
    suppression would silently drop it from a store that promises completeness."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        payload = prompt_payload("run it again")
        run_cap("UserPromptSubmit", payload, store, ON)
        run_cap("UserPromptSubmit", payload, store, ON)
        check("double registration (same event instance): ONE record",
              len(records(store)) == 1, len(records(store)))
        sent = glob.glob(os.path.join(store, ".sentinels", "*"))
        check("dedupe mechanism is the O_CREAT|O_EXCL sentinel", len(sent) >= 1, sent)
        old = time.time() - 120
        for s in sent:
            os.utime(s, (old, old))
        run_cap("UserPromptSubmit", payload, store, ON)
        check("repeated identical prompt (new event instance): TWO records",
              len(records(store)) == 2, len(records(store)))


def test_no_git_cwd_yields_null_repo_sha():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        plain = os.path.join(d, "plain")
        os.makedirs(plain)
        run_cap("UserPromptSubmit", prompt_payload("x", cwd=plain), store, ON)
        recs = records(store)
        check("no-git cwd: repo and sha are null, never a guess",
              len(recs) == 1 and recs[0]["repo"] is None and recs[0]["sha"] is None, recs)


def test_megabyte_paste():
    big = "K" * 1_000_000
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        p = run_cap("UserPromptSubmit", prompt_payload(big), store, ON)
        recs = records(store)
        check("1MB paste: captured whole, exit 0",
              p.returncode == 0 and len(recs) == 1 and recs[0]["text"] == big
              and recs[0]["sha256"] == hashlib.sha256(big.encode()).hexdigest(),
              (p.returncode, len(recs)))


def test_non_utf8_transcript_fails_open():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        tr = os.path.join(d, "t.jsonl")
        with open(tr, "wb") as fh:
            fh.write(b'\xff\xfe garbage \xf0\x28\x8c\x28\n')
            fh.write(assistant_line("clean final").encode() + b"\n")
        p = run_cap("Stop", stop_payload(tr), store, ON)
        check("non-UTF8 transcript bytes: exit 0, no stdout, clean final still captured",
              p.returncode == 0 and p.stdout == "" and len(records(store)) == 1
              and records(store)[0]["text"] == "clean final",
              (p.returncode, records(store)))


def test_missing_transcript_fails_open_with_sidecar():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        p = run_cap("Stop", stop_payload(os.path.join(d, "nope.jsonl")), store, ON)
        side = os.path.join(store, ".capture-errors.log")
        check("missing transcript: exit 0, no record, error in the sidecar not the void",
              p.returncode == 0 and not records(store) and os.path.isfile(side)
              and os.path.getsize(side) > 0, (p.returncode, os.path.isfile(side)))


def test_concurrent_two_process_append():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        procs = [subprocess.Popen([sys.executable, CAP, "--event", "UserPromptSubmit"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True,
                                  env=clean_env(store, ON))
                 for _ in range(2)]
        for i, pr in enumerate(procs):
            pr.communicate(json.dumps(prompt_payload("turn {}".format(i),
                                                     session="s{}".format(i))), timeout=60)
        recs = records(store)
        check("two concurrent writers: both records land, every line parses",
              len(recs) == 2 and {r["text"] for r in recs} == {"turn 0", "turn 1"}, recs)


def test_closure_only_from_deliberation_verb():
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        run_cap("UserPromptSubmit", prompt_payload("a turn"), store, ON)
        check("capture records never carry the closure shape",
              all("closure" not in r for r in records(store)), records(store))
        p = subprocess.run([sys.executable, DELIB, "close", "--session", "sess-1",
                            "--note", "reviewed"], capture_output=True, text=True,
                           env=clean_env(store), timeout=60)
        closures = [r for r in records(store) if "closure" in r]
        check("deliberation close: appends a closure record (event-sourced, no rewrite)",
              p.returncode == 0 and len(closures) == 1
              and closures[0]["closure"].get("session_id") == "sess-1", (p.returncode, p.stderr))
        before = open(glob.glob(os.path.join(store, "????-??-??.jsonl"))[0]).read()
        check("close appended — the original capture line is still byte-present",
              '"a turn"' in before, before[:200])
        p = subprocess.run([sys.executable, DELIB, "stats"], capture_output=True,
                           text=True, env=clean_env(store), timeout=60)
        check("deliberation stats: reports records and bytes (the measured volume number)",
              p.returncode == 0 and "record" in p.stdout.lower()
              and "byte" in p.stdout.lower(), (p.returncode, p.stdout))


def main():
    print("deliberation-capture calibration")
    for missing, what in ((CAP, "hooks/scripts/capture.py"), (DELIB, "bin/deliberation.py")):
        if not os.path.isfile(missing):
            check("{} exists".format(what), False, "missing")
    tests = (test_capture_writes_a_record,
             test_activation_default_off_without_enrollment,
             test_env_off_beats_enrollment_marker,
             test_unwritable_store_never_blocks_the_prompt,
             test_hooks_json_registers_capture,
             test_redaction_and_post_redaction_hash,
             test_stop_captures_assistant_final,
             test_stop_backward_scan_recovers_a_long_final,
             test_stop_truncation_is_flagged_never_silent,
             test_stop_reentry_guard,
             test_event_mismatch_writes_nothing,
             test_double_registration_dedupe_but_not_repeats,
             test_no_git_cwd_yields_null_repo_sha,
             test_megabyte_paste,
             test_non_utf8_transcript_fails_open,
             test_missing_transcript_fails_open_with_sidecar,
             test_concurrent_two_process_append,
             test_closure_only_from_deliberation_verb)
    if os.path.isfile(CAP) and os.path.isfile(DELIB):
        for fn in tests:
            fn()
    else:
        _ = tests  # referenced either way; the runs-guard audits invocation sites
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
