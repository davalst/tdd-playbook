#!/usr/bin/env python3
"""Suite-level regression tests for the holdout answer-key confinement (Part 2, 2026-08-15).

These live in the BLESSED suite (not only calibration/test_harness.py) because they pin the
security-adversary's confirmed findings on the diff that built the holdout controller — chiefly
F1, the critical one: `git clone` writes `.git/` beside `bodies/`, and denying only the
`bodies/` leaf left `git show HEAD:bodies/*.json` able to reconstruct the entire answer key from
the object store. The fix denies the whole clone TREE. A critical security regression belongs in
the first-class suite that runs every gate, and it is the closure evidence for the P1 finding in
docs/reviews/2026-08-15-two-tier-calibration-part2-controller.json.

Raw `assert` (H5): an assert cannot fake a passing suite, an exit call can. main() sums failures.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# dirname^3: tests -> tdd-playbook -> plugins -> REPO ROOT.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "calibration"))

import confine  # noqa: E402
import child_env as ce  # noqa: E402
import holdout  # noqa: E402
import run_calibration as rc  # noqa: E402


def test_holdout_deny_read_prefers_clone_root():
    """F1: the deny target is the whole clone ROOT (covers .git), not the bodies leaf."""
    keep_dir = os.environ.get(rc.HOLDOUT_DIR_ENV)
    keep_deny = os.environ.get(rc.HOLDOUT_DENY_ENV)
    try:
        os.environ[rc.HOLDOUT_DIR_ENV] = "/clone/vault/bodies"
        os.environ[rc.HOLDOUT_DENY_ENV] = "/clone"
        assert rc.holdout_deny_read() == ["/clone"], rc.holdout_deny_read()
        # and with no env at all, a dev run is never confined
        os.environ.pop(rc.HOLDOUT_DIR_ENV, None)
        os.environ.pop(rc.HOLDOUT_DENY_ENV, None)
        assert rc.holdout_deny_read() is None
    finally:
        for k, v in ((rc.HOLDOUT_DIR_ENV, keep_dir), (rc.HOLDOUT_DENY_ENV, keep_deny)):
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_run_holdout_denies_whole_clone_tree():
    """F1 end-to-end: run_holdout sets the deny env to a root that contains BOTH bodies/ and the
    .git sibling `git show` would reconstruct the key from. Offline (a local git vault clone)."""
    git_id = ["-c", "user.email=t@t", "-c", "user.name=t"]
    with tempfile.TemporaryDirectory() as vault:
        bodies = os.path.join(vault, "bodies")
        os.makedirs(bodies)
        with open(os.path.join(bodies, "b.json"), "w") as fh:
            json.dump({"id": "hc-body", "agent": "claims-verifier", "plant": "p",
                       "edits": [], "task": "t", "must_match": ["a"], "must_not_match": ["b"]}, fh)
        # post-2026-08-16 a register is REQUIRED whenever bodies exist (a register-less
        # vault refuses: every body would run unauthorized). Dated pre-gate -> no manifest.
        import plant_forms
        with open(os.path.join(vault, holdout.REGISTER_NAME), "w") as fh:
            fh.write("# H\n\n## Entries\n\n" + plant_forms.ENTRIES_TABLE
                     + plant_forms.format_register_row(
                         "2026-08-15", "hc-body", "holdout",
                         plant_forms.plant_sha(os.path.join(bodies, "b.json")), "seed"))
        for c in (["git", "-C", vault, "init", "-q"],
                  ["git", "-C", vault, *git_id, "add", "-A"],
                  ["git", "-C", vault, *git_id, "commit", "-q", "-m", "seed"]):
            subprocess.run(c, check=True, capture_output=True, text=True)
        seen = {}

        def runner(argv, env, bodies_dir):
            deny = env.get(rc.HOLDOUT_DENY_ENV)
            git_sibling = os.path.join(os.path.dirname(bodies_dir), ".git")
            seen["ok"] = (bool(deny)
                          and holdout.dest_is_inside_tree(bodies_dir, deny)
                          and holdout.dest_is_inside_tree(git_sibling, deny)
                          and "--form" in argv and "holdout" in argv)
            return 0

        code = holdout.run_holdout(vault, ["--dry-run"], runner=runner)
        assert code == 0
        assert seen.get("ok"), seen


def test_child_env_strips_holdout_location():
    """F2: the answer-key location never reaches a nested model's env; capture stays off."""
    keep_a = os.environ.get(rc.HOLDOUT_DIR_ENV)
    keep_b = os.environ.get(rc.HOLDOUT_DENY_ENV)
    try:
        os.environ[rc.HOLDOUT_DIR_ENV] = "/clone/vault/bodies"
        os.environ[rc.HOLDOUT_DENY_ENV] = "/clone"
        env = ce.child_env()
        assert rc.HOLDOUT_DIR_ENV not in env and rc.HOLDOUT_DENY_ENV not in env, \
            [k for k in env if "HOLDOUT" in k]
        assert env.get("TDD_PLAYBOOK_HOOK_CAPTURE") == "off"
    finally:
        for k, v in ((rc.HOLDOUT_DIR_ENV, keep_a), (rc.HOLDOUT_DENY_ENV, keep_b)):
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_confine_denies_git_sibling_under_root():
    """F1 at the OS layer (macOS): denying the clone ROOT blocks the .git sibling; a MUST-FAIL
    with only the bodies leaf denied leaves it readable. Skips cleanly without sandbox-exec."""
    if not confine.sandbox_exec_available():
        return
    with tempfile.TemporaryDirectory() as d:
        root = os.path.realpath(os.path.join(d, "vault"))
        bodies = os.path.join(root, "bodies")
        gitobj = os.path.join(root, ".git")
        ws = os.path.realpath(os.path.join(d, "ws"))
        for p in (bodies, gitobj, ws):
            os.makedirs(p)
        with open(os.path.join(gitobj, "answer"), "w") as fh:
            fh.write("ANSWER-KEY")
        probe = os.path.join(ws, "p.sh")
        with open(probe, "w") as fh:
            fh.write('#!/bin/sh\ncat "%s/answer" >/dev/null 2>&1 && echo READ || echo BLOCK\n'
                     % gitobj)
        os.chmod(probe, 0o755)
        blocked = subprocess.run(confine.confined_argv(["/bin/sh", probe], ws, deny_read=[root]),
                                 capture_output=True, text=True, timeout=30).stdout
        assert "BLOCK" in blocked, blocked
        leaked = subprocess.run(confine.confined_argv(["/bin/sh", probe], ws, deny_read=[bodies]),
                                capture_output=True, text=True, timeout=30).stdout
        assert "READ" in leaked, leaked  # the original bug, proving the test can distinguish


