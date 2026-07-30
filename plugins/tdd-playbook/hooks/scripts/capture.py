#!/usr/bin/env python3
"""Deliberation capture — evidence collection, never enforcement (CIVerd brief, v1.23).

Appends human turns (UserPromptSubmit) and assistant finals (Stop) to an append-only
per-day JSONL store. The store exists so that "who actually said X" is answerable from
records instead of memory — conveyed ≠ ratified, and only David closes (closure records
are appended by bin/deliberation.py; NO code path here can emit one).

Posture, in order of importance:
- FAIL OPEN. Always exit 0. NEVER write stdout: on UserPromptSubmit stdout is injected
  into context; a nonzero exit blocks the user's own prompt. Errors go to the sidecar
  `.capture-errors.log` inside the store, or nowhere.
- The registered `--event` argument is the fact; the payload's hook_event_name is only a
  cross-check. Unknown or mismatched -> exit 0, write nothing.
- Activation: env TDD_PLAYBOOK_HOOK_CAPTURE=on|off wins; otherwise the enrollment marker
  <store>/ENABLED decides (written by the build on David's machines — a stranger's
  marketplace install ships OFF, never a silent always-on recorder). Env `off` BEATS the
  marker: David's machine is exactly the one that is both enrolled and runs live
  calibration, and the calibration answer key must never enter this store
  (calibration/child_env.py sets the off-env for every nested claude).
- sha256 is computed over the POST-redaction text only — the append-only store must not
  keep a crackable hash of every "redacted" credential forever.
- Dedupe: the plugin+vendored topology can register this hook twice for one event. An
  O_CREAT|O_EXCL sentinel keyed on (session, event, payload bytes) collapses the same
  event instance to ONE record; a sentinel older than the TTL is a legitimately repeated
  identical prompt and is captured again (sha-based suppression would silently drop it).
- Stop reads the assistant final from transcript_path by BACKWARD CHUNKED SCAN until the
  last complete assistant line — a fixed-N tail-seek silently truncates long finals. If
  the scan cap (TDD_PLAYBOOK_CAPTURE_SCAN_CAP, default 8MB) is hit first, the record
  carries truncated: true — never a partial presented as the full turn.

Store: TDD_PLAYBOOK_DELIBERATION_DIR or ~/.claude/deliberation (dir 0700, files 0600).
Record fields (closed whitelist, pinned by test): ts, session_id, cwd, repo, sha,
direction, text, sha256, schema, redactions (+ truncated only when true). Deliberately NO
status field — effective status derives from closure records; missing = open.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback

SCHEMA = 1
DEDUPE_TTL_S = 30.0
CHUNK = 65536

REDACTIONS = [
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("private-key", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")),
    ("secret-assignment", re.compile(
        r"(?i)\b(password|passwd|secret|token|api_key|apikey)\s*[=:]\s*\S{6,}")),
]


# ------------------------------------------------------------------ store module
# (bin/deliberation.py and the registry doctor import these — capture OWNS the store)

def store_dir():
    return os.path.expanduser(
        os.environ.get("TDD_PLAYBOOK_DELIBERATION_DIR") or "~/.claude/deliberation")


def is_active(store):
    knob = os.environ.get("TDD_PLAYBOOK_HOOK_CAPTURE", "").strip().lower()
    if knob == "off":
        return False          # env off BEATS the marker — the answer-key protection
    if knob == "on":
        return True
    return os.path.isfile(os.path.join(store, "ENABLED"))


def day_path(store, when=None):
    day = (when or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%d")
    return os.path.join(store, day + ".jsonl")


def ensure_store(store):
    if not os.path.isdir(store):
        os.makedirs(store, exist_ok=True)
        os.chmod(store, 0o700)  # only when WE create it; never repair perms we don't own


def append_record(store, rec):
    """One fully-built line per os.write — concurrent writers never interleave."""
    ensure_store(store)
    path = day_path(store)
    line = (json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def status():
    """(on, store, records_today) — the doctor's informational line; must never raise."""
    store = store_dir()
    on = is_active(store)
    n = 0
    try:
        with open(day_path(store)) as fh:
            n = sum(1 for ln in fh if ln.strip())
    except OSError:
        pass
    return on, store, n


def redact(text):
    total = 0
    for label, rx in REDACTIONS:
        if label == "secret-assignment":
            text, n = rx.subn(lambda m: m.group(1) + "=[REDACTED:secret-assignment]", text)
        else:
            text, n = rx.subn("[REDACTED:{}]".format(label), text)
        total += n
    return text, total


# ------------------------------------------------------------------ capture internals

