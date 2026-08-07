#!/usr/bin/env python3
"""Host-neutral contracts for repository identity, TEST-LOCK state, and decisions.

This is deliberately a narrow evolutionary seam.  It knows Git identity, the versioned
lock/evidence shapes, containment, and pure path policy.  It does *not* know Claude/Codex
event JSON, shell syntax, hook exit codes, installation paths, or user messages; those are
adapter transport concerns.

Runtime state lives beneath Git's common directory so linked worktrees consume one lock
authority.  The record still binds its creating worktree and HEAD: cross-worktree evidence
is visible rather than silently promoted to certification.  Tracked `.tdd-playbook/` is
reserved for policy/configuration, never ephemeral authority.
"""
import contextlib
import datetime
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import uuid

SCHEMA_VERSION = 1
STATE_DIRNAME = "tdd-playbook"
LOCK_FILENAME = "active-lock.json"
EVENTS_FILENAME = "events.jsonl"
PENDING_FILENAME = "pending-red.json"
TRANSACTION_FILENAME = "lock-transaction.lock"
ASSURANCE_LEVELS = (
    "unmeasured",
    "local_claim",
    "host_observed",
    "host_prevented",
    "ci_verified",
    "civerd_signed",
)
LOCAL_ASSURANCE_LEVELS = ASSURANCE_LEVELS[:4]
EVIDENCE_DECISIONS = ("allow", "block", "detect", "capture", "report", "unavailable")
EVIDENCE_DETAIL_KEYS = frozenset({
    "capability", "route", "outcome", "reason_code", "test_id", "redactions",
    "count", "control", "host_exit",
})

VERIFIER_BASENAMES = frozenset({
    "conftest.py", "pytest.ini", "tox.ini", "setup.cfg",
    "jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs",
    "vitest.config.js", "vitest.config.ts", "vitest.config.mts",
    "playwright.config.js", "playwright.config.ts", ".mocharc.yml",
    ".mocharc.json", "karma.conf.js",
})
LOCK_STATE_BASENAMES = frozenset({
    "active-lock.json", "events.jsonl", "tdd-lock.json",
    "tdd-lock-journal.jsonl", "tdd-pending-red.json", TRANSACTION_FILENAME,
})
GUARD_BASENAMES = frozenset({
    "test_lock_guard.py", "snapshot_guard.py", "test_weakening_guard.py",
    "flaky_guard.py", "overmock_guard.py", "red_lock.py", "_common.py",
    "hooks.json", "settings.json", "settings.local.json",
})


class ContractError(ValueError):
    """A malformed, mismatched, or unsafe host-contract value."""


def _git(start, *args):
    try:
        proc = subprocess.run(
            ["git", "-C", start, *args], capture_output=True, text=True,
            timeout=15, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ContractError("cannot resolve Git repository from {!r}: {}".format(start, exc))
    value = proc.stdout.strip()
    if not value:
        raise ContractError("Git returned an empty value for {}".format(" ".join(args)))
    return value


def _absolute_git_path(start, value):
    if os.path.isabs(value):
        return os.path.realpath(value)
    return os.path.realpath(os.path.join(start, value))


def resolve_repository(start=None):
    """Resolve the canonical repository/worktree identity used by every adapter."""
    origin = os.path.realpath(start or os.getcwd())
    root = os.path.realpath(_git(origin, "rev-parse", "--show-toplevel"))
    worktree_git_dir = os.path.realpath(_git(origin, "rev-parse", "--absolute-git-dir"))
    try:
        common_raw = _git(origin, "rev-parse", "--path-format=absolute", "--git-common-dir")
    except ContractError:
        common_raw = _git(origin, "rev-parse", "--git-common-dir")
    common_git_dir = _absolute_git_path(origin, common_raw)
    try:
        head = _git(origin, "rev-parse", "--verify", "HEAD")
    except ContractError:
        head = None
    repo_id = hashlib.sha256(common_git_dir.encode("utf-8")).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root,
        "common_git_dir": common_git_dir,
        "worktree_git_dir": worktree_git_dir,
        "worktree_id": hashlib.sha256(worktree_git_dir.encode("utf-8")).hexdigest(),
        "repo_id": repo_id,
        "head": head,
        "state_dir": os.path.join(common_git_dir, STATE_DIRNAME),
    }


def _require_identity(identity):
    needed = {"root", "common_git_dir", "worktree_git_dir", "worktree_id",
              "repo_id", "state_dir", "head"}
    if not isinstance(identity, dict) or not needed.issubset(identity):
        raise ContractError("incomplete repository identity")
    expected = os.path.join(os.path.realpath(identity["common_git_dir"]), STATE_DIRNAME)
    if os.path.realpath(identity["state_dir"]) != expected:
        raise ContractError("state directory does not belong to the Git common directory")