def test_run_holdout_refuses_form_override():
    """SECURITY (adversary finding 1, 2026-08-16): the egress muzzle derives from
    `--form holdout` in the child, and argparse takes the LAST --form — a forwarded
    `--form all` would run the private bodies through the DEV printer (plant text + both
    oracle regexes + raw doer output). run_holdout must REFUSE the override, before any
    clone."""
    try:
        holdout.run_holdout("unused://never-cloned", ["--form", "all"])
    except ValueError as e:
        assert "--form" in str(e), e
    else:
        raise AssertionError("run_holdout accepted a forwarded --form override")


def test_judge_workspace_outside_public_repo():
    """SECURITY (adversary finding 2, 2026-08-16): the sandbox re-grants writes to its
    WORKSPACE (the cwd). The judge is the one model holding approved bodies + oracle
    regexes in context, so its workspace must be a throwaway temp dir — never the public
    repo dir that gets committed and pushed. Also pins that the vault deny-read is
    actually forwarded (a **kw double must not let the argument vanish)."""
    import host_runner
    seen = {}

    def spy_invoke(host, binary, prompt, model, cwd, **kw):
        seen["cwd"] = cwd
        seen["deny"] = kw.get("confine_deny_read")
        return host_runner.Result(host, "ok", "Control-Verdict: KEEP\nRecommendation: k",
                                  0, None)
    keep = host_runner.invoke
    host_runner.invoke = spy_invoke
    try:
        jr = holdout.judge_control({"id": "x", "edits": [], "task": "t"}, "r", k=1,
                                   deny_read=["/some/vault"])
    finally:
        host_runner.invoke = keep
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    assert seen.get("cwd") and not seen["cwd"].startswith(repo_root), seen
    assert "tdd-judge-" in seen["cwd"], seen
    assert seen.get("deny") == ["/some/vault"], seen
    assert not os.path.exists(seen["cwd"]), "judge workspace not deleted"
    assert jr["verdict"] == "KEEP", jr


