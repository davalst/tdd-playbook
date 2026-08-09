#!/usr/bin/env python3
"""Plan (and, separately, perform) a reset of Playbook machine state.

Split like gate_plan.py / gate_runner.py: `plan()` is PURE — it stats and lists, it never
removes — and `apply()` is the only thing that deletes. Every test drives the planner, so the
dangerous half has one small surface.

SCOPES, and why `--shared` is not folded into `--repo`:
  repo      this worktree's vendored install + repo-local runtime exhaust
  shared    <git-common-dir>/tdd-playbook/**  — SHARED BY EVERY WORKTREE of the repo. A blast
            radius that wide has to be a scope the user typed, not one they inherited.
  machine   ~/.claude/deliberation/**         — real data, outside any repo
  plugin    ~/.claude/plugins/cache/*/tdd-playbook/<version>/ — user-scope, shared by every
            repo AND by live sessions. Stale-only by default: deleting the version the
            running session executes from darkens guards everywhere, silently (the H8 lesson).
  burn-evidence  docs/calibration/** + calibration/corpus/** — NEVER reachable from a
            combination of the others. Deleting these does not merely lose data: history.md
            and ledger.md are append-only and corpus/approved/ is byte-immutable under
            check_scoreboard_integrity, so removing them makes the repo permanently RED
            against every baseline.

THE HARD REFUSAL: linked worktrees. This repo carries five under `.claude/worktrees/`, one
locked and several on unpushed branches. Enumeration is an explicit ALLOWLIST derived from
what install wrote — never a glob over `.claude/` — and `is_protected_worktree` refuses any
path that is, contains, or sits inside a registered worktree.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                           timeout=30)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


def worktree_paths(root):
    """Every registered worktree of this repo, absolute and realpath'd."""
    out = []
    for line in _git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            out.append(os.path.realpath(line.split(" ", 1)[1].strip()))
    return out


def is_protected_worktree(root, path):
    """True if `path` is, contains, or lives inside a registered worktree other than root.

    Containment is checked in BOTH directions on purpose: deleting the worktree itself and
    deleting a parent that holds it are the same catastrophe."""
    p = os.path.realpath(path)
    main = os.path.realpath(root)
    for wt in worktree_paths(root):
        if wt == main:
            continue
        if p == wt or p.startswith(wt + os.sep) or wt.startswith(p + os.sep):
            return True
    return False


def is_plugin_source(root):
    """This repo is the canonical plugin SOURCE, not a vendored target — resetting it would
    be near-meaningless and it is where the worktrees live."""
    return os.path.isfile(os.path.join(root, "plugins", "tdd-playbook",
                                       ".claude-plugin", "plugin.json"))


def _identity(root):
    try:
        import host_contract
        return host_contract.resolve_repository(root)
    except Exception:
        return None


def _row(scope, kind, path, why):
    return {"scope": scope, "kind": kind, "path": path, "why": why}


def plan(root, scopes=("repo",), repo=None, force=False):
    """PURE. Returns a list of rows; removes nothing."""
    root = os.path.realpath(root)
    repo = repo or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    scopes = set(scopes)
    rows = []

    if "repo" in scopes:
        try:
            import vendoring
            rels = vendoring.installed_paths(repo, root, "claude")
        except Exception:
            rels = []
        for rel in rels:
            p = os.path.join(root, rel)
            if os.path.exists(p):
                rows.append(_row("repo", "file", p, "vendored by install"))
        for name in ("playbook-yield.jsonl", "playbook-guards-heartbeat",
                     "tdd-lock.json", "tdd-lock.json.migrated",
                     "tdd-lock-journal.jsonl", "tdd-pending-red.json",
                     ".tdd-playbook-version"):
            p = os.path.join(root, ".claude", name)
            if os.path.exists(p):
                rows.append(_row("repo", "file", p, "repo-local runtime exhaust"))

    if "shared" in scopes:
        ident = _identity(root)
        if ident:
            state = ident["state_dir"]
            sharers = [w for w in worktree_paths(root)]
            why = "SHARED BY {} WORKTREE(S)".format(len(sharers)) if len(sharers) > 1 \
                else "git common-dir state"
            for name in ("active-lock.json", "events.jsonl", "pending-red.json",
                         "lock-transaction.lock"):
                p = os.path.join(state, name)
                if os.path.exists(p):
                    rows.append(_row("shared", "file", p, why))
            gr = os.path.join(state, "gate-runs")
            if os.path.isdir(gr):
                rows.append(_row("shared", "dir", gr,
                                 "{} gate run(s) · {}".format(len(os.listdir(gr)), why)))

    if "machine" in scopes:
        store = os.environ.get("TDD_PLAYBOOK_DELIBERATION_DIR") or \
            os.path.join(os.path.expanduser("~"), ".claude", "deliberation")
        if os.path.isdir(store):
            rows.append(_row("machine", "dir", store,
                             "capture store — ALL REPOS, not just this one"))

    if "plugin" in scopes:
        cache = os.environ.get("TDD_PLAYBOOK_PLUGIN_CACHE") or \
            os.path.join(os.path.expanduser("~"), ".claude", "plugins", "cache")
        for mk in sorted(os.listdir(cache)) if os.path.isdir(cache) else []:
            base = os.path.join(cache, mk, "tdd-playbook")
            if not os.path.isdir(base):
                continue
            versions = sorted(os.listdir(base))
            # Keep BOTH the canonical version and the newest installed one: deleting the copy
            # the running session executes from darkens guards in every repo, silently.
            keep = set(versions[-1:])
            for v in versions:
                if v in keep and not force:
                    rows.append(_row("plugin", "keep", os.path.join(base, v),
                                     "newest installed — kept without --force"))
                else:
                    rows.append(_row("plugin", "dir", os.path.join(base, v),
                                     "stale plugin cache version"))

    if "burn-evidence" in scopes:
        for rel in ("docs/calibration", "calibration/corpus"):
            p = os.path.join(root, rel)
            if os.path.exists(p):
                rows.append(_row("burn-evidence", "dir", p,
                                 "EVIDENCE — append-only/immutable under "
                                 "check_scoreboard_integrity; removing it makes this repo "
                                 "permanently RED against every baseline"))

    # Hard refusals last, so they are visible next to what would have been removed.
    safe, refused = [], []
    for r in rows:
        if r["kind"] in ("file", "dir") and is_protected_worktree(root, r["path"]):
            refused.append(_row(r["scope"], "wtree", r["path"],
                                "LINKED WORKTREE — reset never touches these"))
        else:
            safe.append(r)
    if is_plugin_source(root) and not force and "repo" in scopes:
        refused.append(_row("repo", "refused", root,
                            "this is the canonical plugin SOURCE, not a vendored target — "
                            "--force to override"))
        safe = [r for r in safe if r["scope"] != "repo"]
    return safe + refused


def apply(rows, dry_run=True):
    """The ONLY thing here that deletes. `plan()` never does."""
    import shutil
    removed = []
    if dry_run:
        return removed
    for r in rows:
        if r["kind"] == "file" and os.path.exists(r["path"]):
            os.remove(r["path"])
            removed.append(r["path"])
        elif r["kind"] == "dir" and os.path.isdir(r["path"]):
            shutil.rmtree(r["path"])
            removed.append(r["path"])
    return removed
