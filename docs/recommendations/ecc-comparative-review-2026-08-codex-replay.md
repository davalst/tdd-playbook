# Codex replay protocol — ECC comparative review, 2026-08-31

**Why this file exists.** David asked for the same review to be run by Codex and the two
answers compared. **Codex could not be run in the session that produced
`ecc-comparative-review-2026-08.md`** (blockers below, both verified). Rather than skip the
comparison or simulate it, this file freezes the replay so it can be run later and graded
honestly.

**The load-bearing property: the scoring rule is committed BEFORE any Codex output exists.**
A comparison graded after both answers are on the table is graded by whoever holds the pen —
and here that would be the author of one of the two answers. Same reasoning as the D3 scoring
rule committed on `main` at `fe5a519`. If this file is edited after a Codex run, the edit
is visible in git and the comparison is void.

---

## Why it could not be run here

Both checked, both fatal on their own:

1. **No credentials.** No `OPENAI_API_KEY` in the environment, no `~/.codex`, no
   `~/.config/openai`. (`@openai/codex` itself resolves fine on the registry — 0.151.0 — so
   the package is not the problem.)
2. **Egress blocked.** `curl https://api.openai.com/v1/models` returns
   `CONNECT tunnel failed, response 403` from the session's agent proxy.

Neither is fixable from inside the sandbox, and neither should be worked around.

**What was NOT done, stated plainly:** no Codex output was generated, approximated, predicted,
or stood in for by another Claude agent. There is no comparison result in this repo yet.
A Claude subagent is not a Codex replay and swapping one in silently would answer a different
question than the one asked.

---

## Run it

Run this **on `main`, not on the review branch** — `git checkout main` first. The review
document lives on `claude/ecc-repo-best-practices-09kouy`, and a Codex run that can read it is
not an independent second opinion. Verify before starting:

```bash
git rev-parse --abbrev-ref HEAD          # expect: main
ls docs/recommendations/ | grep ecc      # expect: NO ecc-comparative-review-2026-08.md
```

Give Codex the same two things this session had — the playbook repo as cwd, and a clone of ECC:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/affaan-m/ecc /tmp/ecc-replay
git -C /tmp/ecc-replay checkout 005eff40fd4a4ac005da7a70e713459175385516
```

Pinning that sha matters: ECC ships weekly, and a Codex run against a later tree would be
scored against claims verified on an earlier one. A drifted sha is a void replay, not a
disagreement.

Then, from the playbook repo root, the **verbatim question David asked** — not a paraphrase,
and with no hint that a prior review exists:

> Deeply review this repo and compare it to ours and see what best practice patterns could
> help improve us (verify your claims). /tmp/ecc-replay is a clone of
> https://github.com/affaan-m/ECC

Save the transcript to `docs/recommendations/ecc-codex-replay-output.md` and commit it
UNEDITED before scoring anything.

---

## Pre-registered scoring rule

Score both reviews on the same six axes. Three of the six can only ever cost the Claude
review points; that asymmetry is deliberate, because the Claude review is the incumbent and
an incumbent that cannot lose is not being tested.

| # | Axis | How it is scored | Who it can hurt |
|---|------|------------------|-----------------|
| S1 | **Claims that hold** | Re-run each review's verification commands. A claim counts only if the command reproduces the stated result. | both |
| S2 | **Claims that are false** | Any claim whose command contradicts it. Weighted 3x — a confident wrong claim is worse than a missing one. | both |
| S3 | **Claims asserted without a check** | Load-bearing statements with no command, file:line, or run behind them. | both |
| S4 | **Real findings the other review missed** | A finding is "real" only if a command confirms it. | both |
| S5 | **Findings that do not survive** | A recommendation resting on something the tree contradicts. | both |
| S6 | **Honest about its own gaps** | Does it name what it could NOT check, and mark bounded searches as bounded rather than as proof of absence? | both |

**Adjudication is mechanical where it can be.** S1, S2, S4 and S5 are settled by running
commands, not by reading prose. S3 and S6 need a human read. If an axis cannot be settled
mechanically, record it as unsettled rather than resolving it by preference.

**A disagreement is not automatically a Claude error and not automatically a Codex error.**
Run the command. If neither review's command settles it, that is an S3 hit against whichever
review made the claim.

---

## The incumbent's claims, frozen for scoring

These are the fourteen from `ecc-comparative-review-2026-08.md`, restated as commands so
they can be re-run against the same two trees. If a Codex run contradicts one of these, run
the command — do not adjudicate by argument.

| # | Claim | Command that settles it |
|---|-------|--------------------------|
| C1 | ECC catalog is 68 agents / 94 commands / 286 skills | `node scripts/ci/catalog.js --text` in the ECC clone |
| C2 | ECC's `SOUL.md` claims 30/135/60 and is NOT one of catalog.js's checked files | `grep -n "30 specialized" SOUL.md; grep -n "SOUL" scripts/ci/catalog.js` |
| C3 | `check-unicode-safety.js` blocks the U+E0000–E007F tag block | `grep -n "0xE0000" scripts/ci/check-unicode-safety.js` |
| C4 | Its test plants violations into a temp root | `grep -n "ECC_UNICODE_SCAN_ROOT" tests/scripts/check-unicode-safety.test.js` |
| C5 | This repo has no unicode/smuggling check | `grep -rn "200B\|FEFF\|E0000\|homoglyph" plugins/ calibration/ scripts/` — hits must all be English prose |
| C6 | This repo's tree currently contains zero such code points | the code-point scan in the review's method note |
| C7 | `_DEFAULT_MODES` is 4 block / 4 off / 1 warn | import `_common.py`, `Counter(_DEFAULT_MODES.values())` |
| C8 | `README.md:251` says "4 blocking, 5 opt-in" | `sed -n '251p' README.md` |
| C9 | The roster pin windows `[start-30 : start+500]` and pins the count word only against `len(blocking)` | read `test_hooks.py:1356-1404` |
| C10 | `gate.yml` has no `persist-credentials` | `grep -n persist-credentials .github/workflows/gate.yml` |
| C11 | `.github/` has no `dependabot.yml` | `ls -a .github/` |
| C12 | ECC's skills validator warns unless `--strict`, which CI never passes | `grep -rn "CI_STRICT_SKILLS\|--strict" .github/workflows/ package.json` |
| C13 | `validate-workflow-security.js` is in CI and absent from `npm test` | `grep -c validate-workflow-security package.json` (expect 0) |
| C14 | No calibration/planted-defect harness found in ECC | **bounded search, not proof of absence** — the one claim the incumbent already flagged as refutable |

C14 is the incumbent's most refutable claim and the cheapest place for a Codex run to score
an S4. That is the point of listing it.

---

## What a good outcome looks like

Not "Claude won." The replay is worth running if it produces any of:

- an S4 against the incumbent — a real ECC pattern the first review did not surface;
- an S2 against the incumbent — a claim that does not reproduce;
- agreement on R1 (doctrine-compliance measurement) from an independent path, which would
  raise confidence that it is the right thing to build;
- **disagreement on R1**, which is more interesting still, since R1 is the only proposal
  large enough to be worth being wrong about.

Two reviews agreeing on the four small verified defects tells you almost nothing — those were
found by running commands, and any competent reviewer running the same commands finds them.
The signal is in what only one of the two saw.