def test_approve_manifest_sha_matches_landed_body():
    """The bytes VALIDATED are the bytes that LAND (2026-08-17, pre-fix 656eff5).

    approve computed the manifest's candidate sha on the PROPOSED file and then re-dumped
    the body into bodies/ with indent=2 — different bytes — so the manifest held a sha that
    could never match the body it authorizes. vault_integrity_problems reads exactly that
    pair, and `holdout run` ABORTS on a non-empty problem list, so ONE hand-authored or
    reformatted proposed file bricked the whole vault. `cmd_author_holdout` already wrote
    the canonical form as a duplicated literal, which is why machine-authored bodies matched
    by luck and this stayed invisible until a hand-shaped body met MANIFEST_REQUIRED_SINCE.

    The proposed body here is written NON-canonically ON PURPOSE (compact, no trailing
    newline): that is the hand-edited shape the flow invites, since `holdout author` tells a
    human to review the file before approving. Vacuity-guarded — an approve that does not
    land fails the test rather than skipping the assertions.
    """
    plant = {"id": "sha-chain-plant", "agent": "claims-verifier", "plant": "p", "edits": [],
             "task": "t", "must_match": ["SENTINEL_ORACLE"], "must_not_match": ["x"]}

    def caught(sc, vd, contract, body_path=None, **kw):
        import plant_forms
        return {"table": {"id": sc["id"], "kind": "plant", "k": 3, "n": 3, "invalid": 0,
                          "verdict": "caught", "approvable": True},
                "manifest": {"schema": 1, "candidate_id": sc["id"],
                             "candidate_content_sha256": plant_forms.plant_sha(body_path),
                             "k": 3, "n": 3, "verdict": "caught", "contract": {}, "reps": []},
                "reasoning": None}

    import contextlib
    import io
    import plant_forms
    with tempfile.TemporaryDirectory() as vault:
        os.makedirs(os.path.join(vault, "proposed"))
        with open(os.path.join(vault, "proposed", plant["id"] + ".json"), "w") as fh:
            json.dump(plant, fh)          # deliberately NOT the canonical byte-form
        with contextlib.redirect_stdout(io.StringIO()):
            code = holdout.cmd_approve_holdout(vault, plant["id"], "sha-chain regression",
                                               validator=caught)
        body = os.path.join(vault, "bodies", plant["id"] + ".json")
        assert code == 0 and os.path.isfile(body), (code, os.listdir(vault))
        manifest = json.load(open(os.path.join(vault, "manifests", plant["id"] + ".json")))
        assert manifest["candidate_content_sha256"] == plant_forms.plant_sha(body), (
            "manifest sha {} != landed body sha {}".format(
                manifest["candidate_content_sha256"][:12], plant_forms.plant_sha(body)[:12]))
        assert holdout.vault_integrity_problems(vault) == [], \
            holdout.vault_integrity_problems(vault)


def _approve_into_fresh_vault(vault, plant, today=None):
    """Land `plant` in `vault` through the REAL approve path, from a deliberately non-canonical
    proposed file."""
    import plant_forms
    os.makedirs(os.path.join(vault, "proposed"), exist_ok=True)
    with open(os.path.join(vault, "proposed", plant["id"] + ".json"), "w") as fh:
        json.dump(plant, fh)

    def caught(sc, vd, contract, body_path=None, **kw):
        return {"table": {"id": sc["id"], "kind": "plant", "k": 3, "n": 3, "invalid": 0,
                          "verdict": "caught", "approvable": True},
                "manifest": {"schema": 1, "candidate_id": sc["id"],
                             "candidate_content_sha256": plant_forms.plant_sha(body_path),
                             "k": 3, "n": 3, "verdict": "caught", "contract": {}, "reps": []},
                "reasoning": None}
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        code = holdout.cmd_approve_holdout(vault, plant["id"], "regression fixture",
                                           validator=caught, today=today)
    return code, buf.getvalue()


