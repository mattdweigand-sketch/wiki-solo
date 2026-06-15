---
name: wiki-maintenance
description: Router for wiki hygiene, artifact promotion, first-person capture, corpus synthesis, export, and the archived harness pointer. Open the one task file you need.
---

# Maintenance Workspace

Wiki hygiene, artifact promotion, first-person capture, corpus synthesis, and backup export. Load this router, then open only the one task file the work calls for. Do not pull every task file into context. `/wiki-capture` is a shortcut for decision capture or experience capture, not a separate workflow.

Invoking `/wiki-lint` authorizes the full lint workflow, including its verifier-agent evidence check, unless the user asks for deterministic-only lint, no subagents, or skipping the evidence check.

The wiki autonomy harness is archived as a paused experiment under `archive/wiki-harness/`. Do not run or extend it unless the project explicitly reopens the harness; [`wiki-harness.md`](wiki-harness.md) is a pointer stub.

Artifact promotion uses the shared capture preflight. Before applying artifact promotion, run `python3 scripts/capture_gate.py` with the proposed route and stop if it requires approval. Approved reruns write or confirm `scripts/capture-runs.jsonl` and must be followed by `python3 scripts/validate_capture_runs.py`. Decision capture, experience capture, workflow updates, setup updates, and routine page updates do not require this approval gate unless they are part of a promotion or analysis-capture route. If the user directly says they made a decision or lived through something they want remembered, use `/wiki-capture`; use `/wiki-promote` only when evaluating a separate artifact.

Synthesis promotion uses `python3 scripts/synthesis_gate.py` before updating `wiki/synthesis.md`, flipping draft confidence/status, or logging a synthesis promotion. Approved reruns write or confirm `scripts/synthesis-runs.jsonl` and must be followed by `python3 scripts/validate_synthesis_runs.py`.

## Load / Skip

| Task | Open | Also load | Skip |
|---|---|---|---|
| Lint the wiki | [`lint.md`](lint.md) | all wiki pages, `wiki/contradictions.md`, `wiki/sourcing-queue.md` | `raw/`, the other task files |
| Anything about the archived wiki autonomy harness | [`wiki-harness.md`](wiki-harness.md) | `archive/wiki-harness/README.md`, `archive/wiki-harness/wiki-harness-workflow.md` | archived scripts and fixtures unless explicitly reopening/debugging the harness |
| Promote an artifact | [`artifact-promotion.md`](artifact-promotion.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), `wiki/index.md`, `scripts/capture_gate.py`, artifact being evaluated | unrelated entity folders, raw sources not cited by the artifact |
| Capture a decision | [`capture-decision.md`](capture-decision.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), affected entity pages | the full index, raw sources, other task files |
| Capture an observation, field note, or lived context | [`capture-experience.md`](capture-experience.md) | `wiki/SCHEMA.md`, `REFERENCES.md` (cross-referencing rules), the relevant entity folder + related pages | the full index, raw sources, other task files |
| Refresh the sourcing queue | [`refresh-sourcing-queue.md`](refresh-sourcing-queue.md) | `wiki/sourcing-queue.md`, last ~10 `wiki/log.md` entries | the full wiki, entity pages, raw sources |
| Synthesize the corpus | [`synthesize.md`](synthesize.md) | `wiki/synthesis.md` first, full `scripts/lint.py` output, `wiki/log.md` since the last synthesis entry, `wiki/index.md`, candidate pages only | `raw/`, harness scripts, entity folders the candidates do not touch |
| Export a backup zip of the corpus | [`export.md`](export.md) | nothing else | all wiki pages, raw sources, other task files |

Each task file opens with its own Load / Skip list. Follow it instead of pulling the whole wiki into context.
