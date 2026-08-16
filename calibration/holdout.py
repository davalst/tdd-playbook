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


def vault_integrity_problems(vault_root):
    """Integrity of a vault BEFORE it feeds an eval: (1) HASH-DRIFT via verify_bodies (a body
    whose content no longer matches its recorded content_sha256), and (2) an UNREGISTERED body —
    a bodies/*.json id with no register row (verify_bodies checks rows->shas, so an extra body
    would otherwise run untracked/unauthorized). Returns the problem list ([] == clean). No
    register present -> None (a fresh vault with only bodies has nothing recorded to drift from;
    the caller decides)."""
    reg = os.path.join(vault_root, REGISTER_NAME)
    bodies = os.path.join(vault_root, "bodies")
    if not os.path.isfile(reg):
        return None
    entries = plant_forms.parse_register(open(reg).read())
    problems = list(verify_bodies(entries, bodies))
    reg_ids = {e["plant_id"] for e in entries}
    for bid in holdout_shas(bodies):
        if bid not in reg_ids:
            problems.append("body '{}' is not in the register — an unregistered holdout body is "
                            "not authorized/verifiable".format(bid))
    return problems


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
    workdir = tempfile.mkdtemp(prefix="tdd-holdout-")
    try:
        dest = stage_vault(vault_url, workdir)
        bodies = os.path.join(dest, "bodies")
        probs = vault_integrity_problems(dest)
        if probs:
            raise ValueError("holdout vault FAILED its integrity check — refusing to run "
                             "(drift or unregistered body):\n  " + "\n  ".join(probs))
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


def _sha256_file(path):
    import hashlib
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


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
        "runner_source_sha256": _sha256_file(os.path.join(HERE, "host_runner.py")),
        "oracle_source_sha256": _sha256_file(RUNNER),
        "oracle_normalization_version": rc.ORACLE_NORMALIZATION_VERSION,
        "verifier_brief_sha256": _sha256_file(os.path.join(
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
    reps, reasoning = [], None
    keep_deny = os.environ.get(rc.HOLDOUT_DENY_ENV)
    os.environ[rc.HOLDOUT_DENY_ENV] = vault_dir
    try:
        for _ in range(int(contract["repeat"])):
            if runner is not None:
                status, out = runner(clean)
            else:
                root = rc.stage(clean)
                try:
                    status, out = rc.run_agent(clean, root, host_bin, contract["model"],
                                               contract["host"],
                                               isolation=contract["isolation"])
                finally:
                    shutil.rmtree(root, ignore_errors=True)
            if status == "ok":
                passed, _probs, mode = rc.oracle(clean, out)
                reps.append({"passed": passed, "mode": mode, "env": False})
                if not passed and reasoning is None:
                    reasoning = out
            else:
                reps.append({"passed": False,
                             "mode": "timeout" if status == "timeout" else "env-failure",
                             "env": status == "env_failure"})
    finally:
        if keep_deny is None:
            os.environ.pop(rc.HOLDOUT_DENY_ENV, None)
        else:
            os.environ[rc.HOLDOUT_DENY_ENV] = keep_deny
    counted = [r for r in reps if not r["env"]]
    k = sum(1 for r in counted if r["passed"])
    n = len(counted)
    verdict = validation_verdict(k, n, is_control)
    if body_path:
        cand_sha = _sha256_file(body_path)
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
        with open(os.path.join(proposed, sc["id"] + ".json"), "w") as fh:
            json.dump(sc, fh, indent=2)
            fh.write("\n")
        accepted += 1
        print("PROPOSED {} (review the file, then: holdout approve --vault-dir {} {} --reason "
              "...)".format(sc["id"], vault_dir, sc["id"]))
    print("holdout author: {} proposed to {} · {} rejected".format(
        accepted, proposed, len(res["rejected"])))
    return 0 if accepted else 1


def cmd_approve_holdout(vault_dir, plant_id, reason, *, model=None, claude_bin="claude",
                        repeat=None, validator=None):
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
    with open(src) as fh:
        sc = json.load(fh)
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
    model = model or os.environ.get("TDD_PLAYBOOK_CALIBRATION_MODEL", "sonnet")
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
    with open(dst, "w") as fh:
        json.dump(sc, fh, indent=2)
        fh.write("\n")
    os.remove(src)
    sha = plant_forms.plant_sha(dst)
    reg = os.path.join(vault_dir, REGISTER_NAME)
    new = not os.path.isfile(reg)
    with open(reg, "a") as fh:
        if new:
            fh.write("# Holdout register\n\n" + plant_forms.ENTRIES_SECTION + "\n\n"
                     + plant_forms.ENTRIES_TABLE)
        fh.write(plant_forms.format_register_row(
            _dt.date.today().isoformat(), plant_id, "holdout", sha, reason))
    print("APPROVED {} -> bodies/ + register (sha {}...). Commit + push the vault privately."
          .format(plant_id, sha[:12]))
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
                   help="verifier model for the validation gate (default: "
                        "TDD_PLAYBOOK_CALIBRATION_MODEL or sonnet — MUST match the model "
                        "your holdout evals use, or 'holds' doesn't predict the reading)")
    v.add_argument("--repeat", type=int, default=None, help="validation reps (default 3)")
    v.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
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
    if args.cmd == "author":
        return cmd_author_holdout(args.vault_dir, args.model, args.category, args.claude_bin)
    if args.cmd == "approve":
        return cmd_approve_holdout(args.vault_dir, args.id, args.reason, model=args.model,
                                   claude_bin=args.claude_bin, repeat=args.repeat)
    if args.cmd == "validate":
        return cmd_validate_holdout(
            args.vault_dir, args.id,
            args.model or os.environ.get("TDD_PLAYBOOK_CALIBRATION_MODEL", "sonnet"),
            args.claude_bin, args.repeat)
    return 2


if __name__ == "__main__":
    sys.exit(main())
