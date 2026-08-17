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

`holdout_shas` delegates to `plant_forms.shas_in_dir` — the SAME enumerator `corpus_shas` uses —
so the drift check compares like with like by construction (arch-F3), not by two copied loops.

CUSTODY LIMIT (decided 2026-08-15, stated rather than assumed). What the private vault DOES
protect: the answer key stays out of model TRAINING data (private repos are not crawled, so no
future model "knows" the plants from training), out of the EVALUATED agent's reach during a run
(the whole clone tree is read-denied and its location is stripped from the agent's env), and out
of the public repo/CI/downstream installs (the vault URL is a runtime argument, never baked in;
no body or holdout id ships publicly). What it does NOT protect: an everyday agent session
running with the OWNER's own GitHub credentials could `gh repo clone` the vault and read the
answers. No repo setting can prevent that — grading requires the key to be readable by something
the owner controls, and an actor holding that credential holds the key. The accepted position:
for a self-run measurement instrument, an agent acting as the owner cheating the owner's own
benchmark is self-defeating; the realistic failure is leakage into training or into an agent's
context, which the above DOES cover. Defense-in-depth against the owner's own agents (a separate
account/org, or a run-time-only token) was considered and deliberately not built — it is the
credential-custody bureaucracy this lean design set out to avoid. Revisit only if the vault ever
needs to defend against the owner's own tooling.
"""
import argparse
import json
import os
import re
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
    if public_tree is None:
        raise ValueError(
            "clone_vault cannot prove `dest` is outside a working tree (no git toplevel "
            "resolved) — refusing rather than risk an in-tree clone (security F5: the "
            "containment check must fail closed, not silently pass when it cannot decide).")
    if dest_is_inside_tree(dest, public_tree):
        raise ValueError(
            "clone_vault refuses a dest inside the public working tree ({}): a holdout body "
            "there could be committed, staged, or read by any Bash session in this repo. Clone "
            "to an ephemeral temp dir outside the tree.".format(public_tree))
    subprocess.run(["git", "clone", "--depth", "1", repo_url, dest],
                   check=True, capture_output=True, text=True, timeout=120)
    return dest


def holdout_shas(bodies_dir):
    """{plant id: sha256} over the fetched bodies — plant_forms.shas_in_dir, the SAME enumerator
    corpus_shas uses, so verify_bodies -> form_problems compares like with like by construction
    (arch-F3), not by two loops kept identical by hand. A missing dir yields {} (an unfetched /
    unarmed holdout resolves nothing)."""
    return plant_forms.shas_in_dir(bodies_dir)


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


REGISTER_NAME = "holdout-register.md"


def stage_vault(vault_url, workdir):
    """Clone the private vault into `workdir` (an ephemeral OUT-OF-TREE temp dir the caller
    deletes) and return the CLONE ROOT — which contains bodies/, the register, AND the .git
    object store (why the child is denied the whole root, F1). clone_vault refuses an in-tree
    dest."""
    dest = os.path.join(workdir, "vault")
    clone_vault(vault_url, dest, public_tree=repo_toplevel(HERE))
    return dest


# Bodies whose LATEST register row is dated on/after this must carry a validation manifest
# (the D1 gate shipped 2026-08-16; strictly-after grandfathers every body approved before
# the gate existed — their cleanup is the D4 remediation sweep's job, not a bricked run).
# Closing integration-adversary ISLAND1: without this, the persisted manifest had no reader
# and a hand-copied body + hand-written register row walked around the approve gate.
MANIFEST_REQUIRED_SINCE = "2026-08-17"


def write_body(path, sc):
    """THE one byte-form for a holdout body. `approve` canonicalizes the PROPOSED file through
    this BEFORE validating and lands the body through it too, so the bytes the verifier measured
    are byte-IDENTICAL to the bytes that land, and the manifest's candidate sha therefore matches
    the body it authorizes.

    Origin (2026-08-17, the day MANIFEST_REQUIRED_SINCE activated the reader that exposed it):
    approve computed the manifest sha on the proposed file, then re-dumped the body with
    indent=2. `cmd_author_holdout` already wrote proposed bodies in exactly this canonical form,
    so machine-authored bodies matched by luck of a duplicated literal — but the flow tells a
    human to REVIEW the file first, and any hand-authored or reformatted proposed body produced a
    manifest sha that could NEVER match its body. vault_integrity_problems then read every such
    vault as stale, and `holdout run` ABORTS on that, so one reformatted file bricked the whole
    vault. Two write sites agreeing to stay byte-identical is how they drift; one owner cannot
    (arch-F3, the shas_in_dir pattern).

    Canonicalizing the proposed file is a FORMATTING-only rewrite — `sc` is what was parsed from
    it — and it happens before validation, so a body that later fails the gate is left in
    proposed/ canonical rather than as-authored. That is intentional: re-proposing it validates
    the same bytes that would land."""
    with open(path, "w") as fh:
        json.dump(sc, fh, indent=2)
        fh.write("\n")


def vault_integrity_problems(vault_root):
    """Integrity of a vault BEFORE it feeds an eval: (1) HASH-DRIFT via verify_bodies (a body
    whose content no longer matches its recorded content_sha256), (2) an UNREGISTERED body —
    a bodies/*.json id with no register row (verify_bodies checks rows->shas, so an extra body
    would otherwise run untracked/unauthorized), and (3) post-gate CURRENT bodies must carry a
    validation manifest whose candidate sha matches the body — the D1 gate's proof-of-passage,
    so the gate cannot be bypassed by hand-copying. Returns the problem list ([] == clean). No
    register present -> None (a fresh vault with only bodies has nothing recorded to drift from;
    the caller decides — run_holdout refuses when bodies exist)."""
    reg = os.path.join(vault_root, REGISTER_NAME)
    bodies = os.path.join(vault_root, "bodies")
    if not os.path.isfile(reg):
        return None
    entries = plant_forms.parse_register(open(reg).read())
    problems = list(verify_bodies(entries, bodies))
    reg_ids = {e["plant_id"] for e in entries}
    shas = holdout_shas(bodies)
    for bid in shas:
        if bid not in reg_ids:
            problems.append("body '{}' is not in the register — an unregistered holdout body is "
                            "not authorized/verifiable".format(bid))
    for sid, e in plant_forms.resolve_latest(entries).items():
        if (e["date"] >= MANIFEST_REQUIRED_SINCE
                and (e.get("status") or "current") == "current" and sid in shas):
            mpath = os.path.join(vault_root, "manifests", sid + ".json")
            if not os.path.isfile(mpath):
                problems.append(
                    "body '{}' (registered {}) has NO validation manifest — post-gate "
                    "bodies land only through `holdout approve`, which persists one; a "
                    "hand-copied body is unvalidated".format(sid, e["date"]))
                continue
            try:
                msha = json.load(open(mpath)).get("candidate_content_sha256")
            except (OSError, ValueError):
                msha = None
            if msha != shas[sid]:
                problems.append(
                    "body '{}': its validation manifest does not match the body's content "
                    "sha — a stale manifest authorizes nothing; re-validate".format(sid))
    return problems


def cmd_integrity(vault_dir):
    """READ-ONLY operator check: is this vault fit to feed an eval? Nothing is written, no model
    is invoked, no clone is made — the same problem list `run` refuses on, printed on demand.

    Born 2026-08-17: vault_integrity_problems had no standalone reader. It ran only INSIDE
    run_holdout, so the only way to learn a vault was stale was to start a full eval and watch it
    abort — and the answer to "is my vault OK?" was a Python one-liner. A check an operator cannot
    run is a check that reports to nobody (§6a). Prints the remediation command per affected body
    rather than naming a problem and leaving the next step to be looked up (§4a)."""
    if not os.path.isdir(vault_dir):
        print("no such vault dir: {}".format(vault_dir))
        return 1
    problems = vault_integrity_problems(vault_dir)
    if problems is None:
        bodies = os.path.join(vault_dir, "bodies")
        n = len(holdout_shas(bodies)) if os.path.isdir(bodies) else 0
        print("vault has no register ({} body/bodies on disk) — nothing recorded to check. A "
              "fresh vault reads CLEAN here; `run` still refuses if bodies exist without a "
              "register.".format(n))
        return 0
    if not problems:
        # §12 — a result carries its SCOPE. Bodies dated before MANIFEST_REQUIRED_SINCE have their
        # manifest SKIPPED, not verified, so a flat "every one matches its manifest" is an
        # overclaim: the first real run of this command printed manifest assurance for 20 bodies
        # having checked 0 of them. Report the denominator, not the reassurance.
        shas = holdout_shas(os.path.join(vault_dir, "bodies"))
        latest = plant_forms.resolve_latest(plant_forms.parse_register(
            open(os.path.join(vault_dir, REGISTER_NAME)).read()))
        on_disk = [e for sid, e in latest.items() if sid in shas]
        checked = [e for e in on_disk
                   if e["date"] >= MANIFEST_REQUIRED_SINCE
                   and (e.get("status") or "current") == "current"]
        print("vault integrity: CLEAN — {n} registered body/bodies, every one matching its "
              "register sha. Validation manifests CHECKED for {k} of {n}.".format(
                  n=len(on_disk), k=len(checked)))
        if len(checked) < len(on_disk):
            print("  {} predate the {} manifest requirement and are grandfathered — their "
                  "manifests were NOT verified (cleanup is the remediation sweep's job, not a "
                  "bricked run).".format(len(on_disk) - len(checked), MANIFEST_REQUIRED_SINCE))
        return 0
    print("vault integrity: {} PROBLEM(S) — `holdout run` will refuse this vault.".format(
        len(problems)))
    for p in problems:
        print("  - " + p)
    ids = sorted({e["plant_id"] for e in plant_forms.parse_register(
        open(os.path.join(vault_dir, REGISTER_NAME)).read())
        if any(e["plant_id"] in p for p in problems)})
    if ids:
        print("\nTo fix, re-run the validation gate for the affected body/bodies (one at a time; "
              "this DOES invoke the verifier):")
        for sid in ids:
            print("  python3 holdout.py validate --vault-dir {} {}".format(vault_dir, sid))
    return 1


def contract_mismatch_warnings(vault_root, run_model, run_isolation="with-playbook"):
    """arch-F1/F6 (2026-08-16): a manifest's 'holds' predicts a reading only under the SAME
    contract. Compare each persisted manifest's recorded model/isolation against the run
    being launched; mismatches WARN (ids only — never blocked: the number still computes,
    it just doesn't carry the gate's prediction). run_model=None means the run will use
    the eval default (rc.DEFAULT_MODEL)."""
    import run_calibration as rc
    out = []
    run_model = run_model or rc.DEFAULT_MODEL
    mdir = os.path.join(vault_root, "manifests")
    if not os.path.isdir(mdir):
        return out
    for fn in sorted(os.listdir(mdir)):
        if not fn.endswith(".json"):
            continue
        try:
            m = json.load(open(os.path.join(mdir, fn)))
        except (OSError, ValueError):
            out.append("CONTRACT WARNING: manifest {} is unreadable".format(fn))
            continue
        c = m.get("contract") or {}
        if c.get("model") and c["model"] != run_model:
            out.append("CONTRACT MISMATCH {}: validated under model '{}' but this run "
                       "uses '{}' — its 'holds' does not predict this reading"
                       .format(m.get("candidate_id", fn), c["model"], run_model))
        if c.get("isolation") and c["isolation"] != run_isolation:
            out.append("CONTRACT MISMATCH {}: validated under isolation '{}' but this "
                       "run uses '{}'".format(m.get("candidate_id", fn), c["isolation"],
                                              run_isolation))
    return out


HISTORY = os.path.join(os.path.dirname(HERE), "docs", "calibration", "history.md")


def _filtered_run_lines(stdout):
    """The glance-able lines from a run: per-scenario headers + verdicts + the Calibration reading.
    Drops the rollup wall (gate_yield / ledger / suppressed-findings noise) so a --summary run is
    readable instead of a scroll."""
    keep = ("=== ", "PASS", "AMBER", "**BLOCKING", "BLOCKING FAIL", "INVALID", "Calibration:",
            "DIAGNOSE",  # DIAGNOSE + DIAGNOSE-SUMMARY: the read-only miss-triage (safe labels)
            "Corrected")  # D0: the status-partitioned reading, printed beside the legacy one
    return [ln for ln in (stdout or "").splitlines() if ln.startswith(keep)]


STALE_DAYS = 30  # the holdout is opt-in; past this with no run, surface it so it can't go dark


def holdout_staleness(history_text, today=None):
    """(days_since_last_holdout_run, is_stale) or None if no holdout run recorded. The 'date' that
    keeps the holdout from going dark: a run that never happens is a date that never advances, and
    both the summary and the regular calibration run read this to surface it."""
    import datetime
    import history_format as hf
    last = hf.latest_form_date(history_text, "holdout")
    if last is None:
        return None
    today = today or datetime.date.today()
    days = (today - last).days
    return days, days > STALE_DAYS


def holdout_summary_lines(history_text, today=None):
    """An HONEST one-glance reading from the calibration history: the latest holdout recall/FP with
    its Wilson interval, the latest dev recall for comparison, a conservative verdict, and a
    staleness line. With few plants the interval is wide and the comparison is explicitly withheld
    — a small-n gap is not a signal. Pure (takes the history text + optional today) so it is
    testable without a run."""
    import history_format as hf
    blocks, _ = hf.parse_run_blocks(history_text)
    lh = next((b for b in reversed(blocks) if b.get("form") == "holdout"), None)
    if not lh:
        return ["holdout: no holdout run recorded yet"]
    hk, hn = lh["recall"]
    fk, fn = lh["fp"]
    lines = ["Holdout reading: recall {}/{} {} · FP {}/{} {}".format(
        hk, hn, hf.interval_cell(hk, hn), fk, fn, hf.interval_cell(fk, fn))]
    corr = lh.get("corrected")
    if corr:
        ck, cn = corr["recall"]
        gk, gn = corr["fp"]
        lines.append("Corrected reading (superseded bodies excluded — the trustworthy "
                     "number): recall {}/{} {} · FP {}/{} {}".format(
                         ck, cn, hf.interval_cell(ck, cn), gk, gn, hf.interval_cell(gk, gn)))
    snap = lh.get("population_snapshot")
    if snap:
        counts = {}
        for st_, _sha in snap.values():
            counts[st_] = counts.get(st_, 0) + 1
        lines.append("Population as-of-run: " + " · ".join(
            "{} {}".format(v, k) for k, v in sorted(counts.items())))
    stale = holdout_staleness(history_text, today)
    if stale is not None:
        days, is_stale = stale
        lines.append("Last run: {} day(s) ago{}".format(
            days, "  -> STALE (> {}d): re-run or grow the corpus".format(STALE_DAYS)
            if is_stale else ""))
    if corr:
        # the comparison below reads the TRUSTWORTHY number — a retired body must not
        # depress (or inflate) the dev-vs-holdout gap it is no longer part of
        hk, hn = corr["recall"]
    ld = next((b for b in reversed(blocks) if b.get("form") == "dev"), None)
    if ld:
        dk, dn = ld["recall"]
        lines.append("Dev (latest):    recall {}/{} {}".format(dk, dn, hf.interval_cell(dk, dn)))
        if hn < 8:
            lines.append("-> n={} is too small to compare to dev; author more holdout plants to "
                         "tighten the interval before reading into any gap.".format(hn))
        else:
            hr = hk / hn if hn else 0.0
            dr = dk / dn if dn else 0.0
            if hr + 0.15 < dr:
                lines.append("-> WATCH: holdout recall ({:.0%}) is well below dev ({:.0%}) — the "
                             "verifiers may be overfitting the public corpus.".format(hr, dr))
            else:
                lines.append("-> OK: holdout recall is in line with dev.")
    return lines


def run_holdout(vault_url, extra_argv=(), *, runner=None, summary=False):
    """The whole opt-in run, lightweight and manual (no schedule, no automation — the v1.32
    opt-in-and-reactive doctrine): clone the vault to an ephemeral out-of-tree dir, VERIFY its
    integrity (drift + unregistered bodies), point the loader at its bodies, run the eval with the
    agent BOXED-IN (run_agent auto-confines while the bodies are on disk, fails closed if
    confinement is unavailable), then delete the clone so no answer key outlives the run. Returns
    the eval's exit code. `summary` collapses the rollup wall to the verdicts + reading + a
    dev-vs-holdout comparison. `runner` is injectable for tests."""
    # SECURITY (adversary finding 1, 2026-08-16): the egress muzzle is derived from
    # `--form holdout` in the child, and argparse takes the LAST --form — so a forwarded
    # `--form all` would run the private bodies through the DEV printer, which emits the
    # plant text, both oracle regexes, and the raw doer output. The muzzle is not
    # user-negotiable on this path: refuse the override instead of silently un-muzzling.
    if "--form" in extra_argv:
        raise ValueError(
            "run_holdout refuses a forwarded --form: the holdout egress allow-list is "
            "derived from `--form holdout`, and overriding it would print the private "
            "answer key (plant text + oracle regexes + raw output) through the dev "
            "printer. Run the public corpus with run_calibration.py directly instead.")
    workdir = tempfile.mkdtemp(prefix="tdd-holdout-")
    try:
        dest = stage_vault(vault_url, workdir)
        bodies = os.path.join(dest, "bodies")
        probs = vault_integrity_problems(dest)
        if probs is None and holdout_shas(bodies):
            # fail-open one layer above a fail-closed check (arch lead, 2026-08-16): a
            # register-less vault would run every body unauthorized and implicitly
            # `current` — the silent re-entry the scorer's own FATAL refuses.
            raise ValueError("holdout vault has bodies but NO register ({}) — refusing: "
                             "every body would run unauthorized with an implicit "
                             "'current' status.".format(REGISTER_NAME))
        if probs:
            raise ValueError("holdout vault FAILED its integrity check — refusing to run "
                             "(drift or unregistered body):\n  " + "\n  ".join(probs))
        # arch-F1/F6: 'holds' predicts THIS reading only under the same contract — warn
        # loudly (stderr, ids only) when a manifest was validated under a different
        # model/isolation than the run being launched.
        run_model = (extra_argv[extra_argv.index("--model") + 1]
                     if "--model" in extra_argv else None)
        for w in contract_mismatch_warnings(dest, run_model):
            print(w, file=sys.stderr)
        env = dict(os.environ)
        env["TDD_PLAYBOOK_HOLDOUT_DIR"] = bodies       # loader (trusted parent) reads bodies
        reg = os.path.join(dest, REGISTER_NAME)
        if os.path.isfile(reg):
            # D0: the register (status column) flows to the scorer through the TRUSTED
            # PARENT only — run_calibration parses it once; child_env strips it from the
            # nested model, like the DIR/DENY pair.
            env["TDD_PLAYBOOK_HOLDOUT_REGISTER"] = reg
        env["TDD_PLAYBOOK_HOLDOUT_DENY"] = workdir      # child is denied the WHOLE clone tree
        # (F1) — workdir contains vault/, which contains BOTH bodies/ and the .git object store
        # that `git show HEAD:bodies/*.json` would otherwise reconstruct the answer key from.
        argv = [sys.executable, RUNNER, "--form", "holdout", *extra_argv]
        if runner is not None:
            return runner(argv, env, bodies)
        if summary:
            proc = subprocess.run(argv, env=env, capture_output=True, text=True)
            for ln in _filtered_run_lines(proc.stdout):
                print(ln)
            try:
                print("")
                for ln in holdout_summary_lines(open(HISTORY).read()):
                    print(ln)
            except OSError:
                pass
            if "--diagnose" not in extra_argv:  # GAP3: point a user who sees a miss at the triage
                print("\nTip: `holdout diagnose --vault <url>` classifies each miss "
                      "(would-pass-normalized — a brittle-scorer artifact — vs a genuine wrong "
                      "verdict), emitting safe labels only.")
            return proc.returncode
        return subprocess.run(argv, env=env).returncode
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# --- D1: the deterministically-SCORED validation gate (trustworthy-holdout-controls) --------
# WHY: `holdout diagnose` (v1.38.0) proved the FP number was measuring CONTROL-AUTHORING
# quality, not verifier quality — controls were approved without ever running a verifier
# against them. The gate closes that: before a body lands, its TARGET verifier runs against
# it under the SAME execution contract the eval uses. The verifier is an LLM; the SCORING is
# deterministic (rc.oracle) — the gate is not "LLM-free", it is deterministically scored.
# Fail-closed: HOLDS/caught only at k/k; a real split is `unstable`, n==0 `inconclusive`,
# and every non-approvable verdict refuses the landing.

APPROVABLE = ("holds", "caught")


# file hashing: plant_forms.plant_sha is THE raw-file sha256 (arch-F9 — the TOCTOU check
# compares hashes across call sites, so two implementations staying accidentally equal is
# not a foundation; one helper is).

def fixture_tree_sha():
    """Content hash of the staged fixture world (same filter stage() copies with), so the
    manifest pins WHAT the verifier was shown, not just which scenario name ran."""
    import hashlib
    import run_calibration as rc
    h = hashlib.sha256()
    for root, dirs, files in os.walk(rc.FIXTURE):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for fn in sorted(files):
            if fn.endswith((".pyc", ".pyo")):
                continue
            p = os.path.join(root, fn)
            h.update(os.path.relpath(p, rc.FIXTURE).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def host_binary_identity(host_bin):
    """What binary would actually run: its self-reported version + resolved path. Cheap,
    structured, and honest — `unknown` when the binary won't answer, never a guess."""
    path = shutil.which(host_bin) or host_bin
    try:
        p = subprocess.run([host_bin, "--version"], capture_output=True, text=True,
                           timeout=30)
        first = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        ver = first[0][:120] if first else "unknown"
    except Exception:
        ver = "unknown"
    return "{} @ {}".format(ver, path)


def eval_contract(sc, model, *, host="claude", host_bin="claude",
                  isolation="with-playbook", repeat=None, host_identity=None):
    """The FULL execution contract a validation runs under. It MUST equal the eval's
    contract or "holds" doesn't predict the reading — so every axis the eval varies is
    RECORDED here (a mismatch is auditable, never silent). STRUCTURED-ONLY by construction:
    hashes and labels, no fixture text, no oracle regexes."""
    import run_calibration as rc
    return {
        "agent": sc["agent"], "model": model, "host": host,
        "host_binary_identity": (host_identity if host_identity is not None
                                 else host_binary_identity(host_bin)),
        "isolation": isolation,
        "max_turns": rc.turns_for(sc),
        "repeat": int(repeat or rc.DEFAULT_REPEAT),
        "calibration_args": os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", ""),
        "fixture_sha256": fixture_tree_sha(),
        "runner_source_sha256": plant_forms.plant_sha(os.path.join(HERE, "host_runner.py")),
        "oracle_source_sha256": plant_forms.plant_sha(RUNNER),
        "oracle_normalization_version": rc.ORACLE_NORMALIZATION_VERSION,
        "verifier_brief_sha256": plant_forms.plant_sha(os.path.join(
            os.path.dirname(HERE), "plugins", "tdd-playbook", "agents",
            sc["agent"] + ".md")),
    }


def validation_verdict(k, n, is_control):
    """Map rc.verdict_for's closed vocabulary onto the validation decision (ONE seam, no
    second promotion rule): k/k -> holds/caught · a real split -> unstable · 0/n ->
    fails/missed · n==0 -> inconclusive. Only holds/caught are approvable."""
    import run_calibration as rc
    v = rc.verdict_for("_validation", k, n, last=None)
    if v == "PASS":
        return "holds" if is_control else "caught"
    if v.startswith("INVALID"):
        return "inconclusive"
    if v.startswith("**BLOCKING"):
        return "fails" if is_control else "missed"
    return "unstable"


def validate_item(sc, vault_dir, contract, *, runner=None, body_path=None,
                  host_bin="claude"):
    """Run the item's TARGET verifier against it under `contract`, deterministically scored.
    Returns {"table", "manifest", "reasoning"}:
      table    — the k/n decision table (the ONLY thing a caller may print);
      manifest — STRUCTURED-ONLY audit record (hashes, labels, rep outcomes — no raw
                 output, no oracle regexes), hash-bound to the candidate content;
      reasoning — the worst failing rep's raw verifier output, held IN MEMORY for the D2
                 judge and then dropped. Callers must never print or persist it.
    The spawn is confined away from the vault (TDD_PLAYBOOK_HOLDOUT_DENY=vault_dir) for the
    duration and the env is restored after. `runner(sc) -> (status, out)` is injectable."""
    import datetime as _dt
    import run_calibration as rc
    is_control = bool(sc.get("control_for"))
    clean = {kk: vv for kk, vv in sc.items() if kk != "_meta"}
    keep_deny = os.environ.get(rc.HOLDOUT_DENY_ENV)
    os.environ[rc.HOLDOUT_DENY_ENV] = vault_dir
    try:
        # ONE rep loop, shared with the eval (rc.run_reps, arch-F2) — the gate predicts
        # the reading only if both run the same rep semantics.
        full_reps = rc.run_reps(clean, contract["repeat"], host_bin, contract["model"],
                                contract["host"], isolation=contract["isolation"],
                                runner=runner)
    finally:
        if keep_deny is None:
            os.environ.pop(rc.HOLDOUT_DENY_ENV, None)
        else:
            os.environ[rc.HOLDOUT_DENY_ENV] = keep_deny
    reasoning = next((r["out"] for r in full_reps
                      if not r["passed"] and not r["env"] and r["out"]), None)
    # manifest reps are STRUCTURED-ONLY: strip the problems (they quote oracle regexes)
    # and the raw output before anything leaves this function besides `reasoning`.
    reps = [{"passed": r["passed"], "mode": r["mode"], "env": r["env"]}
            for r in full_reps]
    k, n = rc.rep_counts(full_reps)
    verdict = validation_verdict(k, n, is_control)
    if body_path:
        cand_sha = plant_forms.plant_sha(body_path)
    else:
        import hashlib
        cand_sha = hashlib.sha256(
            json.dumps(clean, sort_keys=True).encode()).hexdigest()
    table = {"id": sc["id"], "kind": "control" if is_control else "plant",
             "k": k, "n": n, "invalid": len(reps) - n, "verdict": verdict,
             "approvable": verdict in APPROVABLE}
    manifest = {"schema": 1, "candidate_id": sc["id"],
                "candidate_content_sha256": cand_sha,
                "kind": table["kind"], "k": k, "n": n, "verdict": verdict,
                "reps": reps, "contract": contract,
                "validated_at": _dt.datetime.now().isoformat(timespec="seconds")}
    return {"table": table, "manifest": manifest, "reasoning": reasoning}


def manifest_sha(manifest):
    """The hash a human confirmation (D2) is bound to — canonical-JSON sha256, so a
    confirmation can never be replayed for a different item or a re-edited body."""
    import hashlib
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()


def print_validation_table(table):
    """THE one stdout emission for a validation — allow-list shape (id · kind · k/n ·
    invalid · verdict), the same egress class as scenario_header. Nothing else prints."""
    print("VALIDATE {} | {} | {}/{} reps passed | invalid {} | {}".format(
        table["id"], table["kind"], table["k"], table["n"], table["invalid"],
        table["verdict"].upper()))


# --- D2: the control-quality judge — ADVISORY, k/k, human-confirmed -------------------------
# The judge exists so David never reads code: it explains WHY a flagged control is suspect
# and RECOMMENDS one of three actions defined by the motivating shapes (holdout diagnose,
# 2026-08-16 — FP 10/10 measured control-authoring quality, not verifier quality):
#   REJECT      — the control is NOT actually clean w.r.t. its own task's question;
#   FIX-ORACLE  — the code is clean but the oracle is unfair (a greedy prose regex a
#                 correct explanation trips; anchor oracles on the verdict line);
#   KEEP        — control clean AND oracle fair: the verifier genuinely over-flags — a
#                 real, tracked weakness (-> known-overflag, counted, never hidden).
# The judge NEVER mutates the corpus. Custody (ONE model): it must read the oracle to judge
# it — authoring-time exposure, the same class as the adversary AUTHOR — distinct from the
# tighter eval-time containment. Only structured labels+hashes persist; the free-text
# rationale is shown transiently for the y/n and never durably persisted.

JUDGE_AGENT = "control-quality-adversary"
_JUDGE_VERDICT = re.compile(r"Control-Verdict:\s*(REJECT|FIX-ORACLE|KEEP)", re.IGNORECASE)


def parse_judge_verdict(text):
    """The FORCED closed-vocabulary line, or None. Free prose never becomes a verdict."""
    m = _JUDGE_VERDICT.search(text or "")
    return m.group(1).upper() if m else None


def judge_payload(sc, reasoning):
    """What the judge reads: the control (edits/task/oracle) + the verifier's reasoning.
    It cannot judge fairness blind — this IS the accepted authoring-time exposure."""
    return json.dumps(
        {"control": {k: sc.get(k) for k in
                     ("id", "agent", "control_for", "plant", "edits", "task",
                      "must_match", "must_not_match") if k in sc},
         "verifier_reasoning": reasoning},
        indent=2)


def judge_control(sc, reasoning, *, model="opus", host="claude", claude_bin="claude",
                  k=3, invoke=None, deny_read=None):
    """Run the judge k times; require k/k agreement on the forced verdict — any split or
    unparseable vote is INCONCLUSIVE (no auto-action; §5a oracle-split: an LLM verdict is
    advisory, never the silent authority on an irreversible change). Returns
    {"verdict", "votes", "rationale"} — rationale is the last parseable output, held for
    TRANSIENT display only. `invoke(prompt) -> text` is injectable."""
    import run_calibration as rc
    import host_runner
    from child_env import child_env
    prompt = (rc.agent_body(JUDGE_AGENT)
              + "\n\n# ITEM UNDER JUDGMENT (JSON)\n" + judge_payload(sc, reasoning))
    votes, rationale = [], None
    for _ in range(int(k)):
        if invoke is not None:
            out = invoke(prompt)
        else:
            # SECURITY (adversary finding 2, 2026-08-16): the sandbox re-grants writes to
            # its WORKSPACE (the cwd). The judge is the one model holding approved bodies
            # + oracle regexes in context, so its workspace must be a throwaway temp dir —
            # never HERE, which is the public repo that gets committed and pushed.
            jroot = tempfile.mkdtemp(prefix="tdd-judge-")
            try:
                res = host_runner.invoke(
                    host, claude_bin, prompt, model, jroot, timeout=600, env=child_env(),
                    extra_args=os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", "").split(),
                    confine_deny_read=deny_read)
                out = res.output if res.status == "ok" else ""
            except Exception:
                out = ""
            finally:
                shutil.rmtree(jroot, ignore_errors=True)
        v = parse_judge_verdict(out or "")
        votes.append(v)
        if v is not None:
            rationale = out
    agreed = votes and votes[0] is not None and all(v == votes[0] for v in votes)
    return {"verdict": votes[0] if agreed else "INCONCLUSIVE", "votes": votes,
            "rationale": rationale}


def confirm_disposition(action, msha, *, interactive=None, input_fn=None):
    """The human-confirm half of an irreversible disposition. True ONLY on an explicit
    interactive 'y'; non-interactive / no TTY -> ABORT, never auto-proceed. The prompt is
    BOUND to the manifest content-hash, so a confirmation cannot be replayed for a
    different item or a re-edited body."""
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        print("ABORT: '{}' is irreversible and needs an interactive y/n bound to manifest "
              "{} — re-run in a terminal. Nothing was changed.".format(action, msha[:12]))
        return False
    ans = (input_fn or input)("{} — confirm [manifest {}] y/n: ".format(action, msha[:12]))
    return (ans or "").strip().lower() == "y"


def cmd_validate_holdout(vault_dir, plant_id, model, claude_bin, repeat):
    """Read-only: validate a proposed OR approved body against its target verifier and
    print the decision table. Moves nothing, writes nothing."""
    _refuse_in_tree(vault_dir)
    for sub in ("proposed", "bodies"):
        path = os.path.join(vault_dir, sub, plant_id + ".json")
        if os.path.isfile(path):
            break
    else:
        print("no holdout body: {}".format(plant_id))
        return 1
    with open(path) as fh:
        sc = json.load(fh)
    contract = eval_contract(sc, model, host_bin=claude_bin, repeat=repeat)
    res = validate_item(sc, vault_dir, contract, body_path=path, host_bin=claude_bin)
    print_validation_table(res["table"])
    return 0 if res["table"]["approvable"] else 1


# --- authoring into the private vault (adversary model -> proposed/ -> approved bodies/) --------
def _refuse_in_tree(vault_dir):
    """A local vault checkout must live OUTSIDE the public working tree — a holdout body committed
    into the public repo would defeat the whole boundary. Fail-closed (also when the tree can't
    be resolved)."""
    tree = repo_toplevel(HERE)
    if tree is None:
        raise ValueError("cannot resolve the public working tree to prove the vault-dir is "
                         "outside it — refusing (fail closed)")
    if dest_is_inside_tree(vault_dir, tree):
        raise ValueError("refusing a vault-dir inside the public working tree ({}): a holdout "
                         "body there could be committed to the public repo".format(tree))


def _vault_universe(vault_dir):
    """Existing scenarios for id-uniqueness + pairing: public shipped + public corpus + this
    vault's proposed/ + bodies/. ONE loader (rc.load_corpus) with extended paths — never a second
    membership check (arch-F1)."""
    import run_calibration as rc
    import author_plants as ap
    return (rc.load_scenarios() + ap.corpus_scenarios(("proposed", "approved"))
            + rc.load_corpus([os.path.join(vault_dir, "proposed"),
                              os.path.join(vault_dir, "bodies")]))


def cmd_author_holdout(vault_dir, model, category, claude_bin):
    """Generate FRESH holdout plant+control pairs with the adversary model and stage them in the
    vault's proposed/ for human review. The generated plants ARE the answer key, so nothing but
    ids reaches stdout (generate_accepted_pairs returns no raw output; rejections are id+category)
    and nothing holdout enters the public repo (proposed/ lives in the out-of-tree vault clone)."""
    import datetime as _dt
    import author_plants as ap
    _refuse_in_tree(vault_dir)
    proposed = os.path.join(vault_dir, "proposed")
    os.makedirs(proposed, exist_ok=True)
    prompt = ap.adversary_prompt(category)
    known = _vault_universe(vault_dir)
    # Defense in depth (security review, 2026-08-15): on any cycle after the first, the vault's
    # bodies/ holds already-approved holdout answers ON DISK. The adversary runs in HERE (the
    # public repo) and is NEVER handed the vault path (it reaches neither child_env, host_runner,
    # nor the prompt — grep-confirmed), so it cannot reach those bodies; owner-level crawling is
    # out of scope (custody note). Still, where a sandbox exists, box the adversary away from the
    # vault — belt-and-suspenders. NEVER fail authoring for lack of a sandbox (it is host-portable
    # and generates, not reads, the key).
    deny = None
    bodies_dir = os.path.join(vault_dir, "bodies")
    if os.path.isdir(bodies_dir) and any(f.endswith(".json") for f in os.listdir(bodies_dir)):
        import confine
        if confine.sandbox_exec_available():
            deny = [vault_dir]
    try:
        res = ap.generate_accepted_pairs(prompt, "claude", claude_bin, model, known,
                                         deny_read=deny)
    except FileNotFoundError:
        print("FATAL: claude binary not found ({})".format(claude_bin))
        return 2
    if res["parse_failed"]:
        print("REJECTED: no parseable JSON array in adversary output")   # NO raw output printed
        return 1
    for cid, reason in res["rejected"]:
        print("REJECTED {}: {}".format(cid, reason))   # id + category only, never an oracle echo
    accepted = 0
    for sc in res["accepted"]:
        sc["_meta"] = {"authored_by_model": model, "authored_at": _dt.date.today().isoformat(),
                       "status": "proposed", "form": "holdout"}
        write_body(os.path.join(proposed, sc["id"] + ".json"), sc)
        accepted += 1
        print("PROPOSED {} (review the file, then: holdout approve --vault-dir {} {} --reason "
              "...)".format(sc["id"], vault_dir, sc["id"]))
    print("holdout author: {} proposed to {} · {} rejected".format(
        accepted, proposed, len(res["rejected"])))
    return 0 if accepted else 1


def cmd_approve_holdout(vault_dir, plant_id, reason, *, model=None, claude_bin="claude",
                        repeat=None, validator=None, judge=None, supersedes="",
                        interactive=None, today=None):
    """Move a reviewed proposed body into bodies/ and record it in the register (form=holdout,
    real content_sha256). Re-validates (minus dup-id, the proposed file IS the id), echoes
    pairing, and — D1 — runs the body's TARGET VERIFIER against it under the eval contract:
    only holds/caught at k/k lands; unstable/fails/missed/inconclusive REFUSE (fail closed;
    the proposed suspect stays in proposed/ for re-authoring — a never-landed body is
    DISCARDED or re-authored, never "retired"). The structured manifest persists beside the
    register; the verifier's raw reasoning stays in memory and is never printed. Only a
    COUNT of schema problems is printed (never the strings, which can echo oracle regexes).
    `validator` is injectable for tests; the default is validate_item (the real gate)."""
    import datetime as _dt
    import run_calibration as rc
    _refuse_in_tree(vault_dir)
    if not reason:
        print("refusing: an assignment with no reason is not auditable (--reason required)")
        return 1
    src = os.path.join(vault_dir, "proposed", plant_id + ".json")
    if not os.path.isfile(src):
        print("no proposed holdout body: {}".format(plant_id))
        return 1
    if supersedes and supersedes not in _latest_register_rows(vault_dir):
        # integration-adversary NOTE6 (2026-08-16): a typo'd link would otherwise land
        # silently and hard-fail the NEXT `holdout run` for the whole vault (the dangling-
        # link check lives in vault_integrity_problems) — refuse one keystroke instead.
        print("REFUSING approval — --supersedes '{}' names no register entry (a dangling "
              "supersession link would brick the next run).".format(supersedes))
        return 1
    with open(src) as fh:
        sc = json.load(fh)
    # Canonicalize the proposed bytes BEFORE anything measures them, so the sha the verifier
    # records in its manifest is the sha the landed body will carry (see write_body).
    write_body(src, sc)
    universe = _vault_universe(vault_dir)
    existing = {s["id"] for s in universe if s["id"] != plant_id}
    probs = rc.validate_scenario({k: v for k, v in sc.items() if k != "_meta"}, existing)
    if probs:
        print("REFUSING approval — the body no longer validates ({} problem(s))".format(len(probs)))
        return 1
    for p in rc.pairing_problems(universe):
        if p.startswith(plant_id + ":"):
            print("pairing note: " + p)   # echo (ids only); its control may still be in proposed/
    # D1 — the validation gate: the verifier must actually be run against the body before
    # it can land. Deterministically scored; fail closed on anything but k/k.
    # arch-F1: ONE model default, the eval's own (rc.DEFAULT_MODEL) — a second literal
    # here once meant the default path validated under a model the reading never uses.
    model = model or rc.DEFAULT_MODEL
    contract = eval_contract(sc, model, host_bin=claude_bin, repeat=repeat)
    if validator is None:
        def validator(s, vd, c, **kw):
            return validate_item(s, vd, c, host_bin=claude_bin, **kw)
    res = validator(sc, vault_dir, contract, body_path=src)
    print_validation_table(res["table"])
    if not res["table"]["approvable"]:
        print("REFUSING approval — validation verdict '{}' (only k/k lands; a mixed or "
              "unmeasured run never does). The body stays in proposed/ — fix it and "
              "re-propose, or discard it. Run `holdout validate --vault-dir {} {}` to "
              "re-check.".format(res["table"]["verdict"], vault_dir, plant_id))
        # D2 — hand the in-memory reasoning to the ADVISORY judge so the operator learns
        # WHY without reading code. Transient display only; a judge failure never masks
        # the refusal (the deterministic block above needs no confirmation — nothing
        # irreversible happened, the body simply did not land).
        # SECURITY (adversary finding 3, 2026-08-16): the rationale quotes the oracle, and
        # "transient" is only true on a TTY — a non-interactive invocation (CI, an agent's
        # Bash tool, `| tee`) would write it into a durable log/transcript. Same rule as
        # remediate: no TTY, no judge; the deterministic refusal stands on its own.
        if interactive is None:
            interactive = sys.stdin.isatty()
        if not interactive and judge is not False:
            print("(judge skipped: non-interactive — its rationale quotes the oracle and "
                  "must not land in a log. Re-run `holdout approve` in a terminal, or "
                  "`holdout validate` for the table alone.)")
        elif res.get("reasoning") and judge is not False:
            try:
                jr = (judge or judge_control)(sc, res["reasoning"],
                                              deny_read=[vault_dir])
                print("JUDGE (advisory): {} — votes {}".format(
                    jr["verdict"], "/".join(str(v) for v in jr["votes"])))
                if jr.get("rationale"):
                    print("--- judge rationale (transient — not persisted) ---")
                    print(jr["rationale"].strip()[:2000])
            except Exception as e:
                print("(judge unavailable: {} — the refusal above stands on the "
                      "deterministic score alone)".format(e))
        return 1
    # TOCTOU: the body on disk must still be the exact bytes validation measured.
    if plant_forms.plant_sha(src) != res["manifest"]["candidate_content_sha256"]:
        print("REFUSING approval — the body changed after validation (content sha "
              "mismatch). Re-validate the current bytes.")
        return 1
    manifests = os.path.join(vault_dir, "manifests")
    os.makedirs(manifests, exist_ok=True)
    with open(os.path.join(manifests, plant_id + ".json"), "w") as fh:
        json.dump(res["manifest"], fh, indent=2, sort_keys=True)
        fh.write("\n")
    bodies = os.path.join(vault_dir, "bodies")
    os.makedirs(bodies, exist_ok=True)
    dst = os.path.join(bodies, plant_id + ".json")
    write_body(dst, sc)
    os.remove(src)
    sha = plant_forms.plant_sha(dst)
    reg = os.path.join(vault_dir, REGISTER_NAME)
    new = not os.path.isfile(reg)
    with open(reg, "a") as fh:
        if new:
            fh.write("# Holdout register\n\n" + plant_forms.ENTRIES_SECTION + "\n\n"
                     + plant_forms.ENTRIES_TABLE)
        # `today` is injectable ONLY so the MANIFEST_REQUIRED_SINCE threshold is exercisable on
        # BOTH sides on the day a change ships (2026-08-17). vault_integrity_problems was always
        # two-directionally testable — it reads the register row's date, and test_harness pins a
        # pre-gate and a post-gate row — but the APPROVE path stamped the real clock, so the
        # branch it lands on was whatever the calendar said. That is exactly how the manifest-sha
        # defect hid: the D1.c approve test stamped 2026-08-16, one day under the threshold, so
        # the manifest check never ran through approve until the morning it went red in CI's
        # absence. A date-activated gate that can only be exercised on one side of its own
        # threshold is unfalsifiable at authoring time (§13).
        fh.write(plant_forms.format_register_row(
            today or _dt.date.today().isoformat(), plant_id, "holdout", sha, reason,
            status="current", supersedes=supersedes or ""))
    print("APPROVED {} -> bodies/ + register (sha {}...). Commit + push the vault privately."
          .format(plant_id, sha[:12]))
    return 0


# --- D4: remediation — supersede the bad pairs, on confirm ----------------------------------
def _register_entries(vault_dir):
    reg = os.path.join(vault_dir, REGISTER_NAME)
    if not os.path.isfile(reg):
        return []
    return plant_forms.parse_register(open(reg).read())


def _latest_register_rows(vault_dir):
    # delegates to THE latest-wins owner (plant_forms.resolve_latest, arch-F4) — a local
    # fold here is how remediation reads different semantics than the scorer
    return plant_forms.resolve_latest(_register_entries(vault_dir))


def _cas_error(vault_dir, sid, latest=None):
    """COMPARE-AND-SWAP pre-check for a status transition: the body on disk must still be
    the exact bytes the register last recorded for this id. A drifted body gets NO status
    transition — investigate the drift first (it is already an integrity finding)."""
    latest = latest if latest is not None else _latest_register_rows(vault_dir)
    if sid not in latest:
        return "no register entry for '{}'".format(sid)
    body = os.path.join(vault_dir, "bodies", sid + ".json")
    if not os.path.isfile(body):
        return "no body on disk for '{}'".format(sid)
    if plant_forms.plant_sha(body) != latest[sid]["content_sha256"]:
        return ("CAS refusal: body '{}' no longer matches its registered content sha — it "
                "changed since the register last recorded it; run the vault integrity "
                "check before any status transition".format(sid))
    return None


def append_status_row(vault_dir, sid, status, reason, supersedes=""):
    """Append-only status transition (bodies are IMMUTABLE — a transition is a new register
    row, never an edit or a deletion), CAS-guarded on the body hash. Returns None on
    success or the refusal string."""
    import datetime as _dt
    err = _cas_error(vault_dir, sid)
    if err:
        return err
    sha = plant_forms.plant_sha(os.path.join(vault_dir, "bodies", sid + ".json"))
    with open(os.path.join(vault_dir, REGISTER_NAME), "a") as fh:
        fh.write(plant_forms.format_register_row(
            _dt.date.today().isoformat(), sid, "holdout", sha, reason,
            status=status, supersedes=supersedes))
    return None


def cmd_remediate_holdout(vault_dir, model, claude_bin, repeat, only_id=None, *,
                          validator=None, judge=None, confirm=None, interactive=None):
    """D4: run the D1 validation + D2 judge over every CURRENT approved pair and apply the
    CONFIRMED disposition — REJECT/FIX-ORACLE retires the PAIR to legacy-invalid (pair-level:
    retiring a control retires its plant too, else recall and FP split across asymmetric
    cohorts); KEEP marks the control known-overflag (counted, tracked, never hidden). Every
    transition is append-only + CAS-guarded and runs ONLY on an interactive y/n bound to the
    control's validation-manifest hash. Non-interactive ABORTS before any model spend.
    A failing PLANT gets a note (harden/supersede via the authoring cycle), not a judge —
    the judge's three shapes are control shapes. Bodies are never edited or deleted."""
    _refuse_in_tree(vault_dir)
    if interactive is None:
        interactive = sys.stdin.isatty()
    if not interactive:
        print("ABORT: remediation applies irreversible register transitions on a human "
              "y/n — run it in a terminal. Nothing was validated or changed (no spend).")
        return 2
    import run_calibration as rc
    bodies_dir = os.path.join(vault_dir, "bodies")
    # ONE loader (rc.load_corpus, arch-F9/F1) — never a second bodies/*.json loop
    scs = {s["id"]: s for s in rc.load_corpus([bodies_dir]) if s.get("id")}
    entries = _register_entries(vault_dir)
    latest = plant_forms.resolve_latest(entries)
    statuses = plant_forms.resolve_statuses(entries)
    pairs = [(scs[sc["control_for"]], sc) for sc in scs.values()
             if sc.get("control_for") and sc["control_for"] in scs
             and statuses.get(sc["id"], "current") == "current"
             and statuses.get(sc["control_for"], "current") == "current"]
    if validator is None:
        def validator(s, vd, c, **kw):
            return validate_item(s, vd, c, host_bin=claude_bin, **kw)
    cfn = confirm or confirm_disposition
    acted = 0
    for plant_sc, ctl_sc in pairs:
        if only_id and only_id not in (plant_sc["id"], ctl_sc["id"]):
            continue
        res = {}
        for sc in (ctl_sc, plant_sc):
            contract = eval_contract(sc, model, host_bin=claude_bin, repeat=repeat)
            res[sc["id"]] = validator(sc, vault_dir, contract,
                                      body_path=os.path.join(bodies_dir, sc["id"] + ".json"))
            print_validation_table(res[sc["id"]]["table"])
        res_c, res_p = res[ctl_sc["id"]], res[plant_sc["id"]]
        if res_c["table"]["approvable"] and res_p["table"]["approvable"]:
            print("PAIR OK: {} + {}".format(plant_sc["id"], ctl_sc["id"]))
            continue
        if res_c["table"]["approvable"]:
            # only the plant failed — a weak plant is the authoring cycle's business
            print("WEAK PLANT {}: the verifier no longer catches it at k/k — harden or "
                  "supersede it next authoring cycle (no judge disposition; the judge's "
                  "shapes are control shapes).".format(plant_sc["id"]))
            continue
        if res_c["table"]["verdict"] == "inconclusive":
            # integration-adversary GAP5 (2026-08-16): inconclusive means the ENVIRONMENT
            # refused — zero measured reps. An irreversible transition (or even a judge
            # spend) on an unmeasured run would break D1's own fail-closed rule.
            print("INCONCLUSIVE {}: every validation rep was an environment failure — "
                  "nothing was measured, so nothing is judged or retired. Fix the "
                  "environment and re-run.".format(ctl_sc["id"]))
            continue
        jr = (judge or judge_control)(ctl_sc, res_c.get("reasoning") or "",
                                      deny_read=[vault_dir])
        print("JUDGE (advisory): {} — votes {}".format(
            jr["verdict"], "/".join(str(v) for v in jr["votes"])))
        if jr.get("rationale"):
            print("--- judge rationale (transient — not persisted) ---")
            print(jr["rationale"].strip()[:2000])
        if jr["verdict"] == "INCONCLUSIVE":
            print("INCONCLUSIVE — the judges disagreed; no action taken (re-run, or read "
                  "the pair yourself).")
            continue
        msha = manifest_sha(res_c["manifest"])
        if jr["verdict"] in ("REJECT", "FIX-ORACLE"):
            action = ("retire the PAIR {} + {} to legacy-invalid (judge {})"
                      .format(plant_sc["id"], ctl_sc["id"], jr["verdict"]))
            if not cfn(action, msha, interactive=True):
                print("skipped — statuses unchanged.")
                continue
            # PAIR atomicity: CAS-check BOTH before writing EITHER, so a drifted body can
            # never leave a half-retired (asymmetric) pair behind.
            errs = [e for e in (_cas_error(vault_dir, ctl_sc["id"], latest),
                                _cas_error(vault_dir, plant_sc["id"], latest)) if e]
            if errs:
                for e in errs:
                    print("REFUSED: " + e)
                continue
            reason = "superseded: judge {} at remediation".format(jr["verdict"])
            for sid in (ctl_sc["id"], plant_sc["id"]):
                err = append_status_row(vault_dir, sid, "legacy-invalid", reason)
                if err:
                    print("REFUSED: " + err)
            acted += 1
            print("PAIR retired (append-only; bodies untouched). Land a SEPARATELY-"
                  "APPROVED superseding replacement pair: `holdout author …` then "
                  "`holdout approve --vault-dir {} <new-plant> --supersedes {}` and "
                  "`… <new-control> --supersedes {}` — the corpus only grows."
                  .format(vault_dir, plant_sc["id"], ctl_sc["id"]))
        elif jr["verdict"] == "KEEP":
            action = ("mark control {} known-overflag (a real, tracked verifier weakness "
                      "— counted, never hidden)".format(ctl_sc["id"]))
            if not cfn(action, msha, interactive=True):
                print("skipped — statuses unchanged.")
                continue
            err = append_status_row(
                vault_dir, ctl_sc["id"], "known-overflag",
                "judge KEEP at remediation — genuine verifier over-flag; do not tune the "
                "verifier against this held item (promote-and-replace to fix it)")
            print("REFUSED: " + err if err
                  else "control marked known-overflag; the corrected FP keeps counting it.")
            acted += 1 if not err else 0
    print("remediation pass complete: {} pair(s) reviewed · {} transition(s) applied. "
          "Commit + push the vault, then re-run `holdout diagnose --vault <url>` — it now "
          "reports BOTH the legacy and corrected readings.".format(len(pairs), acted))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Holdout controller — author fresh answers into the private vault, and run "
                    "the eval with the agent boxed-in. Opt-in and manual.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="clone the vault, verify it, run a confined holdout eval, "
                                    "delete the clone")
    r.add_argument("--vault", required=True, help="git URL of the private holdout vault")
    r.add_argument("--summary", action="store_true",
                   help="collapse the rollup wall to just the verdicts + reading + a dev-vs-holdout "
                        "comparison (glance-able)")
    # Extra run_calibration args (e.g. --model sonnet --repeat 3) are captured by parse_known_args
    # below and forwarded — argparse.REMAINDER does not collect LEADING options like --model, which
    # is why `run --vault URL --model sonnet` used to error.
    i = sub.add_parser("integrity", help="READ-ONLY: check whether a vault is fit to feed an "
                                         "eval (no model, no clone, no writes)")
    i.add_argument("--vault-dir", required=True,
                   help="a local clone of the private vault (outside the public tree)")
    a = sub.add_parser("author", help="generate fresh holdout plants (adversary model) into the "
                                      "vault's proposed/ for review")
    a.add_argument("--vault-dir", required=True,
                   help="a PERSISTENT local clone of the private vault (outside the public tree)")
    a.add_argument("--model", required=True, help="adversary model (>= the doer's tier)")
    a.add_argument("--category", help="focus category for this cycle")
    a.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    v = sub.add_parser("approve", help="validate (run the target verifier under the eval "
                                       "contract; k/k or it refuses), then move a reviewed "
                                       "proposed body into bodies/ + register")
    v.add_argument("--vault-dir", required=True)
    v.add_argument("id", help="the proposed plant id to approve")
    v.add_argument("--reason", required=True, help="why this assignment (audit trail)")
    v.add_argument("--model", default=None,
                   help="verifier model for the validation gate (default: the eval's "
                        "own default, TDD_PLAYBOOK_CALIBRATION_MODEL or haiku — MUST match "
                        "the model your holdout evals use, or 'holds' doesn't predict the "
                        "reading; pass --model sonnet if that is what your runs use)")
    v.add_argument("--repeat", type=int, default=None, help="validation reps (default 3)")
    v.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    v.add_argument("--supersedes", default="",
                   help="the retired body id this replacement supersedes (D4 remediation)")
    m = sub.add_parser("remediate", help="run the validation gate + advisory judge over "
                                         "every CURRENT approved pair; supersede bad pairs "
                                         "/ mark known-overflag on YOUR y/n (interactive "
                                         "only; non-interactive aborts)")
    m.add_argument("--vault-dir", required=True,
                   help="a PERSISTENT local clone of the private vault (outside the public "
                        "tree)")
    m.add_argument("--model", default=None,
                   help="verifier model (default: the eval's own default — must match your "
                        "holdout eval model; pass --model sonnet if that is what your runs "
                        "use)")
    m.add_argument("--repeat", type=int, default=None)
    m.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    m.add_argument("--id", default=None, help="remediate only the pair containing this id")
    w = sub.add_parser("validate", help="READ-ONLY: run a body's target verifier against it "
                                        "under the eval contract and print the k/n decision "
                                        "table (moves nothing, writes nothing)")
    w.add_argument("--vault-dir", required=True)
    w.add_argument("id", help="the proposed or approved body id to validate")
    w.add_argument("--model", default=None)
    w.add_argument("--repeat", type=int, default=None)
    w.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    d = sub.add_parser("diagnose", help="run the holdout eval AND classify each miss "
                                        "(would-pass-normalized vs a genuine wrong verdict vs "
                                        "inconclusive) — read-only triage that says WHAT to fix; "
                                        "emits SAFE labels only, never the answer key")
    d.add_argument("--vault", required=True, help="git URL of the private holdout vault")
    # diagnose forwards --model/--repeat via extra (like run); it always runs glance-able + diagnosed.
    args, extra = ap.parse_known_args(argv)
    if args.cmd == "run":
        # forward --model/--repeat/etc. to run_calibration
        return run_holdout(args.vault, extra, summary=args.summary)
    if args.cmd == "diagnose":
        # a normal scored run WITH --diagnose (in-pass, no replay, no persisted output)
        return run_holdout(args.vault, ["--diagnose", *extra], summary=True)
    # author/approve take no forwarded args — reject unknowns strictly.
    if extra:
        ap.error("unrecognized arguments: " + " ".join(extra))
    if args.cmd == "integrity":
        return cmd_integrity(args.vault_dir)
    if args.cmd == "author":
        return cmd_author_holdout(args.vault_dir, args.model, args.category, args.claude_bin)
    if args.cmd == "approve":
        return cmd_approve_holdout(args.vault_dir, args.id, args.reason, model=args.model,
                                   claude_bin=args.claude_bin, repeat=args.repeat,
                                   supersedes=args.supersedes)
    if args.cmd == "remediate":
        import run_calibration as rc
        return cmd_remediate_holdout(args.vault_dir, args.model or rc.DEFAULT_MODEL,
                                     args.claude_bin, args.repeat, only_id=args.id)
    if args.cmd == "validate":
        import run_calibration as rc
        return cmd_validate_holdout(args.vault_dir, args.id, args.model or rc.DEFAULT_MODEL,
                                    args.claude_bin, args.repeat)
    return 2


if __name__ == "__main__":
    sys.exit(main())
