"""Holdout controller — FETCH the private vault + VERIFY bodies through the EXISTING seams.

Part 2, 2026-08-15. The private vault (davalst/tdd-playbook-holdout) holds the answer-key
bodies that must never enter the public repo, its CI workspace, the child sandbox, host
transcript storage, logs, artifacts, or public summaries. This module is the FETCH + VERIFY
half of the controller; `confine.py` is the confinement half; `run_calibration.load_corpus`
(dirs=) is the one loader that picks the fetched bodies up via TDD_PLAYBOOK_HOLDOUT_DIR.

Two load-bearing refusals, each reusing an existing mechanism rather than adding a parallel one:

  1. CONTAINMENT — `clone_vault` refuses a dest inside the public working tree. A body under the
     tree could be committed, staged, or read by any Bash session in this repo (the local
     ~/.claude/projects transcript pile this session proved readable is exactly why an in-tree
     or in-home vault is unsafe). The vault clones to an EPHEMERAL temp dir the controller
     deletes after staging.

  2. HASH-DRIFT — `verify_bodies` delegates to `plant_forms.form_problems` (already a gate
     stage), feeding it the fetched bodies' computed shas. The holdout register lives in the
     PRIVATE vault and pins a real `content_sha256` per body, so a body whose content no longer
     matches its recorded sha REDs through the SAME checker a public corpus plant would — not a
     second, self-blocking checker (arch-F3). The public repo's `plant-forms.md` never names a
     holdout id (arch-F4 body containment), so the public gate's own form_problems run stays
     clean without any holdout entry to resolve.

`holdout_shas` hashes EXACTLY as `plant_forms.corpus_shas` does (bytes of the file, keyed by
the `id` inside the json) — one hashing definition, reused, so the drift check compares like
with like.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

import plant_forms


def _real(p):
    return os.path.realpath(p)


def repo_toplevel(start):
    """The git working-tree root containing `start`, or None if `start` is not in a repo.
    Used to derive the containment boundary the vault must clone OUTSIDE of."""
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def dest_is_inside_tree(dest, tree):
    """True if `dest` resolves to `tree` or a path within it. The containment-refusal predicate,
    factored out so it is unit-testable without a clone or a network."""
    if not tree:
        return False
    d, t = _real(dest), _real(tree)
    return d == t or d.startswith(t + os.sep)


def clone_vault(repo_url, dest, *, public_tree):
    """Shallow-clone the private vault to `dest`. REFUSES (ValueError, before any clone) if
    `dest` is inside `public_tree` — a holdout body there could be committed, staged, or read by
    any Bash session. Callers pass an ephemeral temp dir (tempfile.mkdtemp resolves outside the
    tree on macOS/Linux) and delete it after staging. Returns `dest`."""
    if dest_is_inside_tree(dest, public_tree):
        raise ValueError(
            "clone_vault refuses a dest inside the public working tree ({}): a holdout body "
            "there could be committed, staged, or read by any Bash session in this repo. Clone "
            "to an ephemeral temp dir outside the tree.".format(public_tree))
    subprocess.run(["git", "clone", "--depth", "1", repo_url, dest],
                   check=True, capture_output=True, text=True, timeout=120)
    return dest


def holdout_shas(bodies_dir):
    """{plant id: sha256 of its file} over the fetched bodies, hashed EXACTLY as
    plant_forms.corpus_shas does (bytes of the file, keyed by the `id` inside the json) so the
    map feeds plant_forms.form_problems as a drop-in for corpus_shas. A dir that does not exist
    yields {} (an unfetched / unarmed holdout resolves nothing)."""
    out = {}
    if not os.path.isdir(bodies_dir):
        return out
    for name in sorted(os.listdir(bodies_dir)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(bodies_dir, name)
        try:
            with open(p) as fh:
                pid = json.load(fh).get("id")
        except (OSError, ValueError):
            continue
        if pid:
            out[pid] = plant_forms.plant_sha(p)
    return out


def verify_bodies(entries, bodies_dir):
    """Hash-drift refusal through the EXISTING checker (arch-F3). Runs
    plant_forms.form_problems over the private holdout register `entries` with the fetched
    bodies' computed shas, so a body whose content drifts from its recorded content_sha256 REDs
    exactly as a tampered corpus plant would. `entries` come from the PRIVATE vault's register
    (parse_register), not the public plant-forms.md. Returns the problem list ([] == clean)."""
    return plant_forms.form_problems(entries, holdout_shas(bodies_dir))


# --- the opt-in run command (the one entrypoint that ties it together) ----------------------
HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_calibration.py")


def stage_vault(vault_url, workdir):
    """Clone the private vault into `workdir` (an ephemeral OUT-OF-TREE temp dir the caller
    deletes) and return its bodies dir. clone_vault refuses an in-tree dest."""
    dest = os.path.join(workdir, "vault")
    clone_vault(vault_url, dest, public_tree=repo_toplevel(HERE))
    return os.path.join(dest, "bodies")


def run_holdout(vault_url, extra_argv=(), *, runner=None):
    """The whole opt-in run, lightweight and manual (no schedule, no automation — the v1.32
    opt-in-and-reactive doctrine): clone the vault to an ephemeral out-of-tree dir, point the
    loader at its bodies, run the eval with the agent BOXED-IN (run_agent auto-confines while
    the bodies are on disk, and fails closed if confinement is unavailable), then delete the
    clone so no answer key outlives the run. Returns the eval's exit code. `runner` is injectable
    for tests; by default a real `run_calibration --form holdout` subprocess inherits the env."""
    workdir = tempfile.mkdtemp(prefix="tdd-holdout-")
    try:
        bodies = stage_vault(vault_url, workdir)
        env = dict(os.environ)
        env["TDD_PLAYBOOK_HOLDOUT_DIR"] = bodies
        argv = [sys.executable, RUNNER, "--form", "holdout", *extra_argv]
        if runner is not None:
            return runner(argv, env, bodies)
        return subprocess.run(argv, env=env).returncode
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Holdout controller — fetch the private vault and run the eval with the "
                    "agent boxed-in. Opt-in and manual; reach for it when you want a holdout "
                    "reading, like calibration itself.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="clone the vault, run a confined holdout eval, delete the clone")
    r.add_argument("--vault", required=True, help="git URL of the private holdout vault")
    r.add_argument("rest", nargs=argparse.REMAINDER,
                   help="extra args forwarded to run_calibration (e.g. --model opus --repeat 3)")
    args = ap.parse_args(argv)
    if args.cmd == "run":
        return run_holdout(args.vault, args.rest)
    return 2


if __name__ == "__main__":
    sys.exit(main())
