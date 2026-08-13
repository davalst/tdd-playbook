---
description: Render the Readable Surface — what this system IS, organised by worry, in plain language, for the reader who doesn't fall back to source. Facts are mechanical and cited; narration never gates. `/readable S17` answers one inventory scenario against the current tree.
argument-hint: [S-row id, e.g. S17 — default: all worry pages]
---

Render the **readable surface** for: $ARGUMENTS (default: every worry page).

This is DESCRIPTION, not a verdict — the one Playbook output whose job is to answer
"what is it?" for a reader who cannot walk into the source. The facts are mechanical; your
narration is prose ABOUT them. **Prose never gates**: this command has no exit-code
consumer and joins no gate stage, and it must NEVER dispatch a paid adversary itself —
an auto-spent adversary from a description command is inventory row S23 ("an expensive
path with no limit"), dogfooded. You may RECOMMEND one; the human spends.

**1. Derive the facts (mechanical, cited):**

    python3 "${CLAUDE_PLUGIN_ROOT}/bin/readable_surface.py" facts $ARGUMENTS

Every row carries a `file:line` citation. If it refuses with exit 3, the repo has no
capability registry — relay the init instruction verbatim; never narrate an empty page as
"nothing here."

**2. Narrate the change or the page in plain sentences** — the reader's questions, not the
code's nouns. Every sentence that carries a claim must cite a fact the tool printed
(`file:line`). A scenario whose Facts column is `—` gets the honest answer the tool
prints: no mechanical facts — name the Route agent as the next step, and stop there.

**THE BUSINESS-OWNER TEST, applied sentence by sentence before presenting** (added after
the surface's first real read failed its only reader — the facts were fine, the narration
was repo idiom, and the reader had to ask for plain English again): if a sentence would
not make sense to a smart business owner who cannot read code, rewrite it. Say "nothing
will tell you if this breaks", never "no liveness probe". Say "a rule that's written down
but switched off", never "declared unarmed". Say "things you run by hand", never
"opt-in CLI surfaces". Citations go at the END of a section or stay in the mechanical
output — never mid-sentence, where they break the reading. Shorter is plainer: cut before
explaining. Repo idiom in the narration is a FAILURE of this command even when every fact
is correct — readability is the deliverable, not polish on it.

**3. MECHANICAL GATE on your own narration (the workflow, because Markdown cannot refuse):**
run the citation check over what you are about to present, BEFORE presenting it:

    python3 "${CLAUDE_PLUGIN_ROOT}/bin/readable_surface.py" facts $ARGUMENTS | \
      python3 "${CLAUDE_PLUGIN_ROOT}/bin/verify_citations.py" - --base .

and verify your narration's citations the same way. **Zero citations is the vacuity hole**
in the reused gate (`verify_citations` exits 0 on a scan of nothing): require `Citations:
N` with N ≥ 1 per worry page you narrate, and PASTE the tool's summary line so the count
is auditable — a self-reported "N/N" is narration with a colon in it. An uncitable
sentence is cut, not hedged.

**4. If nothing changed since the reader last looked, say exactly that** — "nothing
changed" as an explicit line, never silence.

**Afterwards (the R&D loop, one line, honest):** if reading the surface led you (the
human) to dispatch an adversary or change a decision, record it —

    python3 "${CLAUDE_PLUGIN_ROOT}/bin/gate_yield.py" usage-note --scenario <S-row|full> \
      --dispatched yes|no --changed-a-decision yes|no

The machine already counted the use; the note is self-report and can never move the
count. The keep/kill call on this whole surface (2026-09-30) reads that record.
