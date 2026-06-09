# <Organization> Wiki — Task Router

`AGENTS.md` is canonical: it holds the folder map, conventions, and hard rules. This file routes a task to the right workflow. Do not read everything; find the task, open the workflow entry, and load only what it says to load.

Works with any agent. Claude Code, ChatGPT, Codex, Cursor, or a raw API harness all use the same path: read `AGENTS.md`, check `wiki/domain.md`, read this file, then open the workflow for the task.

Ordinary source ingest starts with a no-write route preflight:

```bash
python3 scripts/wiki_route_policy.py <raw-source>
```

It returns `direct_edit`, `full_harness`, or `blocked`, and `workflows/ingest/CONTEXT.md` owns the next step.

Analysis capture and artifact promotion share one executable approval preflight:

```bash
python3 scripts/capture_gate.py \
  --artifact "<artifact summary>" \
  --phase accepted|workflow \
  --primary-home "<path or none>" \
  --pages-touched "<comma-separated paths>"
```

Run it with the workflow-specific arguments before filing a substantial research answer as `wiki/analyses/` or applying an artifact promotion. Ordinary source ingest does not require this approval gate. If it prints `APPROVAL REQUIRED`, show the exact output and wait for approval before editing files.

---

## Routing

| Task | Workflow entry | Also load |
|---|---|---|
| Configure a fresh clone | [`SETUP.md`](SETUP.md) | `wiki/domain.md` |
| Ingest a source (`raw/` to wiki page) | [`workflows/ingest/CONTEXT.md`](workflows/ingest/CONTEXT.md) | `wiki/SCHEMA.md` |
| Answer a question from the wiki | [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md) | `wiki/index.md`, then the pages it points to; `scripts/capture_gate.py` if filing analysis |
| Compare entities | [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md) | `wiki/index.md`, relevant entity pages |
| Lint the wiki | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`lint.md`](workflows/maintenance/lint.md) | all wiki pages |
| Run or extend the wiki autonomy harness | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`wiki-harness.md`](workflows/maintenance/wiki-harness.md) | relevant `scripts/wiki_*.py`, `schemas/`, `tests/fixtures/` |
| Promote a useful artifact into durable wiki memory | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`artifact-promotion.md`](workflows/maintenance/artifact-promotion.md) | `wiki/SCHEMA.md`, `wiki/index.md`, `scripts/capture_gate.py` |
| Capture a decision | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`capture-decision.md`](workflows/maintenance/capture-decision.md) | `wiki/SCHEMA.md`, affected entity pages |
| Capture an observation or field note | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`capture-experience.md`](workflows/maintenance/capture-experience.md) | `wiki/SCHEMA.md`, affected entity pages |
| Refresh the sourcing queue | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) to [`refresh-sourcing-queue.md`](workflows/maintenance/refresh-sourcing-queue.md) | `wiki/sourcing-queue.md` if present, otherwise workflow task file |
| Browse what's in the wiki | [`wiki/index.md`](wiki/index.md) | `wiki/domain.md` |

Each workflow opens with its own Load / Skip list. Follow that list instead of pulling the whole wiki into context.
