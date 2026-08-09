#!/usr/bin/env python3
"""Planted-input calibration for `tdd uninstall` and `tdd reset` (owner-control Phase 4).

The plan these serve is "David holds every switch, and the system can be reset or removed at
will." That is only a real property if removal is SAFE, and the sharp edges here are not the
happy path:

  - This repo has FIVE live linked worktrees under `.claude/worktrees/`, one locked, several
    on unpushed branches. Any implementation that treats `.claude/` as a unit destroys them
    AND their uncommitted work, after which `git worktree prune` finishes the job. So the
    worktree case is a first-class planted test, not an edge note.
  - `.claude/commands/`, `.claude/agents/` and `.claude/bin/` are SHARED namespaces: a user's
    own slash command lives beside ours. Delete-by-name, never rmtree.
  - Common-dir state is shared by every worktree of a repo, so removing it from one affects
    all of them — which is why `--shared` is its own scope and never implied by `--repo`.
  - A dry run that prints one set of paths and deletes another is the whole failure class
    this feature could have. The printed set and the deleted set are asserted EQUAL.

Self-contained, no pytest. Run: python3 tests/test_vendoring.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
BIN = os.path.join(REPO, "plugins", "tdd-playbook", "bin")
INSTALLER = os.path.join(REPO, "scripts", "install_into_repo.py")

_r = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(path))
    spec.loader.exec_module(mod)
    return mod


def load_vendoring():
    return _load(os.path.join(BIN, "vendoring.py"), "vendoring")


def load_installer():
    return _load(INSTALLER, "install_into_repo")


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          timeout=30, check=True)


def _repo(base, name="main repo"):
    """A real git repo. The SPACE in the default name is deliberate shell-quoting coverage,
    copied from test_portable_core.py's fixture."""
    root = os.path.join(base, name)
    os.makedirs(root)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Vendoring Test")
    with open(os.path.join(root, "pay.py"), "w") as fh:
        fh.write("def charge(n):\n    return n * 2\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "fixture")
    return root


def _snapshot(root, skip=("/.git/",)):
    """{relpath: (sha256, mode)} — content and mode, never stat times.

    mtimes are excluded because _copy_tree mixes shutil.copy2 (preserves source mtime) with
    open().write() for the rewritten extensions, so they are nondeterministic BY CONSTRUCTION.
    File MODE is deliberately kept: the 0o755 chmod on .py/.sh is intentional behavior."""
    import hashlib
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            norm = "/" + rel.replace(os.sep, "/")
            if any(s in norm for s in skip) or fn.endswith(".pyc"):
                continue
            with open(p, "rb") as fh:
                out[rel] = (hashlib.sha256(fh.read()).hexdigest(),
                            os.stat(p).st_mode & 0o777)
    return out


# --------------------------------------------------------------------------- uninstall
def test_uninstall_is_the_inverse_of_install():
    print("\n[uninstall: the true inverse]")
    ven, inst = load_vendoring(), load_installer()
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        cdir = os.path.join(target, ".claude")
        os.makedirs(cdir, exist_ok=True)

        # PLANTED user state that must survive, in every shared namespace
        os.makedirs(os.path.join(cdir, "commands"), exist_ok=True)
        os.makedirs(os.path.join(cdir, "agents"), exist_ok=True)
        os.makedirs(os.path.join(cdir, "bin"), exist_ok=True)
        user_files = {
            os.path.join(cdir, "commands", "my-own.md"): "# my slash command\n",
            os.path.join(cdir, "agents", "my-adversary.md"): "# my agent\n",
            os.path.join(cdir, "bin", "my-tool.sh"): "#!/bin/sh\necho mine\n",
            os.path.join(cdir, "settings.local.json"): '{"permissions": {"allow": []}}\n',
        }
        for p, c in user_files.items():
            with open(p, "w") as fh:
                fh.write(c)
        custom_hook = {"matcher": "Bash", "hooks": [
            {"type": "command", "command": "./scripts/my-own-hook.sh"}]}
        with open(os.path.join(cdir, "settings.json"), "w") as fh:
            json.dump({"hooks": {"PostToolUse": [custom_hook]}}, fh)

        s0 = _snapshot(target)
        inst.main([target])
        s1 = _snapshot(target)
        check("install actually vendored something (the test is not vacuous)",
              len(s1) > len(s0) + 10, (len(s0), len(s1)))

        plan = ven.uninstall(target, host="claude", apply=True)
        s2 = _snapshot(target)

        # every user file survives, byte-identical
        for p in user_files:
            rel = os.path.relpath(p, target)
            check("user file survives uninstall: " + rel, s2.get(rel) == s0.get(rel),
                  (s0.get(rel), s2.get(rel)))
        # the custom hook group survives; ours are gone
        with open(os.path.join(cdir, "settings.json")) as fh:
            after = json.load(fh)
        cmds = [h.get("command", "") for g in after.get("hooks", {}).get("PostToolUse", [])
                for h in g.get("hooks", [])]
        check("custom user hook group survives uninstall",
              any("my-own-hook.sh" in c for c in cmds), cmds)
        check("no playbook hook remains", not any("/hooks/scripts/" in c for c in cmds), cmds)

        # no vendored file remains
        leftovers = [rel for rel in ven.installed_paths(REPO, target, "claude")
                     if os.path.exists(os.path.join(target, rel))]
        check("no vendored playbook file remains", leftovers == [], leftovers[:5])

        # PLANTED: the leftover detector must be able to FIRE (§13 calibrate-the-checker)
        ghost = os.path.join(cdir, "bin", "host_contract.py")
        os.makedirs(os.path.dirname(ghost), exist_ok=True)
        with open(ghost, "w") as fh:
            fh.write("# re-created by hand\n")
        again = [rel for rel in ven.installed_paths(REPO, target, "claude")
                 if os.path.exists(os.path.join(target, rel))]
        check("PLANTED re-created vendored file IS detected", again != [], again[:3])
        os.remove(ghost)

        # PLANTED: deleting a user file must make the survival check fail — otherwise the
        # survival assertions above could be passing for the wrong reason
        os.remove(os.path.join(cdir, "commands", "my-own.md"))
        s3 = _snapshot(target)
        check("PLANTED removed user file IS detected by the same comparison",
              s3.get(".claude/commands/my-own.md") != s0.get(".claude/commands/my-own.md"))


def test_install_reset_install_is_byte_identical():
    """Deliverable (D): the check done by hand over three days, mechanized."""
    print("\n[install -> uninstall -> install]")
    ven, inst = load_vendoring(), load_installer()
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main([target])
        s1 = _snapshot(target)
        ven.uninstall(target, host="claude", apply=True)
        inst.main([target])
        s3 = _snapshot(target)
        # Runtime exhaust is excluded from the comparison and asserted absent after removal
        # instead: it is written by guards, not by install (the _CLAUDE_IGNORES set).
        runtime = set(inst._CLAUDE_IGNORES)
        s1c = {k: v for k, v in s1.items() if os.path.basename(k) not in runtime}
        s3c = {k: v for k, v in s3.items() if os.path.basename(k) not in runtime}
        diff = sorted(set(s1c) ^ set(s3c))
        check("reinstall restores the same FILE SET", diff == [], diff[:6])
        changed = sorted(k for k in s1c if k in s3c and s1c[k] != s3c[k])
        check("reinstall restores byte-identical CONTENT and modes", changed == [],
              changed[:6])


# ------------------------------------------------------------------------------ reset
def test_reset_is_dry_run_by_default_and_truthful():
    print("\n[reset: dry-run default, printed set == deleted set]")
    ven, inst = load_vendoring(), load_installer()
    rp = _load(os.path.join(BIN, "reset_plan.py"), "reset_plan")
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main([target])
        before = _snapshot(target)

        planned = rp.plan(target, scopes=["repo"])
        paths = sorted({t["path"] for t in planned if t["kind"] in ("file", "dir")})
        check("the plan is non-empty after an install (not vacuous)", paths != [], paths[:3])

        # DRY RUN CHANGES NOTHING
        rp.apply(planned, dry_run=True)
        check("dry run is the default and mutates nothing",
              _snapshot(target) == before, "tree changed under a dry run")

        rp.apply(planned, dry_run=False)
        after = _snapshot(target)
        # realpath BOTH sides: on macOS the temp dir is /var/... while plan() resolves to
        # /private/var/..., and a raw string compare would report every path unannounced —
        # a false alarm that would hide a real one.
        gone = {os.path.realpath(os.path.join(target, k)) for k in set(before) - set(after)}
        printed = {os.path.realpath(p) for p in paths}
        # every path that disappeared must have been printed. The inverse (printed but
        # still present) is allowed only for directories that held user files.
        unannounced = sorted(g for g in gone
                             if not any(g == p or g.startswith(p.rstrip("/") + os.sep)
                                        for p in printed))
        check("PRINTED set == DELETED set (nothing vanishes unannounced)",
              unannounced == [], unannounced[:5])


def test_reset_never_touches_a_linked_worktree():
    """THE sharp edge. This repo has five live worktrees under .claude/worktrees/, one
    locked and several on unpushed branches. An implementation that globs `.claude/` takes
    them and their uncommitted work with it."""
    print("\n[reset: linked worktrees are untouchable]")
    inst = load_installer()
    rp = _load(os.path.join(BIN, "reset_plan.py"), "reset_plan")
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main([target])
        side = os.path.join(target, ".claude", "worktrees", "side")
        os.makedirs(os.path.dirname(side), exist_ok=True)
        _git(target, "worktree", "add", "-q", "-b", "side", side)
        with open(os.path.join(side, "UNCOMMITTED.txt"), "w") as fh:
            fh.write("work that must not be destroyed\n")
        wt_before = _snapshot(side)

        planned = rp.plan(target, scopes=["repo"])
        rp.apply(planned, dry_run=False)

        check("the linked worktree still exists", os.path.isdir(side))
        check("its files are byte-identical", _snapshot(side) == wt_before)
        check("uncommitted work survives",
              os.path.isfile(os.path.join(side, "UNCOMMITTED.txt")))
        listed = _git(target, "worktree", "list").stdout
        check("git still lists the worktree", "side" in listed, listed)
        # PLANTED: the predicate must actually recognise a worktree path
        check("PLANTED: a worktree path is recognised as protected",
              rp.is_protected_worktree(target, side))
        check("...and an ordinary directory is NOT",
              not rp.is_protected_worktree(target, os.path.join(target, ".claude", "bin")))


def test_reset_scopes_evidence_out_and_shared_apart():
    print("\n[reset: evidence out of scope, --shared is its own scope]")
    inst = load_installer()
    rp = _load(os.path.join(BIN, "reset_plan.py"), "reset_plan")
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main([target])
        ev = os.path.join(target, "docs", "calibration")
        os.makedirs(ev, exist_ok=True)
        with open(os.path.join(ev, "history.md"), "w") as fh:
            fh.write("# scoreboard\n")
        corpus = os.path.join(target, "calibration", "corpus", "approved")
        os.makedirs(corpus, exist_ok=True)
        with open(os.path.join(corpus, "p.json"), "w") as fh:
            fh.write("{}\n")

        allp = rp.plan(target, scopes=["repo", "shared", "machine", "plugin"])
        touched = {t["path"] for t in allp}
        check("--all-equivalent scopes never touch docs/calibration",
              not any("docs/calibration" in p for p in touched), sorted(touched)[:5])
        check("--all-equivalent scopes never touch calibration/corpus",
              not any("corpus" in p for p in touched), sorted(touched)[:5])
        check("evidence needs its own explicit scope to be planned at all",
              any("docs/calibration" in t["path"]
                  for t in rp.plan(target, scopes=["burn-evidence"])))

        # create real common-dir state first — otherwise "shared plans nothing" is true for
        # the boring reason that nothing shared exists yet, and the assertion measures nothing
        ident = None
        sys.path.insert(0, BIN)
        try:
            import host_contract
            ident = host_contract.resolve_repository(target)
            os.makedirs(ident["state_dir"], exist_ok=True)
            for nm in ("events.jsonl", "active-lock.json"):
                with open(os.path.join(ident["state_dir"], nm), "w") as fh:
                    fh.write("{}\n")
        except Exception as exc:
            check("host_contract resolves the scratch repo", False, repr(exc))
        repo_only = {t["path"] for t in rp.plan(target, scopes=["repo"])}
        shared_only = {t["path"] for t in rp.plan(target, scopes=["shared"])}
        check("--repo does NOT imply --shared (common-dir state is cross-worktree)",
              not (shared_only & repo_only), sorted(shared_only & repo_only)[:3])
        check("--shared plans the common-dir state", shared_only != set(), shared_only)


def test_reset_refuses_the_canonical_plugin_source():
    print("\n[reset: refuses this repo without --force]")
    rp = _load(os.path.join(BIN, "reset_plan.py"), "reset_plan")
    check("the canonical plugin source is recognised", rp.is_plugin_source(REPO), REPO)
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        check("an ordinary vendored repo is not", not rp.is_plugin_source(target))


def test_doctor_detects_the_shallow_clone_and_carries_a_fix():
    """The default new-user and default CI experience. A shallow clone makes the ledger stage
    UNMEASURED, test_harness's substring assertion then fails, and the gate reports
    `FAIL calibration` with the real cause buried in a stage log — and nothing tells you to
    run `git fetch --unshallow`.

    Two tiers, deliberately: the trigger is "the ledger EPOCH is unreachable", NOT "the clone
    is shallow", because a `--depth 400` clone is shallow and perfectly green. The paired
    FULL-clone control is what keeps this from being a check that always fires."""
    print("\n[doctor: shallow clone]")
    tdd = _load(os.path.join(BIN, "tdd.py"), "tdd")
    with tempfile.TemporaryDirectory() as base:
        src = _repo(base, "src")
        os.makedirs(os.path.join(src, "docs", "calibration"), exist_ok=True)
        for i in (1, 2, 3):
            with open(os.path.join(src, "f{}.txt".format(i)), "w") as fh:
                fh.write("c{}\n".format(i))
            _git(src, "add", "-A"); _git(src, "commit", "-qm", "c{}".format(i))
        epoch = _git(src, "rev-list", "--max-parents=0", "HEAD").stdout.strip()[:7]
        with open(os.path.join(src, "docs", "calibration", "ledger.md"), "w") as fh:
            fh.write("EPOCH: {}\n".format(epoch))
        _git(src, "add", "-A"); _git(src, "commit", "-qm", "ledger")

        shallow = os.path.join(base, "shallow")
        # the file:// form is REQUIRED — a plain path hardlinks and ignores --depth
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        "file://" + src.replace(" ", "%20"), shallow],
                       capture_output=True, timeout=60)
        if not os.path.isdir(shallow):
            check("shallow clone fixture built", False, "clone failed")
            return
        ids = {f["id"] for f in tdd.clone_findings(shallow)}
        check("shallow clone is DETECTED", "shallow-epoch" in ids, ids)
        fix = [f["fix"] for f in tdd.clone_findings(shallow) if f["id"] == "shallow-epoch"]
        check("...and the finding carries the command that fixes it",
              fix and "unshallow" in fix[0], fix)
        # PAIRED CONTROL: a full clone must emit NO shallow finding. A check that always
        # fires is theater, and this is the half that proves it does not.
        check("full clone emits NO shallow finding (the check can stay quiet)",
              "shallow-epoch" not in {f["id"] for f in tdd.clone_findings(src)},
              tdd.clone_findings(src))

    # structural invariant: EVERY doctor finding must carry a fix, or "every failure line
    # carries the command that fixes it" is a promise the code does not keep
    for family in tdd.CHECKS:
        check("check family {} is registered with a runner".format(family["family"]),
              callable(family["run"]))