def normalize_target(identity, path):
    """Return a canonical repo-relative target, rejecting traversal and symlink escape."""
    _require_identity(identity)
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ContractError("target path must be a non-empty string")
    root = os.path.realpath(identity["root"])
    joined = path if os.path.isabs(path) else os.path.join(root, path)
    target = os.path.realpath(os.path.abspath(joined))
    try:
        inside = os.path.commonpath([root, target]) == root
    except ValueError:
        inside = False
    if not inside:
        raise ContractError("target escapes repository root: {!r}".format(path))
    rel = os.path.relpath(target, root)
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        raise ContractError("target escapes repository root: {!r}".format(path))
    return rel.replace(os.sep, "/")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def new_lock_record(identity, files, session_id, now=None):
    _require_identity(identity)
    if not isinstance(session_id, str) or not session_id.strip():
        raise ContractError("lock needs a non-empty session id")
    protected = {}
    for path in files:
        rel = normalize_target(identity, path)
        absolute = os.path.join(identity["root"], *rel.split("/"))
        if not os.path.isfile(absolute):
            raise ContractError("locked target is not a regular file: {}".format(rel))
        protected[rel] = _sha256(absolute)
    if not protected:
        raise ContractError("lock needs at least one file")
    return {
        "schema_version": SCHEMA_VERSION,
        "repo_id": identity["repo_id"],
        "common_git_dir": identity["common_git_dir"],
        "source_root": identity["root"],
        "source_worktree_git_dir": identity["worktree_git_dir"],
        "source_worktree_id": identity["worktree_id"],
        "head": identity["head"],
        "session_id": session_id.strip(),
        "lock_id": uuid.uuid4().hex,
        "generation": 1,
        "locked_at": now or _now(),
        "files": protected,
    }


def lock_path(identity):
    _require_identity(identity)
    return os.path.join(identity["state_dir"], LOCK_FILENAME)


def events_path(identity):
    _require_identity(identity)
    return os.path.join(identity["state_dir"], EVENTS_FILENAME)


def state_path(identity, filename):
    """Resolve a fixed core-owned state file without permitting caller path syntax."""
    _require_identity(identity)
    if filename not in (LOCK_FILENAME, EVENTS_FILENAME, PENDING_FILENAME):
        raise ContractError("unknown core state file: {!r}".format(filename))
    return os.path.join(identity["state_dir"], filename)


def read_state_json(identity, filename, default=None):
    path = state_path(identity, filename)
    try:
        with open(path) as fh:
            value = json.load(fh)
    except FileNotFoundError:
        return {} if default is None else default
    except (OSError, ValueError) as exc:
        raise ContractError("cannot read {}: {}".format(filename, exc))
    if not isinstance(value, dict):
        raise ContractError("{} must contain a JSON object".format(filename))
    return value


def write_state_json(identity, filename, value):
    if filename in (LOCK_FILENAME, EVENTS_FILENAME):
        raise ContractError("{} has a dedicated authority API".format(filename))
    if not isinstance(value, dict):
        raise ContractError("state value must be a JSON object")
    _atomic_json(state_path(identity, filename), value)