def _log_error(store, msg):
    try:
        ensure_store(store)
        path = os.path.join(store, ".capture-errors.log")
        with open(path, "a") as fh:
            fh.write("{} {}\n".format(
                datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                msg.replace("\n", " | ")))
        os.chmod(path, 0o600)
    except Exception:
        pass  # the sidecar failing must not become a new failure


def _is_duplicate(store, session, event, payload_bytes):
    sdir = os.path.join(store, ".sentinels")
    if not os.path.isdir(sdir):
        os.makedirs(sdir, exist_ok=True)
        os.chmod(sdir, 0o700)
    key = hashlib.sha256(
        (session or "").encode() + b"|" + event.encode() + b"|"
        + hashlib.sha256(payload_bytes).digest()).hexdigest()[:32]
    path = os.path.join(sdir, key)
    for _ in range(2):
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            _prune_sentinels(sdir)
            return False
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(path) < DEDUPE_TTL_S:
                    return True   # same event instance (double registration)
                os.remove(path)   # stale: a legitimately repeated identical turn
            except OSError:
                return True
    return False


def _prune_sentinels(sdir, max_age=3600, cap=50):
    try:
        now = time.time()
        for name in os.listdir(sdir)[:cap]:
            p = os.path.join(sdir, name)
            if now - os.path.getmtime(p) > max_age:
                os.remove(p)
    except OSError:
        pass


def _git_info(cwd):
    try:
        top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        if top.returncode != 0 or not top.stdout.strip():
            return None, None
        sha = subprocess.run(["git", "-C", cwd, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return (os.path.basename(top.stdout.strip()),
                sha.stdout.strip() or None if sha.returncode == 0 else None)
    except Exception:
        return None, None


def _assistant_text_of(line_bytes):
    """The concatenated text blocks of one transcript line, or None if it is not an
    assistant message line."""
    try:
        obj = json.loads(line_bytes.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict) or obj.get("type") != "assistant":
        return None
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content
                       if isinstance(b, dict) and b.get("type") == "text")
    return None


def last_assistant_text(path, cap):
    """Backward chunked scan for the LAST COMPLETE assistant line. Returns (text,
    truncated). Cap hit before a complete assistant line -> the decoded tail flagged
    truncated=True; whole file scanned with no assistant line -> (None, False)."""
    size = os.path.getsize(path)
    buf = b""
    pos = size
    with open(path, "rb") as fh:
        while pos > 0 and len(buf) < cap:
            step = min(CHUNK, pos, cap - len(buf))
            pos -= step
            fh.seek(pos)
            buf = fh.read(step) + buf
            lines = buf.split(b"\n")
            # lines[0] may be missing its head unless we reached file start
            complete = lines if pos == 0 else lines[1:]
            for ln in reversed(complete):
                if not ln.strip():
                    continue
                text = _assistant_text_of(ln)
                if text is not None:
                    return text, False
    if pos == 0:
        return None, False  # whole file scanned: genuinely no assistant line
    return buf.decode("utf-8", errors="replace"), True


def _run(argv):
    if "--event" not in argv:
        return
    event = argv[argv.index("--event") + 1] if argv.index("--event") + 1 < len(argv) else ""
    if event not in ("UserPromptSubmit", "Stop"):
        return
    raw = sys.stdin.buffer.read()
    try:
        payload = json.loads(raw.decode("utf-8", errors="replace")) if raw.strip() else {}
    except ValueError:
        return
    if payload.get("hook_event_name") != event:
        return  # the registration is the fact; a mismatched payload is not ours to record
    store = store_dir()
    if not is_active(store):
        return
    if event == "Stop" and payload.get("stop_hook_active"):
        return
    ensure_store(store)
    if _is_duplicate(store, payload.get("session_id"), event, raw):
        return
    truncated = False
    if event == "UserPromptSubmit":
        text, direction = payload.get("prompt") or "", "human"
    else:
        cap = int(os.environ.get("TDD_PLAYBOOK_CAPTURE_SCAN_CAP") or 8_000_000)
        text, truncated = last_assistant_text(payload["transcript_path"], cap)
        if text is None:
            return
        direction = "assistant"
    cwd = payload.get("cwd") or os.getcwd()
    repo, sha = _git_info(cwd)
    text, n_red = redact(text)
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "session_id": payload.get("session_id"), "cwd": cwd, "repo": repo, "sha": sha,
           "direction": direction, "text": text,
           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
           "schema": SCHEMA, "redactions": n_red}
    if truncated:
        rec["truncated"] = True
    append_record(store, rec)


def main(argv=None):
    try:
        _run(argv if argv is not None else sys.argv[1:])
    except Exception:
        _log_error(store_dir(), traceback.format_exc())
    return 0  # fail open, unconditionally


if __name__ == "__main__":
    sys.exit(main())