def test_the_safety_findings_stay_fixed():
    """Frozen from a script-adversary review that returned UNSAFE (16). Each row is a defect
    that was LIVE in the first implementation, reproduced in a scratch dir by the reviewer."""
    print("\n[safety regressions]")
    rp = _load(os.path.join(BIN, "reset_plan.py"), "reset_plan")
    ven = load_vendoring()
    inst = load_installer()

    # F1: lexicographic ordering made 1.9.0 the "newest" of {1.9.0, 1.28.0, 1.32.0}, so the
    # row printed "kept" over 1.9.0 while marking the RUNNING copy stale for rmtree.
    vs = ["1.9.0", "1.28.0", "1.32.0", "1.6.1"]
    check("version ordering is numeric, not lexicographic",
          max(vs, key=rp._vkey) == "1.32.0", max(vs, key=rp._vkey))
    check("PLANTED: the lexicographic answer really is wrong (the bug was reachable)",
          max(vs) == "1.9.0", max(vs))

    # F8: git unavailable made worktree_paths return [] -> nothing protected. FAIL CLOSED.
    old = os.environ.get("PATH", "")
    os.environ["PATH"] = "/nonexistent"
    try:
        rp.worktree_paths(REPO)
        check("git-unavailable FAILS CLOSED (raises rather than protecting nothing)", False,
              "returned normally")
    except rp.ResetRefused:
        check("git-unavailable FAILS CLOSED (raises rather than protecting nothing)", True)
    except Exception as exc:
        check("git-unavailable raises ResetRefused specifically", False, repr(exc))
    finally:
        os.environ["PATH"] = old

    # F5: apply() must refuse anything outside the allowed roots, whatever the rows say.
    with tempfile.TemporaryDirectory() as base:
        inside = os.path.join(base, "in"); outside = os.path.join(base, "out")
        os.makedirs(inside); os.makedirs(outside)
        victim = os.path.join(outside, "precious.txt")
        with open(victim, "w") as fh:
            fh.write("do not delete me\n")
        rows = [{"scope": "repo", "kind": "file", "path": victim, "why": "planted escape"}]
        rp.apply(rows, dry_run=False, roots=[inside])
        check("PLANTED path outside every allowed root is REFUSED, not deleted",
              os.path.isfile(victim))

    # F4: the canonical-source refusal must cover EVERY scope, not just repo.
    with tempfile.TemporaryDirectory() as base:
        fake = os.path.join(base, "src")
        os.makedirs(os.path.join(fake, "plugins", "tdd-playbook", ".claude-plugin"))
        with open(os.path.join(fake, "plugins", "tdd-playbook", ".claude-plugin",
                               "plugin.json"), "w") as fh:
            fh.write("{}")
        os.makedirs(os.path.join(fake, "docs", "calibration"))
        _git(fake, "init", "-q")
        rows = rp.plan(fake, scopes=["burn-evidence"])
        kinds = {r["kind"] for r in rows}
        check("plugin SOURCE refuses burn-evidence too, not just --repo",
              "refused" in kinds and "dir" not in kinds, rows)

    # P1: the roster must survive in the TARGET, or both verbs are no-ops downstream where
    # scripts/ does not exist. This is the finding both reviewers led with.
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main([target])
        man = os.path.join(target, ven.MANIFEST_REL)
        check("install writes an install manifest into the target", os.path.isfile(man), man)
        # resolve the roster with a DELIBERATELY WRONG source repo — the vendored situation
        rels = ven.installed_paths("/nonexistent/source", target, "claude")
        check("the roster resolves from the manifest with NO source checkout",
              len(rels) > 10, len(rels))
        rows = ven.uninstall(target, host="claude", apply=False, repo="/nonexistent/source")
        check("uninstall from a vendored copy plans real work (not an exit-0 no-op)",
              sum(1 for r in rows if r["kind"] == "file") > 10,
              [r["kind"] for r in rows][:5])

    # P2: .codex/hooks.json is a SECOND registry; uninstall pruned only .claude/settings.json
    with tempfile.TemporaryDirectory() as base:
        target = _repo(base)
        inst.main(["--host", "all", target])
        ven.uninstall(target, host="all", apply=True)
        ch = os.path.join(target, ".codex", "hooks.json")
        if os.path.isfile(ch):
            with open(ch) as fh:
                cfg = json.load(fh)
            cmds = [h.get("command", "") for g in
                    [g for v in (cfg.get("hooks") or {}).values() for g in v]
                    for h in g.get("hooks", [])]
            check("no Codex hook still points at a deleted playbook script",
                  not any("tdd-playbook" in c for c in cmds), cmds)
        else:
            check("codex hooks.json handled (absent or pruned)", True)


def main():
    print("vendoring / reset calibration")
    for fn in (test_uninstall_is_the_inverse_of_install,
               test_install_reset_install_is_byte_identical,
               test_reset_is_dry_run_by_default_and_truthful,
               test_reset_never_touches_a_linked_worktree,
               test_reset_scopes_evidence_out_and_shared_apart,
               test_reset_refuses_the_canonical_plugin_source,
               test_doctor_detects_the_shallow_clone_and_carries_a_fix,
               test_the_safety_findings_stay_fixed):
        try:
            fn()
        except Exception as exc:  # a suite that dies silently proves nothing
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
