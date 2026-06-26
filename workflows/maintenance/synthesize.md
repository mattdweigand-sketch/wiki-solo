---
name: wiki-synthesize
description: Use this workflow to run a bounded synthesis pass over the corpus: detect what the wiki now implies across pages, surface it as a reviewable memo with no file edits, and promote only what the user approves. Recommending "no change" is a valid outcome.
---

# Synthesize Workflow

Digestion, not ingestion. Ingest brings material in and wires each source into the pages it touches; lint finds defects; this workflow finds what the corpus now implies across several pages and surfaces it for the user to grade. It writes nothing before the user approves a draft or edit scope.

## Core Principle

A synthesis pass is only valuable when it can answer one question:

**What does the wiki now know that no single page says cleanly yet?**

If the honest answer is "nothing material," the pass stops and recommends no change. That is a successful run.

Division of labor:

1. **Primary target: the wiki's self-model.** `wiki/overview.md` and `wiki/primer.md` are cross-corpus judgments no single ingest has the scope to write. They must be drafted and graded, never auto-promoted.
2. **Secondary: genuinely emergent frameworks and cluster distillations.** Three or more pages that now support one conclusion with no page naming it.
3. **Backstop only: per-page "Open questions / gaps" sections.** Ingest writes and updates these in-band, and lint checks that they are present. The synthesize pass flags one only when ingest plainly missed it.

## Memo-Then-Draft-Then-Grade Contract

Every page in `wiki/` may be consumed by future agents with no human present at read time. Synthesized content carries its epistemic state in-band: `confidence: low` where frontmatter applies, and `status: draft` on meta pages that carry a status field. User review is the grade. Only explicit approval, recorded through `scripts/capture_gate.py --kind=synthesis`, flips those markers or records a synthesis promotion.

This workflow is memo-first:

1. The pass proposes candidates in chat with an evidence packet and classification.
2. The user approves which candidates are worth drafting or editing.
3. Approved edits land at draft/low unless the user explicitly graded the exact content.
4. Promotion, ledger updates, and confidence/status flips still stop at `scripts/capture_gate.py --kind=synthesis`.

## Load / Skip

- **Load:** `wiki/synthesis.md` (read Current state and the last few run entries first), recent synthesis records in `scripts/capture-runs.jsonl` when checking whether a prior synthesis scope was already approved, full `python3 scripts/lint.py` output, `wiki/log.md` entries since the last `synthesis` entry, `wiki/index.md`, `wiki/overview.md`, and only the candidate pages the detected signals point to. At drafting time, also load `wiki/SCHEMA.md` and `REFERENCES.md`.
- **Optional:** wiki source pages cited by candidate pages when source-page fidelity matters. Open raw files only when a source-page claim itself needs checking; synthesis normally distills wiki pages, not raw artifacts.
- **Skip:** the full wiki unless the candidate set genuinely cannot be narrowed, unrelated `raw/` sources, and entity folders the candidates do not touch.

## Candidate Signals

A page or cluster becomes a candidate when one of these is true:

- `wiki/overview.md`, `wiki/primer.md`, or `wiki/synthesis.md` no longer reflects the current corpus.
- A reusable framework has emerged from several sources with no page naming it.
- Three or more pages now support the same conclusion.
- Recent ingests modify or challenge an existing thesis.
- Multiple pages repeat the same unresolved question.
- A page is stale relative to a newer owner page it depends on.

One co-citation is not a cluster; a signal must recur before it is a candidate.

## Pass Size And Ranking

Keep a pass small: aim for about five high-signal items. If more surface, rank by:

1. Importance to the configured domain.
2. Usefulness to future agents.
3. Risk of stale or misleading context if left alone.
4. Number and quality of supporting pages.
5. Whether a durable home already exists.

A pass that would touch half the wiki is an audit, not a synthesis loop iteration.

## Allowed Outputs

A memo-first pass may produce:

- A chat-only synthesis memo.
- A proposed update list.
- A recommendation to draft a low-confidence page update.
- A recommendation to update `wiki/synthesis.md`.
- A recommendation to update `wiki/overview.md` or `wiki/primer.md`.
- A recommendation to do nothing.

It may not, without user approval, promote conclusions, flip confidence, update ledgers, rewrite durable pages, or resolve contradictions.

## Evidence Packet

Present one packet per candidate in chat before any edit:

```text
Candidate:
Pages consulted:
Claim now supported:
Why this matters:
Recommended home:
Proposed change:
Confidence:
Classification:
Approval needed:
```

Ground every claim in cited pages and include concise evidence snippets or citations for the support. Synthesis combines what the corpus says; it never adds a fact the corpus does not contain. Cite original pages, never `wiki/synthesis.md`: the ledger is for orientation and drift tracking only, and treating it as a source lets summaries silently replace the pages they summarize.

## Done Condition

The memo-first pass is done when every candidate is classified as one of:

- **Recommend draft** - worth drafting if the user approves the edit scope.
- **Defer** - real but not now; note why in the memo.
- **No change** - examined and rejected, with the reason.
- **Needs user judgment** - a fork only the user can call.
- **Needs more source material** - the corpus does not yet support it.

