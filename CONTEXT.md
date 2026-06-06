# <Organization> Wiki — Task Router

[`AGENTS.md`](AGENTS.md) is canonical and has the folder map and conventions. Claude Code reads it through the thin [`CLAUDE.md`](CLAUDE.md) wrapper. Shared workflow instructions live in [`.agents/`](.agents/). **This file routes you to the right workspace.** Don't read everything — find your task, go to the workspace, follow its `CONTEXT.md`.

---

## Task Routing

| Your Task | Go Here | You'll Also Need |
|---|---|---|
| **Ingest a new file** (raw → wiki page) | [`.agents/workspaces/ingest/CONTEXT.md`](.agents/workspaces/ingest/CONTEXT.md) | [`.agents/workspaces/ingest/docs/schema.md`](.agents/workspaces/ingest/docs/schema.md) for frontmatter spec |
| **Answer a question from the wiki** | [`.agents/workspaces/research/CONTEXT.md`](.agents/workspaces/research/CONTEXT.md) | [`wiki/index.md`](wiki/index.md), [`wiki/primer.md`](wiki/primer.md) |
| **Compare entities** (products vs. competitors, customer A vs. B) | [`.agents/workspaces/research/CONTEXT.md`](.agents/workspaces/research/CONTEXT.md) | [`wiki/index.md`](wiki/index.md) |
| **Capture a decision** | [`.agents/workspaces/maintenance/CONTEXT.md`](.agents/workspaces/maintenance/CONTEXT.md) | [`.agents/workspaces/maintenance/docs/decision-capture.md`](.agents/workspaces/maintenance/docs/decision-capture.md) |
| **Lint the wiki** (contradictions, stale, orphans) | [`.agents/workspaces/maintenance/CONTEXT.md`](.agents/workspaces/maintenance/CONTEXT.md) | [`.agents/workspaces/maintenance/docs/lint-criteria.md`](.agents/workspaces/maintenance/docs/lint-criteria.md) |
| **Refresh sourcing queue** | [`.agents/workspaces/maintenance/CONTEXT.md`](.agents/workspaces/maintenance/CONTEXT.md) | [`.agents/workspaces/maintenance/sourcing-queue.md`](.agents/workspaces/maintenance/sourcing-queue.md) |
| **Update an entity page from a new source** | [`.agents/workspaces/ingest/CONTEXT.md`](.agents/workspaces/ingest/CONTEXT.md) | The existing page + new source |
| **Browse what's in the wiki** | [`wiki/index.md`](wiki/index.md) | — |

---

## Workspace Summary

| Workspace | Purpose | Pattern |
|---|---|---|
| [`.agents/workspaces/ingest/`](.agents/workspaces/ingest/) | Raw source → structured wiki page(s). Triage, extract, link. | Pipeline (3 stages) |
| [`.agents/workspaces/research/`](.agents/workspaces/research/) | Read wiki → synthesize answer with citations. Optionally file as analysis. | Conversational |
| [`.agents/workspaces/maintenance/`](.agents/workspaces/maintenance/) | Wiki hygiene: contradictions, lint, sourcing queue, decision capture. | Task-driven |

Each workspace's `CONTEXT.md` says exactly what to load for each task type — and what to skip.

---

## Cross-Workspace Flow

```
raw/  →  ingest/  →  wiki/  →  research/  →  wiki/analyses/
                       ↑
                  maintenance/
```

- Ingest produces or updates wiki pages.
- Research consumes wiki pages and produces analyses (which themselves become wiki pages, citable by future agents).
- Maintenance keeps the substrate honest — finds contradictions, flags stale content, prompts new sourcing.
