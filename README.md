# Wiki Template

A self-maintaining, LLM-readable knowledge base for your company, team, or project. Downstream AI agents (sales, product, support, ops) read from this wiki instead of re-deriving context from raw documents every time. Built on the [Karpathy LLM-wiki pattern](https://karpathy.ai/zero-to-one/).

Drop your documents into `raw/`, run `/ingest`, and the wiki starts compounding.

## Quick start

1. **Copy this repo** (fork, clone, or "Use this template" on GitHub) into your own workspace.
2. **Drop source documents** into the appropriate `raw/<category>/` subfolder. Existing subfolders are example categories — rename, add, or remove to fit your domain.
3. **Open the project in Claude Code** (or another AI coding agent that respects `CLAUDE.md`).
4. **Run `/ingest`** to turn raw documents into structured wiki pages.
5. **Ask questions.** The agent reads from `wiki/` and cites its sources.

## How to use it

The wiki is designed as a **reference guide for AI agents**. There are three modes of use.

### 1. Ask a question (default)

Just ask. Any AI agent with access to this directory picks up [`CLAUDE.md`](CLAUDE.md), follows it to [`CONTEXT.md`](CONTEXT.md), and routes through the [research workspace](.claude/workspaces/research/CONTEXT.md) — which tells the agent how to find the right pages, cite sources, and respect confidence ratings. No command needed.

The agent answers with citations like `(source: [[sources/some-page]])` so you can trace any claim back to its source.

**Meaningful answers are auto-filed.** When an answer synthesizes 3+ wiki pages and runs >300 words, the agent saves it to [`wiki/analyses/`](wiki/analyses/) automatically and tells you in one line (*"Filed as `analyses/<slug>.md` — delete if not useful."*). This is how the wiki compounds — good answers don't disappear into chat history. Deletion is cheaper than re-asking the same question next month.

### 2. Add a new source

Drop the file into the appropriate `raw/` subfolder, then run:

```
/ingest
```

This runs the 3-stage ingest pipeline (triage → extract → link), creates or updates the relevant entity pages, rebuilds backlinks, and appends a log entry.

### 3. Maintain the wiki

```
/lint
```

Checks for contradictions, stale claims, orphan pages, missing cross-references, terminology drift, and confidence miscalibration. Reports findings, asks which to apply, then applies approved fixes.

For decisions, contradictions, or sourcing-queue updates, just describe the task — the agent routes through the [maintenance workspace](.claude/workspaces/maintenance/CONTEXT.md).

### Browsing manually

Start at [`wiki/index.md`](wiki/index.md) — the master catalog of every page, grouped by entity type with one-line summaries and confidence ratings.

## Repo structure

```
your-wiki/
├── CLAUDE.md       Map of the repo. Always loaded by agents.
├── CONTEXT.md      Task router.
├── README.md       This file.
│
├── raw/            Source documents. Immutable — never edited.
├── wiki/           Knowledge layer. All entity pages live here.
├── deliverables/   Generated outputs (briefs, decks, drafts).
└── .claude/        Workspace machinery and slash commands.
```

## Entity types

13 entity types ship out of the box. Each lives in its own folder under `wiki/`. Add, remove, or rename to fit your domain.

| Type | Folder | Purpose |
|---|---|---|
| Source | `wiki/sources/` | Summary of a raw document — facts, quotes, metadata |
| Product | `wiki/products/` | A product: positioning, users, core jobs |
| Feature | `wiki/features/` | A specific feature: what it does, who uses it |
| Persona | `wiki/personas/` | A user/buyer type: role, goals, pain, objections |
| Customer | `wiki/customers/` | A named customer or segment |
| Competitor | `wiki/competitors/` | A competing vendor: positioning, where they win/lose |
| Concept | `wiki/concepts/` | A domain idea or canonical definition |
| Initiative | `wiki/initiatives/` | A strategic bet, launch, or program |
| Decision | `wiki/decisions/` | A decision, reasoning, alternatives, revisit date |
| Metric | `wiki/metrics/` | A KPI or North Star: definition, formula, target |
| Person/Team | `wiki/people/` | A role, team, or stakeholder |
| Analysis | `wiki/analyses/` | Synthesized output: comparison, brief, gap analysis |
| Style Rule | `wiki/style/` | Writing/naming convention for agent-generated content |

Full schema in [`.claude/workspaces/ingest/docs/schema.md`](.claude/workspaces/ingest/docs/schema.md).

## How agents consume it

Three files cover most queries:

1. [`wiki/index.md`](wiki/index.md) — master catalog
2. [`wiki/overview.md`](wiki/overview.md) — company synthesis
3. [`wiki/glossary.md`](wiki/glossary.md) — canonical terminology

Each page carries a `confidence:` rating in its frontmatter:

| Rating | Meaning |
|---|---|
| `high` | Sourced from authoritative document |
| `medium` | Probable; may rest on a single source |
| `low` | Hypothesis; treat as a starting point |
| `contested` | Sources disagree — see [`contradictions.md`](.claude/workspaces/maintenance/contradictions.md) |

Every factual claim cites its source as `(source: [[source-slug]])`. Inferences are prefixed `Inference:` or `Hypothesis:`.

## Conventions

- **Filenames:** kebab-case, no prefix (`acme-battlecard.md`)
- **Internal links:** `[[page-name]]` (no folder, no extension)
- **`raw/` is immutable** — source files are never edited; new sources are appended
- **Cite the wiki page**, not the raw source, in agent-to-human output

## Workspaces

Three workspaces govern how work happens. Each has its own `CONTEXT.md` with task-specific instructions.

| Workspace | Purpose |
|---|---|
| [`ingest/`](.claude/workspaces/ingest/CONTEXT.md) | Raw source → structured wiki page(s) |
| [`research/`](.claude/workspaces/research/CONTEXT.md) | Wiki → synthesized answer with citations |
| [`maintenance/`](.claude/workspaces/maintenance/CONTEXT.md) | Lint, contradictions, sourcing queue, decision capture |

## Why a wiki instead of RAG

RAG does one thing: at query time, embed the question, retrieve chunks from source docs, and stuff them into context. It front-loads nothing and compounds nothing.

The wiki front-loads the hard work at ingest time and makes every session cheaper and more reliable:

1. **Distillation, not retrieval.** The wiki reads each source once and distills it into structured entity pages. The query agent starts from signal, not raw chunks.
2. **Explicit contradiction handling.** When sources disagree, the wiki flags it and marks pages `confidence: contested`. RAG retrieves both and lets the LLM guess.
3. **Typed, navigable relationships.** Entity types, frontmatter, and `[[wikilinks]]` route agents directly to the right pages. No chunk-hunting.
4. **Compounding knowledge.** Good answers get filed back into `wiki/analyses/` as citable pages. RAG accumulates source documents; the wiki accumulates understanding.
5. **Scoped agent context.** Ingest, research, and maintenance agents each load only what they need. Smaller context, lower hallucination risk.
6. **Domain-locked terminology.** The glossary prevents paraphrase drift on precise terms.

## Activity

See [`wiki/log.md`](wiki/log.md) for the append-only history of every ingest, lint, and decision capture.

## Customizing for your domain

1. **Edit `CLAUDE.md`** — change the "Purpose" section to describe *your* company or domain.
2. **Rename `raw/` subfolders** to match your document categories.
3. **Edit `wiki/overview.md`** — write a paragraph or two about your company. The agent updates this as it ingests sources.
4. **Edit `wiki/glossary.md`** — seed it with terms your domain cares about.
5. **Add or remove entity types.** If you don't sell software, you may not need `products/` or `features/`. If you're a research team, you may want `papers/` or `experiments/`.

The harness in `.claude/` is domain-agnostic — it works on any corpus.
