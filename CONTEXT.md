# <Organization> Wiki - Task Router

`AGENTS.md` is canonical: it holds the folder map, conventions, and hard rules. This file routes a task to the right workspace. Do not read everything; find the task, open the workflow entry, and load only what it says to load.

Works with any agent. Claude Code, ChatGPT, Codex, Cursor, or a raw API harness all use the same path: read `AGENTS.md`, check `wiki/domain.md` for setup status, read this file, then open the workflow for the task. The files under `.claude/commands/` and `.codex/commands/` are optional thin wrappers for `/wiki-ingest`, `/wiki-capture`, `/wiki-lint`, `/wiki-promote`, `/wiki-synthesize`, and `/wiki-export`. Nothing here depends on either wrapper surface.

Workflows are grouped into three workspaces under `workflows/`: **ingest** (raw -> pages), **research** (question -> answer), and **maintenance** (lint, artifact promotion, captures, sourcing queue, synthesize, export). Each workspace's `CONTEXT.md` is its entry point and scopes exactly what to load.

Ordinary source ingest proceeds directly through `workflows/ingest/CONTEXT.md`; the former route preflight is archived with the autonomy harness.

Analysis capture and artifact promotion share one executable approval gate: `python3 scripts/capture_gate.py`. Its job is approval rather than routing: it derives a mode and primary home from its inputs, then blocks durable analysis/promotion edits until the user approves them. Ordinary source ingest does not require this approval gate. If it prints `APPROVAL REQUIRED`, show the full output and wait for approval before editing files.

---

## Routing

| Task | Workspace entry |
|---|---|
| Configure a fresh clone | [`SETUP.md`](SETUP.md) |
| Ingest a source (`raw/` -> wiki page) | [`workflows/ingest/CONTEXT.md`](workflows/ingest/CONTEXT.md) |
| Answer a question from the wiki | [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md) |
| Compare entities | [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md) |
| Lint the wiki | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`lint.md`](workflows/maintenance/lint.md) |
| Anything about the archived wiki autonomy harness | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`wiki-harness.md`](workflows/maintenance/wiki-harness.md) |
| Promote a useful artifact into durable wiki memory | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`artifact-promotion.md`](workflows/maintenance/artifact-promotion.md) |
| Capture a decision | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`capture-decision.md`](workflows/maintenance/capture-decision.md) |
| Capture an observation, field note, or lived context | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`capture-experience.md`](workflows/maintenance/capture-experience.md) |
| Refresh the sourcing queue | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`refresh-sourcing-queue.md`](workflows/maintenance/refresh-sourcing-queue.md) |
| Synthesize the corpus | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`synthesize.md`](workflows/maintenance/synthesize.md) |
| Export a backup zip of the corpus | [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md) -> [`export.md`](workflows/maintenance/export.md) |
| Browse what's in the wiki | [`wiki/index.md`](wiki/index.md) |

Each workflow opens with its own Load / Skip list. Follow that list instead of pulling the whole wiki into context.