After the user approves a candidate, its classification becomes **Draft this** and the durable-edit flow below begins.

## Human Gates

The user must approve before:

- Creating a new `wiki/analyses/` page.
- Drafting or changing `wiki/overview.md`, `wiki/primer.md`, or other core framing pages.
- Updating `wiki/synthesis.md`.
- Flipping draft/low content to approved confidence.
- Resolving a contradiction.
- Turning a synthesis into a durable workflow rule.

Never silently overwrite verified content. Additions to an existing page go in clearly bounded sections; anything that conflicts with what a page already says is flagged in `wiki/contradictions.md` first. When refreshing overview, primer, index, or the synthesis digest, do not copy volatile current-state values from owner pages; name the thread and link the owner page.

## Durable-Edit Flow After Approval

1. If the user approves drafting a new `wiki/analyses/` page, stage the draft to a temporary file and run `scripts/capture_gate.py` with the full required analysis-capture arguments. Example:

   ```bash
   python3 scripts/capture_gate.py \
     --artifact "<short analysis description>" \
     --phase accepted \
     --primary-home "wiki/analyses/<slug>.md" \
     --pages-touched "wiki/analyses/<slug>.md,wiki/index.md,wiki/log.md" \
     --path "tmp/<draft>.md" \
     --synthesized-pages <count> \
     --domain-context yes \
     --trigger ranking_or_framework
   ```

   If it prints `APPROVAL REQUIRED`, show the request and stop. Re-run with `--approved` only after the user approves that displayed action, destination, and file scope.

2. For synthesis promotion, ledger updates, durable core-page drafts, or confidence/status flips, run `scripts/capture_gate.py --kind=synthesis` before the durable change crosses the promotion boundary:

   ```bash
   python3 scripts/capture_gate.py \
     --kind synthesis \
     --artifact "<short run>" \
     --drafts "<what the user reviewed>" \
     --primary-home "<wiki/synthesis.md when updating the ledger; otherwise the edited page>" \
     --pages-touched "<full approval edit scope>"
   ```

   The synthesis branch defaults `--primary-home` to `wiki/synthesis.md`; every run must include its `--primary-home` in `--pages-touched`, so a pass that does not touch the ledger must set `--primary-home` to the edited page and include that page in the scope. If it prints `APPROVAL REQUIRED`, show the request and stop. Re-run with `--approved` only after the user approves the displayed synthesis and scope. This appends or confirms the idempotent record in `scripts/capture-runs.jsonl`; then run `python3 scripts/validate_capture_runs.py`, which must pass.

3. Make only the approved edits. New synthesized content lands at `confidence: low` (restated in the body) and `status: draft` on meta pages unless the user explicitly graded that exact text. New pages get an `index.md` row.

4. Run:

   ```bash
   python3 scripts/rebuild_referenced_by.py
   python3 scripts/lint.py --tier1
   ```

   Both must pass.

5. Update `wiki/synthesis.md` only as part of the approved scope: refresh Current state digest lines that changed, append a run-ledger entry, and bump `updated:`.

6. Append a `synthesis` entry to `wiki/log.md` naming candidates considered, pages touched, approvals, deferrals, and verification. A memo-only no-change pass needs no durable record unless the user wants it logged.

## Log Entry Shape

For a memo-only pass with no durable edits, report in chat and do not log unless the user asks for a durable record.

For an approved draft/edit pass:

```text
## [YYYY-MM-DD] synthesis | <short batch description>
Candidates considered: <count, with the signals that produced them>
Classifications: <Draft this / Defer / No change / Needs user judgment / Needs more source>
Pages touched: <pages, or none>
Held at draft/low pending review: <pages>
Promoted after review: pending | <pages>
Verification: rebuild_referenced_by.py and lint.py --tier1 passed
```

For an approved promotion, append the promotion result:

```text
## [YYYY-MM-DD] synthesis promotion | <short batch description>
Promoted after review: <pages>
Ledger updated: wiki/synthesis.md
Gate: capture_gate.py --kind=synthesis approved exact synthesis content and scope; validate_capture_runs.py passed
Verification: rebuild_referenced_by.py and lint.py --tier1 passed
```

## Success Criteria And Kill Switch

A pass is worth running only if it produces at least one of:

- A clearer current-state summary.
- A reusable framework future agents can cite.
- A stale-page correction.
- A reduced need to re-read many pages.
- A sharper next question for the user.
- A surfaced contradiction or unresolved fork.

Judge quality, not frequency. An empty pass that correctly recommends no change is a success. A pass that mostly produces generic summaries is not. If generic summaries become the pattern, stop using this workflow and let ingest plus lint carry the load.

## Cadence

Run manually after a cluster of related ingests, or whenever the log shows a burst with no distillation following. It stays a manual loop: the pass must always stop for the user's grade, so there is little to gain from automating the trigger. Pair with `refresh-sourcing-queue`, which tracks what the wiki is missing from outside; this workflow tracks what the wiki already contains but has not yet said out loud.
