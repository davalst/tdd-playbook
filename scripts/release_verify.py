#!/usr/bin/env python3
"""release_verify — the EXECUTABLE half of the CIVerd release gate (audit finding F4, decision D5).

civerd-plan §5: "no version bump ships without a signed engine verdict for the release SHA." That
is only a CONTROL if a step runs it and cannot proceed without exit 0 — a checklist line saying
"remember to verify" is a wish an adversarial session rationalises past (the same reason
verify_verdict has no --force). So the release tag is created ONLY here, ONLY after the shipped
`verify_verdict.py` returns 0 for the exact release SHA.

CIVerd signs a verdict AFTER a commit lands (it notices the push, clones at that SHA, runs the
gate, signs). So this gates the *release SHA you actually ship* — not its parent (Option 2's hole:
the parent skips the bump commit, which the agent itself writes — precisely the adversary). Usage:

    scripts/release_verify.py                       # verify HEAD, tag v<plugin.json version>
    scripts/release_verify.py --wait-s 900          # poll until CIVerd publishes (verdicts are async)
    scripts/release_verify.py --dry-run             # verify + report the tag it WOULD create
    scripts/release_verify.py --ledger PATH         # offline verify against a local ledger (tests)

Exit 0 = verified and (unless --dry-run/--no-tag) tag created & pushed. Exit 1 = REFUSED (no green
verdict) — no tag. Exit 2 = bad invocation. This lives in scripts/ (not vendored): it releases THIS
repo; downstream repos' gates are CIVerd-plan P3.
"""
import argparse
import json
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY_BIN = os.path.join(REPO, "plugins", "tdd-playbook", "bin", "verify_verdict.py")
PLUGIN_JSON = os.path.join(REPO, "plugins", "tdd-playbook", ".claude-plugin", "plugin.json")


def _git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)


def _head_sha():
    r = _git("rev-parse", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else None


def _plugin_version():
    with open(PLUGIN_JSON) as fh:
        return json.load(fh)["version"]


def verify_once(sha, max_age_s, ledger=None):
    """Invoke the SHIPPED verify_verdict.py exactly as a release would. Returns (ok, output)."""
    cmd = [sys.executable, VERIFY_BIN, "--sha", sha, "--max-age-s", str(max_age_s)]
    if ledger:
        cmd += ["--ledger", ledger]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return (p.returncode == 0, (p.stdout + p.stderr).strip())


def verify_with_wait(sha, max_age_s, ledger, wait_s, poll_s, sleep=time.sleep, clock=time.monotonic):
    """Poll verify_once until green or the deadline. `sleep`/`clock` are injectable so tests never
    sleep on the real clock (Playbook determinism rule)."""
    deadline = clock() + wait_s
    while True:
        ok, out = verify_once(sha, max_age_s, ledger)
        if ok or clock() >= deadline:
            return ok, out
        sleep(poll_s)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="release_verify.py", description=__doc__.splitlines()[0])
    ap.add_argument("--sha", default=None, help="release commit SHA (default: HEAD)")
    ap.add_argument("--tag", default=None, help="tag to create (default: v<plugin.json version>)")
    ap.add_argument("--max-age-s", type=int, default=86400)
    ap.add_argument("--ledger", default=None, help="local ledger (offline/tests); default fetches")
    ap.add_argument("--wait-s", type=int, default=0, help="poll up to N s for an async verdict")
    ap.add_argument("--poll-s", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true", help="verify only; report the tag, don't create")
    ap.add_argument("--no-tag", action="store_true", help="verify only; never tag/push")
    # NOTE: intentionally no bypass flag. If verify is red, there is no path to a tag.
    args = ap.parse_args(argv)

    sha = args.sha or _head_sha()
    if not sha:
        print("release_verify: cannot resolve HEAD (not a git repo?)", file=sys.stderr)
        return 2
    tag = args.tag or "v{}".format(_plugin_version())

    ok, out = verify_with_wait(sha, args.max_age_s, args.ledger, args.wait_s, args.poll_s)
    print(out)
    if not ok:
        print("RELEASE REFUSED — no green signed verdict for {}; tag {} NOT created".format(
            sha[:12], tag), file=sys.stderr)
        return 1

    if args.dry_run or args.no_tag:
        print("VERIFIED {} — would create tag {} (skipped: {})".format(
            sha[:12], tag, "dry-run" if args.dry_run else "no-tag"))
        return 0

    r = _git("tag", "-a", tag, sha, "-m", "release {} (CIVerd-verified)".format(tag))
    if r.returncode != 0:
        print("verified, but tag failed: {}".format(r.stderr.strip()), file=sys.stderr)
        return 1
    push = _git("push", "origin", tag)
    if push.returncode != 0:
        print("tag {} created locally but push failed: {}".format(tag, push.stderr.strip()),
              file=sys.stderr)
        return 1
    print("RELEASE OK — {} verified and tagged {} (pushed)".format(sha[:12], tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
