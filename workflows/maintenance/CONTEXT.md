---
name: wiki-maintenance
description: Router for wiki hygiene, harness evaluation, artifact promotion, decision capture, observation capture, and sourcing queue refresh. Open the one task file you need.
---

# Maintenance Workspace

Wiki hygiene, harness evaluation, artifact promotion, decision capture, observation capture, and sourcing queue refresh. `/capture` is a shortcut for decision capture or experience capture, not a separate workflow. Load this router, then open only the one task file the work calls for. Don't pull every task file into context.

The wiki harness is the no-write review and eval layer. Ordinary ingest reaches it only when `scripts/wiki_route_policy.py` returns `full_harness`, or when the user explicitly asks to run or extend the harness.

Artifact promotion uses the shared capture preflight. Before applying artifact promotion, run `python3 scripts/capture_gate.py` with the proposed route and stop if it requires approval. Decision capture, observation capture, workflow updates, and routine page updates do not require this approval gate unless they are part of a promotion or analysis-capture route. If the user directly says they made a decision or lived through something they want remembered, use `/capture`; use `/promote` only when evaluating a separate artifact.

## Load / Skip

| Task | Open | Also load | Skip |
|---|---|---|---|
| Lint the wiki | [`lint.md`](lint.md) | all wiki pages, `wiki/contradictions.md`, `wiki/sourcing-queue.md` | `raw/`, the other task files |
| Run or extend the wiki autonomy harness | [`wiki-harness.md`](wiki-harness.md) | relevant `scripts/wiki_*.py`, `schemas/`, `tests/fixtures/`; local harness PRD if one exists | unrelated entity folders, raw sources not named by a fixture |
| Promote an artifact | [`artifact-promotion.md`](artifact-promotion.md) | `wiki/SCHEMA.md`, `wiki/index.md`, `scripts/capture_gate.py`, artifact being evaluated | unrelated entity folders, raw sources not cited by the artifact |
| Capture a decision | [`capture-decision.md`](capture-decision.md) | `wiki/SCHEMA.md`, affected entity pages | the full index, raw sources, other task files |
| Capture an observation or field note | [`capture-experience.md`](capture-experience.md) | `wiki/SCHEMA.md`, the relevant entity folder + related pages | the full index, raw sources, other task files |
| Refresh the sourcing queue | [`refresh-sourcing-queue.md`](refresh-sourcing-queue.md) | `wiki/sourcing-queue.md`, last ~10 `wiki/log.md` entries | the full wiki, entity pages, raw sources |
| Review template modernization | [`template-modernization-spec.md`](template-modernization-spec.md) | root docs, `workflows/`, `scripts/`, `schemas/`, `tests/fixtures/` | raw sources |

Each task file opens with its own Load / Skip list — follow it instead of pulling the whole wiki into context.
