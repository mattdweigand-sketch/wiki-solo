---
name: wiki-synthesize
description: Use this workflow to run an ongoing synthesis pass over the corpus - draft distilled pages and sections at draft/low confidence, surface them for review, and promote only what the user approves.
---

# Synthesize Workflow

Turns accumulated corpus into distilled, reviewable synthesis on an ongoing basis. Ingest brings material in; lint finds defects; this workflow writes the connective tissue: refreshed overview synthesis, missing open-questions sections, cluster distillations, and resolutions to questions newer pages have since answered.

The core contract is the draft-then-grade loop. Synthesis is judgment that future agents may consume as context, so all synthesized content lands with its epistemic state in-band: `confidence: low` where frontmatter applies, and `status: draft` on meta pages that carry a status field. User review is the grade. Only explicit approval flips the markers, and the flip is logged as a promotion.

## Load / Skip

- **Load:** `wiki/synthesis.md` first, full `python3 scripts/lint.py` output, `wiki/log.md` entries since the last `synthesis` entry, `wiki/index.md`, `wiki/overview.md`, and only the candidate pages the signals point to. At drafting time: `wiki/SCHEMA.md` and `REFERENCES.md`.
- **Skip:** `raw/` sources, archived harness scripts, and entity folders the candidates do not touch.

## Synthesis Targets

1. **Domain meta synthesis.** Refresh `wiki/overview.md` when newer pages change what the wiki says about the organization, product surface, market, customer patterns, operating priorities, or unresolved strategic questions.
2. **Per-page gap analysis.** Add, deepen, or resolve `Open questions / gaps` sections on pages where the corpus now contains enough evidence to say something useful.
3. **Undistilled clusters.** Draft a concept or analysis only when three or more pages repeatedly cohere around a useful distinction that no page currently names.
4. **Primer drift.** Update `wiki/primer.md` when the best entry points for common question types have changed.

## Rules

- Everything drafted lands at `confidence: low`; meta pages with a `status:` field also get `status: draft`.
- Never silently overwrite verified content. Anything that conflicts with what a page already says gets flagged in `wiki/contradictions.md` first.
- Bound each run to at most 5 drafts.
- Drafting a new `wiki/analyses/` page is the analysis-capture route: run `python3 scripts/capture_gate.py` first and stop at `APPROVAL REQUIRED`.
- Ground every claim in cited pages. Synthesis combines what the corpus says; it never adds facts the corpus does not contain.
- Cite original pages, never the ledger. `wiki/synthesis.md` is for orientation and drift tracking only.

## Steps

1. Read `wiki/synthesis.md`, then run `python3 scripts/lint.py` and read `wiki/log.md` since the last `synthesis` entry. Build the candidate list from the targets above.
2. Pick the batch, up to 5 drafts. For each candidate, name in one sentence what the draft will add and which pages ground it.
3. Draft, following `wiki/SCHEMA.md` and `REFERENCES.md`. New pages get index rows.
4. Run:

   ```bash
   python3 scripts/rebuild_referenced_by.py
   python3 scripts/lint.py --tier1
   ```

5. Report in chat: each draft, its grounding, and where it sits. Stop. Drafts stay at draft/low until reviewed.
6. On approval, flip `confidence:` and `status:` where appropriate, then log a `promotion` entry. On rejection, revert or rework.
7. Update the ledger as part of the approved run: refresh Current state digest lines that changed and append a run entry recording drafts, approvals, rejections, questions opened and closed, sections reshaped, and ingests that drove the change.
8. Append to `wiki/log.md`:

```text
## [YYYY-MM-DD] synthesis | <short batch description>
Candidates considered: <count, with the signals that produced them>
Drafts written: <pages, each with one-line grounding>
Held at draft/low pending review: <pages>
Promoted after review: <pages or none>
Verification: rebuild_referenced_by.py and lint.py --tier1 passed
```

## Cadence

Run after every burst of related ingests with no distillation following them, or when lint surfaces recurring cross-reference and gap signals.
