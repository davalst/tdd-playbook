#!/usr/bin/env python3
"""Generate AGENTS.md from CLAUDE.md — a curated header plus the doctrine VERBATIM.

WHY GENERATED. AGENTS.md is the Codex agent-instructions convention and this repo reads it
(gate-manifest.json, hooks/scripts/intent_nudge.py). It was hand-maintained as a mirror and
it rotted exactly as hand-maintained mirrors do: by 2026-08-10 it still carried the
PRE-v1.32.0 calibration section — "calibration is not optional", the 14-day clock, the
staleness release gate — every word of which had been reversed days earlier. A reader
following it would have done the opposite of current doctrine.

WHY NOT A TRANSFORM. The previous mirror was produced by a Claude->Codex find-replace, which
left `.Codex/settings.json` (Codex uses lowercase `.codex/`) and "a real `Codex` binary"
where calibration needs the CLAUDE cli on every host. A substitution pass over prose cannot
know which occurrences are host names and which are product names, and it fails silently —
so this does not transform the body at all. The doctrine is HOST-NEUTRAL and is copied byte
for byte; the genuinely host-specific facts are a short curated list that a human maintains
deliberately, right here, where they are visible.

The invariant a test pins: committed AGENTS.md == render(). Edit CLAUDE.md or HOST_NOTES,
then re-render. A hand edit to AGENTS.md is a gate failure, not a merge conflict later.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
SOURCE = os.path.join(REPO, "CLAUDE.md")
TARGET = os.path.join(REPO, "AGENTS.md")

BANNER = (
    "<!-- GENERATED FILE — do not edit by hand.\n"
    "     Source: CLAUDE.md + HOST_NOTES in plugins/tdd-playbook/bin/render_agents.py\n"
    "     Regenerate: python3 plugins/tdd-playbook/bin/render_agents.py render\n"
    "     A hand edit fails the gate (test_reference_docs), it does not merge quietly. -->\n"
)

# The ONLY host-specific facts. Everything below the rule is CLAUDE.md verbatim, because the
# doctrine does not change per host — only where files land and which guards are wired do.
HOST_NOTES = """# AGENTS.md — Codex instructions for the TDD Playbook repo

This repo's engineering doctrine is host-neutral and lives in `CLAUDE.md`. It is reproduced
below **verbatim** so the two can never disagree. Only the facts in this section differ when
the host is Codex rather than Claude Code.

## What differs on Codex

- **Vendored install path.** Codex assets land in `.codex/tdd-playbook/` (lowercase), not
  `.claude/`. Install with `python3 scripts/install_into_repo.py --host codex <repo>`, or
  `--host all` for a repo used from both.
- **Guard coverage is PARTIAL and that is deliberate, not an oversight.** Only
  `lock_guard` has a Codex adapter (`adapters/codex/pre_tool_test_lock.py`). Every other
  guard — including `tag_guard`, which reserves release tags for the owner — is `unavailable`
  on Codex per `docs/architecture/host-parity-policy.json`, tracked as dated debt on the
  `test-lock` capability. So on Codex the session-side half of release-tag authority is
  ABSENT: the tracked-script scanner still applies, the Bash-seam guard does not.
- **Codex config is trust-gated by the host.** Review the generated project hook, trust the
  repository and the hook when prompted, then run
  `python3 .codex/tdd-playbook/bin/tdd.py doctor`. A file existing is not proof of
  activation — the adapter reports prevention only after a real-host planted block and its
  paired clean control have been recorded.
- **`claude` is a product name, not a host name.** Where the doctrine below says a step needs
  "a real `claude` binary" — calibration, the headless doer — it means the Claude CLI, on
  every host including this one. That is not a stale reference to fix; an earlier
  hand-maintained mirror "corrected" it to "Codex binary" and made the instruction wrong.

---

"""


def render():
    with open(SOURCE) as fh:
        doctrine = fh.read()
    # Drop only the source's own H1; HOST_NOTES supplies the title.
    lines = doctrine.splitlines(True)
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return BANNER + HOST_NOTES + "".join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "check"
    want = render()
    have = open(TARGET).read() if os.path.isfile(TARGET) else None
    if cmd == "render":
        with open(TARGET, "w") as fh:
            fh.write(want)
        print("AGENTS.md: rendered from CLAUDE.md ({} bytes)".format(len(want)))
        return 0
    if have == want:
        print("AGENTS.md: PASS — generated file matches CLAUDE.md + HOST_NOTES")
        return 0
    sys.stderr.write(
        "AGENTS.md: STALE — it no longer equals CLAUDE.md + HOST_NOTES.\n"
        "  Regenerate: python3 plugins/tdd-playbook/bin/render_agents.py render\n"
        "  (If you edited AGENTS.md by hand, move the change into CLAUDE.md or HOST_NOTES —\n"
        "   a hand-maintained mirror is what rotted this file into contradicting doctrine.)\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
