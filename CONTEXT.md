# <Organization> Wiki — Task Router

[`AGENTS.md`](AGENTS.md) is canonical and has the folder map and conventions. Claude Code reads it through the thin [`CLAUDE.md`](CLAUDE.md) wrapper. Non-Claude agents should read `AGENTS.md` first. **This file routes you to the right workspace.** Don't read everything — find your task, go to the workspace, follow its `CONTEXT.md`.

---

## Task Routing

| Your Task | Go Here | You'll Also Need |
|---|---|---|
| **Ingest a new file** (raw → wiki page) | [`workspaces/ingest/CONTEXT.md`](workspaces/ingest/CONTEXT.md) | [`workspaces/ingest/docs/schema.md`](workspaces/ingest/docs/schema.md) for frontmatter spec |
| **Answer a question from the wiki** | [`workspaces/research/CONTEXT.md`](workspaces/research/CONTEXT.md) | [`wiki/index.md`](wiki/index.md), [`wiki/primer.md`](wiki/primer.md) |
| **Compare entities** (products vs. competitors, customer A vs. B) | [`workspaces/research/CONTEXT.md`](workspaces/research/CONTEXT.md) | [`wiki/index.md`](wiki/index.md) |
| **Capture a decision** | [`workspaces/maintenance/CONTEXT.md`](workspaces/maintenance/CONTEXT.md) | [`workspaces/maintenance/docs/decision-capture.md`](workspaces/maintenance/docs/decision-capture.md) |
| **Lint the wiki** (contradictions, stale, orphans) | [`workspaces/maintenance/CONTEXT.md`](workspaces/maintenance/CONTEXT.md) | [`workspaces/maintenance/docs/lint-criteria.md`](workspaces/maintenance/docs/lint-criteria.md) |
| **Refresh sourcing queue** | [`workspaces/maintenance/CONTEXT.md`](workspaces/maintenance/CONTEXT.md) | [`workspaces/maintenance/sourcing-queue.md`](workspaces/maintenance/sourcing-queue.md) |
| **Update an entity page from a new source** | [`workspaces/ingest/CONTEXT.md`](workspaces/ingest/CONTEXT.md) | The existing page + new source |
| **Browse what's in the wiki** | [`wiki/index.md`](wiki/index.md) | — |

---

## Workspace Summary

| Workspace | Purpose | Pattern |
|---|---|---|
| [`workspaces/ingest/`](workspaces/ingest/) | Raw source → structured wiki page(s). Triage, extract, link. | Pipeline (3 stages) |
| [`workspaces/research/`](workspaces/research/) | Read wiki → synthesize answer with citations. Optionally file as analysis. | Conversational |
| [`workspaces/maintenance/`](workspaces/maintenance/) | Wiki hygiene: contradictions, lint, sourcing queue, decision capture. | Task-driven |

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
