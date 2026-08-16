# Calibration — proving the Playbook's own verifiers work

The Playbook's loudest rule is "a probe that never fails a plant is theater" (§13). This
directory applies that rule to the Playbook itself: the enforcement **hooks** are calibrated
by `plugins/tdd-playbook/tests/test_hooks.py` (deterministic, every run); the verification
**agents** are calibrated here (behavioral, scheduled — they need a live model).

Layout:
- `fixture/` — a tiny known-good Python package with tests; the arena the agents are
  dropped into. Deliberately boring: the *plants* provide the challenge.
- `scenarios.json` — the planted scenarios: for each agent, what is planted in the fixture
  and what the agent's forced `Recommendation:` / verdict line MUST name to pass.
- `run_calibration.py` — the runner. Applies a scenario's plant to a temp copy of the
  fixture, drives the agent headlessly (`claude -p`, cheap model, hard caps), and applies a
  DETERMINISTIC oracle: did the verdict line name the plant? (String check — no LLM judge;
  the oracle split applies to our own calibration too.)
- `corpus/` — the generative plant corpus (co-evolution): adversary-authored plants, added
  every cycle, never removed. Each plant records the model that authored it.

Cadence: **weekly** (scheduled), and mandatory after any agent-prompt change or doer-model
upgrade (§13 verifier-strength policy). **A plant surviving to a clean verdict is a BLOCKING
failure** — fix the agent (or the harness), never the plant. Results append to
`docs/calibration/history.md` — the public scoreboard.

Run: `python3 calibration/run_calibration.py [--agent NAME] [--repeat K] [--dry-run]`
(`--dry-run` validates scenarios/fixture/corpus + the R2 pairing invariant + the R1 agent-
coverage invariant — every calibratable agent needs a plant — without spending model calls;
used in CI.)

**Wall-clock budget (know it before a live run):** the loop is serial; the CAP is
scenarios × repeats × 600 s — at 30 × 3 that is ~15 h worst case (typical runs are far
below the cap, but investigation-heavy plants raise `max_turns`). History is written ONCE
at run end, so an interrupted run lands nothing: for long runs, chunk by agent
(`--agent mutation-runner`, then the next) so each chunk commits its own block. Each scenario runs `--repeat` times (default 3, §5a): `PASS` only
at k/k, `AMBER` on a partial catch (nonzero exit — no `--strict` flag to remember; AMBER on
consecutive runs promotes to BLOCKING mechanically), `**BLOCKING FAIL**` at 0/k. The run
header reports recall (plants) and FP (controls) as separate numbers.

## The private holdout (two-tier calibration)

The `corpus/` above is the **public, tunable** tier — plants live in this repo, so a Claude
verifier could in principle have seen them. The **holdout** is the second tier: a **private,
never-committed-here** answer key that the verifiers have never seen, so it measures them
without the leakage. `holdout.py` is the controller.

> ⚠️ **The name trap (this is why the repo has this section).** The private repo is
> **`https://github.com/davalst/tdd-playbook-holdout`**. The conventional LOCAL clone is
> **`~/tdd-holdout-vault`** — the directory name is NOT the repo name. `--vault-dir` wants
> the local path (`~/tdd-holdout-vault`); `run --vault` wants the **repo URL**
> (`.../tdd-playbook-holdout`). Passing the dir name as a URL fails `git clone` with exit
> 128. Confirm with `git -C ~/tdd-holdout-vault remote get-url origin`.

**Security invariant — never violated:** the holdout bodies/oracles are the answer key. They
must never enter this public repo, CI, a summary, or a Claude verifier's context. **A Claude
model (including whoever is helping author) must NOT read the proposed/ or bodies/ files** —
reading them contaminates the holdout's independence. The human reviews them; the tools only
ever print ids and fingerprints, never bodies.

**Grow the corpus** (author → review → approve → push). Run several `author` calls, each with
a DIFFERENT `--category`, to parallelise safely: ids are chosen from a snapshot taken at each
call's start, so same-category parallel runs can collide and silently overwrite — different
categories don't (and diversify the corpus):
```bash
# 1. author fresh plant+control pairs into the vault's proposed/ (opus authors harder plants)
python3 calibration/holdout.py author --vault-dir ~/tdd-holdout-vault --model opus --category "band-aid fix at the wrong seam"
#    categories: faked red-first · unwired deliverable · false negative claim · missing edge
#    coverage · vacuous/unmeasured mutation gate · band-aid fix at the wrong seam ·
#    island/dark-by-default plan · unsafe/passes-for-the-wrong-reason script probe

# 2. REVIEW the new files in ~/tdd-holdout-vault/proposed/ yourself (never ask a Claude model to)

# 3. approve the good ones — BOTH the plant AND its control, per pair
python3 calibration/holdout.py approve --vault-dir ~/tdd-holdout-vault <plant-id> --reason "..."
python3 calibration/holdout.py approve --vault-dir ~/tdd-holdout-vault <control-id> --reason "..."

# 4. commit + push the PRIVATE vault (approve moved them proposed/ -> bodies/ + the register)
git -C ~/tdd-holdout-vault add -A && git -C ~/tdd-holdout-vault commit -m "grow holdout corpus" && git -C ~/tdd-holdout-vault push
```

**Run the eval** — clones the vault FRESH from the URL (so approve→commit→**push** must
happen first), verifies integrity (drift + unregistered-body checks), scores, deletes the
clone:
```bash
python3 calibration/holdout.py run --vault https://github.com/davalst/tdd-playbook-holdout --model sonnet --summary
# --summary collapses the rollup wall to the glance-able dev-vs-holdout comparison.
# --vault also accepts a LOCAL path ("$HOME/tdd-holdout-vault") to skip auth — it still
# clones only COMMITTED content, so integrity verification is identical.
```
A dozen-ish approved pairs is where the recall/FP numbers start to mean something. Authoring
misses that report `edits-do-not-apply` (the model's edit `old` string didn't match the
fixture) are harmless — just re-run that category.