def _validate_lock(identity, record):
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported or missing lock schema_version")
    if record.get("repo_id") != identity["repo_id"]:
        raise ContractError("lock belongs to a different repository")
    if os.path.realpath(record.get("common_git_dir", "")) != \
            os.path.realpath(identity["common_git_dir"]):
        raise ContractError("lock common-dir identity mismatch")
    if not isinstance(record.get("files"), dict) or not record["files"]:
        raise ContractError("lock files must be a non-empty object")
    # One-release compatibility for canonical schema-1 records created before transaction
    # generations existed.  The next merge persists these deterministic defaults; this is
    # not a second authority or a permissive schema fallback.
    if "lock_id" not in record and record.get("session_id") and record.get("locked_at"):
        seed = "{}:{}:{}".format(
            record.get("repo_id"), record.get("session_id"), record.get("locked_at"))
        record["lock_id"] = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    if "generation" not in record:
        record["generation"] = 1
    for rel, digest in record["files"].items():
        normalized = normalize_target(identity, rel)
        if normalized != rel.replace(os.sep, "/"):
            raise ContractError("lock path is not canonical: {!r}".format(rel))
        if not isinstance(digest, str) or not digest:
            raise ContractError("lock digest is missing for {}".format(rel))
    for key in ("source_root", "source_worktree_git_dir", "source_worktree_id",
                "session_id", "lock_id", "locked_at"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise ContractError("lock is missing {}".format(key))
    if record.get("head") is not None and not isinstance(record.get("head"), str):
        raise ContractError("lock head must be a string or null")
    if not isinstance(record.get("generation"), int) or record["generation"] < 1:
        raise ContractError("lock generation must be a positive integer")
    return record


def _atomic_json(path, value):
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".lock-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(value, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_lock(identity, record):
    _validate_lock(identity, record)
    with _state_transaction(identity):
        _atomic_json(lock_path(identity), record)


def merge_lock(identity, fresh):
    """Create/extend the lock as one serialized transaction.

    A different session is a competing owner and is refused rather than merged or allowed
    to replace protections.  The same session can extend its protected set across commands.
    """
    _validate_lock(identity, fresh)
    with _state_transaction(identity):
        existing = _read_lock_unlocked(identity)
        if existing is not None and existing["session_id"] != fresh["session_id"]:
            raise ContractError(
                "competing active lock owned by session {!r}".format(existing["session_id"]))
        if existing is not None:
            protected = dict(existing["files"])
            protected.update(fresh["files"])
            fresh = dict(fresh)
            fresh["files"] = protected
            fresh["generation"] = existing["generation"] + 1
        _atomic_json(lock_path(identity), fresh)
        return fresh


def clear_lock(identity, expected_generation=None):
    """Remove the authority only if the caller did not race a newer lock mutation."""
    with _state_transaction(identity):
        existing = _read_lock_unlocked(identity)
        if existing is None:
            return False
        if expected_generation is not None and existing["generation"] != expected_generation:
            raise ContractError("active lock changed while unlock was in progress")
        os.remove(lock_path(identity))
        return True


def _read_lock_unlocked(identity):
    path = lock_path(identity)
    try:
        with open(path) as fh:
            record = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ContractError("cannot read canonical lock: {}".format(exc))
    return _validate_lock(identity, record)


def read_lock(identity):
    return _read_lock_unlocked(identity)


_THREAD_LOCKS = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock(path):
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(path, threading.Lock())


@contextlib.contextmanager
def _exclusive_file(fh):
    """Serialize appends across processes using only the standard library."""
    try:
        import fcntl
    except ImportError:  # pragma: no cover - Windows adapter CI exercises this branch
        import msvcrt
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        try:
            yield
        finally:
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _state_transaction(identity):
    """Serialize the complete lock read/validate/mutate critical section."""
    _require_identity(identity)
    os.makedirs(identity["state_dir"], mode=0o700, exist_ok=True)
    path = os.path.join(identity["state_dir"], TRANSACTION_FILENAME)
    with _thread_lock(path):
        with open(path, "a+") as fh:
            with _exclusive_file(fh):
                yield


def append_event(identity, event):
    _require_identity(identity)
    if not isinstance(event, dict) or event.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("event needs schema_version {}".format(SCHEMA_VERSION))
    path = events_path(identity)
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    line = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    with _thread_lock(path):
        with open(path, "a+") as fh:
            with _exclusive_file(fh):
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())


def read_events(identity):
    path = events_path(identity)
    try:
        with open(path) as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        raise ContractError("cannot read event journal: {}".format(exc))


def import_legacy_lock(identity, session_id):
    """Consume a Claude-era lock once; never maintain two active read authorities."""
    if read_lock(identity) is not None:
        return "already-canonical"
    legacy = os.path.join(identity["root"], ".claude", "tdd-lock.json")
    if not os.path.isfile(legacy):
        return "none"
    migrated = legacy + ".migrated"
    if os.path.exists(migrated):
        raise ContractError("legacy lock and migration marker both exist; refusing split-brain")
    try:
        with open(legacy) as fh:
            old = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ContractError("cannot import legacy lock: {}".format(exc))
    old_files = old.get("files") if isinstance(old, dict) else None
    if not isinstance(old_files, dict) or not old_files:
        raise ContractError("legacy lock has no files")
    files = {}
    for path, digest in old_files.items():
        rel = normalize_target(identity, path)
        if not isinstance(digest, str) or not digest:
            raise ContractError("legacy lock digest missing for {}".format(rel))
        files[rel] = digest
    record = {
        "schema_version": SCHEMA_VERSION,
        "repo_id": identity["repo_id"],
        "common_git_dir": identity["common_git_dir"],
        "source_root": identity["root"],
        "source_worktree_git_dir": identity["worktree_git_dir"],
        "source_worktree_id": identity["worktree_id"],
        "head": identity["head"],
        "session_id": session_id,
        "lock_id": uuid.uuid4().hex,
        "generation": 1,
        "locked_at": old.get("locked_at") or _now(),
        "files": files,
        "imported_from": ".claude/tdd-lock.json",
    }
    merge_lock(identity, record)
    os.replace(legacy, migrated)
    append_event(identity, {
        "schema_version": SCHEMA_VERSION,
        "event": "legacy_lock_imported",
        "repo_id": identity["repo_id"],
        "worktree_id": identity["worktree_id"],
        "session_id": session_id,
        "ts": _now(),
    })
    return "imported"


