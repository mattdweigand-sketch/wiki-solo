---
name: wiki-maintenance
description: Router for wiki hygiene, tooling evals, artifact promotion, first-person capture, corpus synthesis, and export. Open the one task file you need.
---

# Maintenance Workspace

Wiki hygiene, tooling evals, artifact promotion, first-person capture, corpus synthesis, and export. Load this router, then open only the one task file the work calls for. Do not pull every task file into context. `/wiki-capture` is a shortcut for decision capture or experience capture, not a separate workflow.

Invoking `/wiki-lint` authorizes the full lint workflow, including its verifier-agent evidence check, unless the user asks for deterministic-only lint, no subagents, or skipping the evidence check.

Artifact promotion uses the shared capture preflight. Before applying artifact promotion, run `python3 scripts/capture_gate.py` with the proposed route and stop if it requires approval. Approved reruns write or confirm `scripts/capture-runs.jsonl` and must be followed by `python3 scripts/validate_capture_runs.py`. Decision capture, experience capture, workflow updates, setup updates, and routine page updates do not require this approval gate unless they are part of a promotion or analysis-capture route. If the user directly says they made a decision or lived through something they want remembered, use `/wiki-capture`; use `/wiki-promote` only when evaluating a separate artifact.

Synthesis promotion uses `python3 scripts/capture_gate.py --kind=synthesis` before updating `wiki/synthesis.md`, flipping draft confidence/status, or logging a synthesis promotion. Approved reruns write or confirm synthesis approval records in `scripts/capture-runs.jsonl` and must be followed by `python3 scripts/validate_capture_runs.py`.

## Load / Skip

| Task | Open | Also load | Skip |
|---|---|---|---|
| Lint the wiki | [`lint.md`](lint.md) | all wiki pages, `wiki/contradictions.md`, `wiki/sourcing-queue.md` | `raw/`, the other task files |
| Run the wiki tooling evals | [`eval.md`](eval.md) | `scripts/wiki_eval.py`; failing suite output only if a run fails | wiki entity pages, raw sources, Tier-2/Tier-3 content review |
| Promote an artifact | [`artifact-promotion.md`](artifact-promotion.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), `wiki/index.md`, `scripts/capture_gate.py`, artifact being evaluated | unrelated entity folders, raw sources not cited by the artifact |
| Capture a decision | [`capture-decision.md`](capture-decision.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), affected entity pages | the full index, raw sources, other task files |
| Capture an observation, field note, or lived context | [`capture-experience.md`](capture-experience.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), the relevant entity folder + related pages | the full index, raw sources, other task files |
| Refresh the sourcing queue | [`refresh-sourcing-queue.md`](refresh-sourcing-queue.md) | `wiki/sourcing-queue.md`, last ~10 `wiki/log.md` entries | the full wiki, entity pages, raw sources |
| Synthesize the corpus | [`synthesize.md`](synthesize.md) | `wiki/synthesis.md` first, full `scripts/lint.py` output, `wiki/log.md` since the last synthesis entry, `wiki/index.md`, candidate pages only | `raw/`, entity folders the candidates do not touch |
| Review due pages | [`review.md`](review.md) | `python3 scripts/review_due.py` output and due pages only | unrelated entity folders, raw sources |
| Export a corpus zip | [`export.md`](export.md) | nothing else | all wiki pages, raw sources, other task files |

Each task file opens with its own Load / Skip list. Follow it instead of pulling the whole wiki into context.