def _stale_the_manifest(vault, plant_id):
    """PLANT the defect the date gate is supposed to catch, AFTER landing — approve's own TOCTOU
    check refuses a manifest sha that disagrees with the proposed bytes, so staleness cannot be
    injected through the gate (which is itself correct behaviour)."""
    path = os.path.join(vault, "manifests", plant_id + ".json")
    manifest = json.load(open(path))
    manifest["candidate_content_sha256"] = "f" * 64
    with open(path, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)


def test_approve_manifest_gate_exercised_on_both_sides_of_its_date():
    """§13 two-directional (2026-08-17): MANIFEST_REQUIRED_SINCE activates the manifest reader on
    a date. vault_integrity_problems was always testable both ways (it reads the register row's
    date), but APPROVE stamped the real clock, so the branch a landed body fell on was whatever
    the calendar said — which is exactly how the manifest-sha defect hid for a day: the approve
    test stamped one day under the threshold and the check never ran through approve.

    `today` is now injectable, so BOTH directions are pinned regardless of when this suite runs:
    a PRE-threshold row is grandfathered even with a deliberately stale manifest, and a
    POST-threshold row is caught. The stale manifest is the SAME planted defect in both halves,
    so the only variable is the date — an ALLOW row and a BLOCK row over one condition.
    """
    plant = {"id": "date-gate-plant", "agent": "claims-verifier", "plant": "p", "edits": [],
             "task": "t", "must_match": ["SENTINEL_ORACLE"], "must_not_match": ["x"]}
    before = (holdout.MANIFEST_REQUIRED_SINCE[:8]
              + "{:02d}".format(int(holdout.MANIFEST_REQUIRED_SINCE[8:]) - 1))
    after = (holdout.MANIFEST_REQUIRED_SINCE[:8]
             + "{:02d}".format(int(holdout.MANIFEST_REQUIRED_SINCE[8:]) + 1))

    with tempfile.TemporaryDirectory() as vault:
        code, _ = _approve_into_fresh_vault(vault, plant, today=before)
        assert code == 0, "approve did not land the pre-threshold body"
        _stale_the_manifest(vault, plant["id"])
        assert holdout.vault_integrity_problems(vault) == [], (
            "a PRE-threshold body must be grandfathered: "
            + repr(holdout.vault_integrity_problems(vault)))

    with tempfile.TemporaryDirectory() as vault:
        code, _ = _approve_into_fresh_vault(vault, plant, today=after)
        assert code == 0, "approve did not land the post-threshold body"
        _stale_the_manifest(vault, plant["id"])
        probs = holdout.vault_integrity_problems(vault)
        assert any("date-gate-plant" in p and "manifest" in p.lower() for p in probs), (
            "a POST-threshold body with a stale manifest must be caught: " + repr(probs))


def test_integrity_clean_message_carries_its_denominator():
    """§12 (2026-08-17, found on the FIRST real run): the clean message read "every one matching
    its register row and its validation manifest" — but bodies dated before
    MANIFEST_REQUIRED_SINCE have their manifest SKIPPED, not verified. On David's real vault that
    printed manifest assurance for 20 bodies while checking 0 of them.

    A result carries its scope. The clean line must state how many manifests were actually
    CHECKED and how many were grandfathered, and must not claim manifest verification it did not
    do. Two directions: a pre-cutoff body reports 0 checked, a post-cutoff body reports 1.
    """
    before = (holdout.MANIFEST_REQUIRED_SINCE[:8]
              + "{:02d}".format(int(holdout.MANIFEST_REQUIRED_SINCE[8:]) - 1))
    after = (holdout.MANIFEST_REQUIRED_SINCE[:8]
             + "{:02d}".format(int(holdout.MANIFEST_REQUIRED_SINCE[8:]) + 1))
    script = os.path.join(REPO, "calibration", "holdout.py")

    def clean_line(today):
        plant = {"id": "denom-plant", "agent": "claims-verifier", "plant": "p", "edits": [],
                 "task": "t", "must_match": ["SENTINEL_ORACLE"], "must_not_match": ["x"]}
        with tempfile.TemporaryDirectory() as vault:
            code, _ = _approve_into_fresh_vault(vault, plant, today=today)
            assert code == 0, "approve did not land the body"
            out = subprocess.run([sys.executable, script, "integrity", "--vault-dir", vault],
                                 capture_output=True, text=True, timeout=60)
            assert out.returncode == 0, out
            return out.stdout

    grandfathered = clean_line(before)
    assert "0 of 1" in grandfathered, \
        "a grandfathered body must report 0 manifests checked: " + grandfathered
    assert "grandfathered" in grandfathered.lower(), grandfathered

    verified = clean_line(after)
    assert "1 of 1" in verified, \
        "a post-cutoff body must report 1 manifest checked: " + verified