def lock_binding(identity, record):
    """Describe whether an active lock can be evidence for this exact worktree revision."""
    _validate_lock(identity, record)
    if record["head"] != identity["head"]:
        return "stale_revision"
    if not os.path.isdir(record["source_worktree_git_dir"]):
        return "source_worktree_missing"
    if record["source_worktree_id"] != identity["worktree_id"]:
        return "shared_from_other_worktree"
    return "current"


def _surface(rel, record):
    base = os.path.basename(rel)
    if rel in record["files"]:
        return "locked"
    if base in LOCK_STATE_BASENAMES:
        return "lockstate"
    if base in VERIFIER_BASENAMES:
        return "verifier"
    if base in GUARD_BASENAMES:
        return "guard"
    return None


def policy_decision(identity, record, action):
    """Evaluate a normalized action; host adapters decide how to enforce the result."""
    _validate_lock(identity, record)
    if not isinstance(action, dict) or action.get("kind") not in ("read", "write"):
        raise ContractError("action kind must be read|write")
    targets = action.get("targets")
    if not isinstance(targets, list):
        raise ContractError("action targets must be a list")
    result = {"schema_version": SCHEMA_VERSION, "decision": "allow", "surface": None,
              "target": None}
    if action["kind"] == "read":
        return result
    for target in targets:
        rel = normalize_target(identity, target)
        surface = _surface(rel, record)
        if surface:
            return {"schema_version": SCHEMA_VERSION, "decision": "block",
                    "surface": surface, "target": rel}
    return result


def release_authorizing(assurance):
    if assurance not in ASSURANCE_LEVELS:
        raise ContractError("unknown assurance level: {!r}".format(assurance))
    return assurance == "civerd_signed"


def new_local_evidence_event(identity, host, host_version, adapter_version, run_id,
                             event, decision, assurance, scope, details, now=None):
    """Build an allowlisted, explicitly forgeable local observation.

    CI and CIVerd assurance are intentionally impossible to mint through this API.  Their
    records need the independent producer/signature path, not a more persuasive local JSON
    field.  Raw commands, prompts, arguments, environment, and content are excluded by a
    closed details vocabulary so secrets do not enter the durable journal by default.
    """
    _require_identity(identity)
    strings = {"host": host, "host_version": host_version,
               "adapter_version": adapter_version, "run_id": run_id,
               "event": event, "scope": scope}
    if any(not isinstance(value, str) or not value.strip() for value in strings.values()):
        raise ContractError("evidence identity fields must be non-empty strings")
    if decision not in EVIDENCE_DECISIONS:
        raise ContractError("unknown evidence decision: {!r}".format(decision))
    if assurance not in LOCAL_ASSURANCE_LEVELS:
        raise ContractError("local evidence cannot mint assurance {!r}".format(assurance))
    if not isinstance(details, dict) or not set(details).issubset(EVIDENCE_DETAIL_KEYS):
        raise ContractError("evidence details contain non-allowlisted fields")
    if any(isinstance(value, (dict, list, tuple, set, bytes)) for value in details.values()):
        raise ContractError("evidence detail values must be scalar and redacted")
    timestamp = now or _now()
    try:
        datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ContractError("evidence timestamp must be ISO-8601")
    return {
        "schema_version": SCHEMA_VERSION,
        "host": host.strip(),
        "host_version": host_version.strip(),
        "adapter_version": adapter_version.strip(),
        "repo_id": identity["repo_id"],
        "worktree_id": identity["worktree_id"],
        "sha": identity["head"],
        "ts": timestamp,
        "run_id": run_id.strip(),
        "event": event.strip(),
        "decision": decision,
        "assurance": assurance,
        "scope": scope.strip(),
        "details": dict(details),
        "trust": "local_unverified",
    }


def record_capability_observation(identity, host, host_version, adapter_version, run_id,
                                  route, outcome):
    """Production adapter writer for paired, redacted local TEST-LOCK observations."""
    if outcome not in ("blocked", "allowed"):
        raise ContractError("capability outcome must be blocked|allowed")
    event = new_local_evidence_event(
        identity, host=host, host_version=host_version,
        adapter_version=adapter_version, run_id=run_id,
        event="capability_probe", decision="block" if outcome == "blocked" else "allow",
        assurance="host_prevented" if outcome == "blocked" else "host_observed",
        scope=route,
        details={"capability": "test-lock", "route": route, "outcome": outcome,
                 "control": outcome == "allowed", "redactions": 0})
    append_event(identity, event)
    return event
