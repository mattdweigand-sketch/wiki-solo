# <Organization> Wiki

A clonable, agent-readable wiki template. The company context layer for AI agents at the organization defined in [`wiki/domain.md`](wiki/domain.md).

A self-maintaining, LLM-readable knowledge base. Downstream agents (sales, product, customer success) read from it instead of re-deriving context from raw documents. Built on the [Karpathy LLM-wiki pattern](https://karpathy.ai/zero-to-one/).

> **Just cloned this?** See [`SETUP.md`](SETUP.md) — your AI agent will read it on first session and offer to interview you to configure the wiki for your organization.

## How to use it

The wiki is designed as a **reference guide for AI agents**. There are three modes of use.

### 1. Ask a question (default)

Just ask. [`AGENTS.md`](AGENTS.md) is canonical. OpenAI Codex, Cursor, and other AGENTS-aware tools should read it directly. Claude Code auto-loads [`CLAUDE.md`](CLAUDE.md), which is only a thin wrapper that imports `AGENTS.md`. From there the agent follows [`CONTEXT.md`](CONTEXT.md) into the [research workspace](workspaces/research/CONTEXT.md), which tells it how to find the right pages, cite sources, and respect confidence ratings. No command needed.

Example question shapes (fill in your own domain):
- "How does `<our product>` compare to `<competitor>`?"
- "What's our positioning on `<market shift or theme>`?"
- "What's our GTM strategy for `<segment>`?"

The agent answers with citations like `(source: [[sources/<source-slug>]])` so you can trace any claim back to its source.

**Meaningful answers are auto-filed.** When the answer synthesizes 3+ wiki pages and runs >300 words, the agent saves it to [`wiki/analyses/`](wiki/analyses/) automatically and tells you in one line (*"Filed as `analyses/<slug>.md` — delete if not useful."*). This is how the wiki compounds — good answers don't disappear into chat history. Deletion is cheaper than re-asking the same question next month.

### 2. Add a new source

Drop the file into the appropriate `raw/` subfolder, then run:

```
/ingest
```

This runs the 3-stage ingest pipeline (triage → extract → link), creates or updates the relevant entity pages, rebuilds backlinks, and appends a log entry.

> **No slash commands?** `/ingest` and `/lint` are Claude Code shortcuts. On Codex or any other agent, point it at [`workspaces/ingest/CONTEXT.md`](workspaces/ingest/CONTEXT.md) and ask it to follow the pipeline — the prose workflow is the same.

### 3. Maintain the wiki

```
/lint
```

Checks for contradictions, stale claims, orphan pages, missing cross-references, terminology drift, and confidence miscalibration. Reports findings, asks which to apply, then applies approved fixes.

For decisions, contradictions, or sourcing-queue updates, just describe the task — the agent will route through the [maintenance workspace](workspaces/maintenance/CONTEXT.md).

### Browsing manually

Start at [`wiki/index.md`](wiki/index.md) — the master catalog of every page, grouped by entity type with one-line summaries and confidence ratings.

## Repo structure

```
<wiki-root>/
├── AGENTS.md       Canonical project operating map for agents.
├── CLAUDE.md       Thin Claude Code wrapper that imports AGENTS.md.
├── CONTEXT.md      Task router.
├── SETUP.md        First-session config (when wiki/domain.md is unconfigured).
├── README.md       This file.
│
├── raw/            Source documents. Immutable — never edited.
├── wiki/           Knowledge layer. All entity pages live here.
├── workspaces/     Vendor-neutral workflow routing (ingest, research, maintenance).
├── scripts/        Vendor-neutral helpers (rebuild_referenced_by.py).
└── .claude/        Claude Code slash-command wrappers only. Optional.
```

## What's in the wiki

13 entity types out of the box. Drop the ones that don't fit your domain during setup; add custom types as needed.

| Type | Purpose |
|---|---|
| Sources | Summaries of raw documents — what they contain, what they're trustworthy for |
| Products | What the organization offers |
| Features | Specific capabilities within a product |
| Personas | User and buyer types |
| Customers | Named customers or segments |
| Competitors | Competing vendors and how they position |
| Concepts | Domain ideas, terminology, and frameworks |
| Initiatives | Strategic bets, launches, programs |
| Decisions | Choices made, alternatives rejected, when to revisit |
| Metrics | KPIs and North Stars |
| People | Roles, teams, stakeholders |
| Analyses | Synthesized outputs — comparisons, briefs, gap analyses |
| Style Rules | Writing and naming conventions for agent-generated content |

Full catalog: [`wiki/index.md`](wiki/index.md). See [`wiki/domain.md`](wiki/domain.md) for which types this wiki has activated.

## How agents consume it

Four files cover most queries:

1. [`wiki/domain.md`](wiki/domain.md) — org name, scope, active entity types
2. [`wiki/index.md`](wiki/index.md) — master catalog
3. [`wiki/overview.md`](wiki/overview.md) — synthesis of the organization
4. [`wiki/glossary.md`](wiki/glossary.md) — canonical terminology

Each page carries a `confidence:` rating in its frontmatter:

| Rating | Meaning |
|---|---|
| `high` | Sourced from authoritative document |
| `medium` | Probable; may rest on a single source |
| `low` | Hypothesis; treat as a starting point |
| `contested` | Sources disagree — see [`contradictions.md`](workspaces/maintenance/contradictions.md) |

Every factual claim cites its source as `(source: [[source-slug]])`. Inferences are prefixed `Inference:` or `Hypothesis:`.

## Conventions

- **Filenames:** kebab-case, no prefix (e.g. `<competitor>-battlecard.md`)
- **Internal links:** `[[page-name]]` (no folder, no extension)
- **`raw/` is immutable** — source files are never edited; new sources are appended
- **Cite the wiki page**, not the raw source, in agent-to-human output

For the full schema, see [`workspaces/ingest/docs/schema.md`](workspaces/ingest/docs/schema.md).

## Workspaces

Three workspaces govern how work happens. Each has its own `CONTEXT.md` with task-specific instructions.

| Workspace | Purpose |
|---|---|
| [`ingest/`](workspaces/ingest/CONTEXT.md) | Raw source → structured wiki page(s) |
| [`research/`](workspaces/research/CONTEXT.md) | Wiki → synthesized answer with citations |
| [`maintenance/`](workspaces/maintenance/CONTEXT.md) | Lint, contradictions, sourcing queue, decision capture |

## Why a wiki instead of RAG

RAG does one thing: at query time, embed the question, retrieve chunks from source docs, and stuff them into context. It front-loads nothing and compounds nothing.

The wiki front-loads the hard work at ingest time and makes every session cheaper and more reliable:

1. **Distillation, not retrieval.** The wiki reads each source once and distills it into structured entity pages. The query agent starts from signal, not raw chunks.

2. **Explicit contradiction handling.** When sources disagree, the wiki flags it and marks pages `confidence: contested`. RAG retrieves both and lets the LLM guess.

3. **Typed, navigable relationships.** 13 entity types, frontmatter, and `[[wikilinks]]` route agents directly to the right pages. No chunk-hunting.

4. **Compounding knowledge.** Good answers get filed back into `wiki/analyses/` as citable pages. RAG accumulates source documents; the wiki accumulates understanding.

5. **Scoped agent context.** Ingest, research, and maintenance agents each load only what they need. Smaller context, lower hallucination risk.

6. **Domain-locked terminology.** The glossary prevents paraphrase drift on precise domain terms — definitions live in one place and downstream agents use them verbatim.

## Activity

See [`wiki/log.md`](wiki/log.md) for the append-only history of every ingest, lint, and decision capture.