def test_integrity_subcommand_is_wired_and_names_the_fix():
    """§6a (2026-08-17): vault_integrity_problems ran ONLY inside run_holdout, so the only way to
    learn a vault was stale was to start a full eval and watch it abort. `holdout integrity` is
    the read-only reader. Pins that the subcommand EXISTS in the real CLI (a function nobody can
    invoke is dark), that a clean vault exits 0, and that a problem exits nonzero AND prints the
    remediation command — a refusing check prints the diagnosis it already holds (§4a)."""
    plant = {"id": "integ-plant", "agent": "claims-verifier", "plant": "p", "edits": [],
             "task": "t", "must_match": ["SENTINEL_ORACLE"], "must_not_match": ["x"]}
    after = (holdout.MANIFEST_REQUIRED_SINCE[:8]
             + "{:02d}".format(int(holdout.MANIFEST_REQUIRED_SINCE[8:]) + 1))
    script = os.path.join(REPO, "calibration", "holdout.py")

    help_run = subprocess.run([sys.executable, script, "integrity", "--help"],
                              capture_output=True, text=True, timeout=30)
    assert help_run.returncode == 0 and "--vault-dir" in help_run.stdout, help_run

    with tempfile.TemporaryDirectory() as vault:
        code, _ = _approve_into_fresh_vault(vault, plant, today=after)
        assert code == 0, "approve did not land the body"
        clean = subprocess.run([sys.executable, script, "integrity", "--vault-dir", vault],
                               capture_output=True, text=True, timeout=60)
        assert clean.returncode == 0 and "CLEAN" in clean.stdout, clean

    with tempfile.TemporaryDirectory() as vault:
        code, _ = _approve_into_fresh_vault(vault, plant, today=after)
        assert code == 0, "approve did not land the body"
        _stale_the_manifest(vault, plant["id"])
        dirty = subprocess.run([sys.executable, script, "integrity", "--vault-dir", vault],
                               capture_output=True, text=True, timeout=60)
        assert dirty.returncode == 1, dirty
        assert "PROBLEM" in dirty.stdout, dirty.stdout
        assert "validate --vault-dir" in dirty.stdout and "integ-plant" in dirty.stdout, \
            "the refusal must name the fix command: " + dirty.stdout


def main():
    failures = []
    for fn in (test_run_holdout_refuses_form_override,
               test_approve_manifest_sha_matches_landed_body,
               test_integrity_clean_message_carries_its_denominator,
               test_approve_manifest_gate_exercised_on_both_sides_of_its_date,
               test_integrity_subcommand_is_wired_and_names_the_fix,
               test_judge_workspace_outside_public_repo,
               test_holdout_deny_read_prefers_clone_root,
               test_run_holdout_denies_whole_clone_tree,
               test_child_env_strips_holdout_location,
               test_confine_denies_git_sibling_under_root):
        try:
            fn()
            print("  ok   - " + fn.__name__)
        except AssertionError as e:
            failures.append("{}: {}".format(fn.__name__, e))
            print("  FAIL - " + fn.__name__)
    assert not failures, "\n".join(failures)
    print("holdout-confinement suite green")


if __name__ == "__main__":
    main()
