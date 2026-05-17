# <Organization> Wiki — Map

## Purpose

The company-context layer for the AI infrastructure of the organization defined in [`wiki/domain.md`](wiki/domain.md). Downstream agents (sales, product, engineering, customer) consume this wiki to reason about the organization: customers, products, market, people, strategy, decisions. **Agent-readable first, grounded in sources, compounding rather than re-derived.**

This file is the **map** — always loaded. It tells you what's where. It does NOT contain workflows. For task-specific procedure, route through [`CONTEXT.md`](CONTEXT.md) → workspace `CONTEXT.md`.

**First-session check:** Read [`wiki/domain.md`](wiki/domain.md). If `status: unconfigured`, route to [`SETUP.md`](SETUP.md) before answering other questions.

---

## Auto-File Rule (read before answering any domain question)

After answering any domain question that meets **all three** criteria below, file the answer to `wiki/analyses/<slug>.md` using the [analysis template](.claude/workspaces/research/docs/analysis-template.md). **Don't ask first.** Notify in one line after filing: *"Filed as `analyses/<slug>.md` — delete if not useful."* Then append a `query` entry to [`wiki/log.md`](wiki/log.md) and run `python3 .claude/commands/rebuild_referenced_by.py`.

Criteria:
1. The response synthesized **3+ wiki pages** (real cross-page synthesis, not a single-page lookup).
2. The response is **>300 words** (substantive, not a quick fact).
3. The response answers a **domain question** — a question about anything covered by this wiki (products, customers, competitors, strategy, decisions, metrics, etc.; see [`wiki/domain.md`](wiki/domain.md) for the wiki's scope). Meta-discussion about the wiki itself does not qualify.

If any criterion fails, just answer in chat. The wiki compounds because good answers don't disappear into chat history; deletion is cheaper than recall.

---

## Folder Map

```
<wiki-root>/
├── CLAUDE.md              ← Map (this file). Always loaded.
├── CONTEXT.md             ← Task router. Read second.
├── SETUP.md               ← First-session config (when domain.md is unconfigured).
│
├── raw/                   ← Source documents. Immutable. Never write here.
│
├── wiki/                  ← Knowledge layer. Entity pages and indexes.
│   ├── index.md           ← Navigational entry point for any query
│   ├── primer.md          ← By-question-type routing into the wiki
│   ├── overview.md        ← Big-picture summary of the organization
│   ├── glossary.md        ← Canonical terms for this domain
│   ├── domain.md          ← Domain config (org, scope, active entity types)
│   ├── log.md             ← Append-only history of ingest/query/lint sessions
│   └── <entity-type>/     ← One folder per entity type (see table below)
│
└── .claude/               ← Wiki machinery (slash commands + workspace routing)
    ├── commands/          ← Slash commands (/ingest, /lint) + helper scripts
    └── workspaces/
        ├── ingest/        ← Workspace: raw → wiki (pipeline)
        ├── research/      ← Workspace: query → analysis (conversational)
        └── maintenance/   ← Workspace: wiki hygiene (task-driven)
```

---

## Entity Types

13 entity types. Each lives in its own folder under `wiki/`. Frontmatter spec, citation rules, and source-type templates are in [`.claude/workspaces/ingest/docs/schema.md`](.claude/workspaces/ingest/docs/schema.md) — read it when authoring or auditing pages.

| Type | Folder | Purpose |
|---|---|---|
| Source | `wiki/sources/` | Summary of a raw document — facts, quotes, metadata |
| Product | `wiki/products/` | A product offered by the organization: positioning, users, core jobs |
| Feature | `wiki/features/` | A specific feature: what it does, who uses it |
| Persona | `wiki/personas/` | A user/buyer type: role, goals, pain, objections |
| Customer | `wiki/customers/` | A named customer/segment: profile, use cases, risks |
| Competitor | `wiki/competitors/` | A competing vendor: positioning, where they win/lose |
| Concept | `wiki/concepts/` | A domain idea relevant to this wiki's scope |
| Initiative | `wiki/initiatives/` | A strategic bet, launch, or program |
| Decision | `wiki/decisions/` | A decision, reasoning, alternatives, revisit date |
| Metric | `wiki/metrics/` | A KPI or North Star: definition, formula, target |
| Person/Team | `wiki/people/` | A role, team, or stakeholder (role-focused) |
| Analysis | `wiki/analyses/` | Synthesized output: comparison, brief, gap analysis |
| Style Rule | `wiki/style/` | Writing/naming convention for agent-generated content |

---

## Cross-Workspace Flow

```
raw/              ingest/             wiki/             research/         analyses
(sources)   →     (raw → page)   →    (knowledge)   →   (query)      →    wiki/analyses/
                                            ↑
                                     maintenance/
                                     (lint, contradictions, sourcing-queue)
```

- **Ingest** reads `raw/`, writes to `wiki/`. Never modifies `raw/`.
- **Research** reads `wiki/`, writes synthesized outputs to `wiki/analyses/`.
- **Maintenance** reads `wiki/` plus its own scratchpads (`.claude/workspaces/maintenance/contradictions.md`, `.claude/workspaces/maintenance/sourcing-queue.md`), writes back to `wiki/` to fix issues.

---

## Naming and Citation Conventions

- **Filenames:** kebab-case, no extension prefix. Example: `<competitor>-battlecard.md`.
- **Page titles:** title-cased in frontmatter is fine.
- **Internal links:** `[[page-name-without-extension]]`. Always use this for cross-references between wiki pages.
- **Citations:** When stating a fact, append `(source: [[source-filename]])`. When stating opinion or inference, prefix with `Inference:` or `Hypothesis:`.
- **Confidence:** `high` | `medium` | `low` | `contested`. When `low` or `contested`, restate in the page body — downstream agents may skip frontmatter.
- **Terminology:** Use domain-specific terms precisely. Don't paraphrase. Add new terms to [`wiki/glossary.md`](wiki/glossary.md). The domain's scope is defined in [`wiki/domain.md`](wiki/domain.md).

---

## Quick Navigation

| Want to... | Go here |
|---|---|
| **Ingest a new source file** | [`.claude/workspaces/ingest/CONTEXT.md`](.claude/workspaces/ingest/CONTEXT.md) |
| **Understand entity types and frontmatter** | [`.claude/workspaces/ingest/docs/schema.md`](.claude/workspaces/ingest/docs/schema.md) |
| **Answer a question from the wiki** | [`.claude/workspaces/research/CONTEXT.md`](.claude/workspaces/research/CONTEXT.md) |
| **Capture a decision** | [`.claude/workspaces/maintenance/CONTEXT.md`](.claude/workspaces/maintenance/CONTEXT.md) |
| **Lint the wiki / check contradictions** | [`.claude/workspaces/maintenance/CONTEXT.md`](.claude/workspaces/maintenance/CONTEXT.md) |
| **Refresh the sourcing queue** | [`.claude/workspaces/maintenance/CONTEXT.md`](.claude/workspaces/maintenance/CONTEXT.md) |
| **See what's in the wiki** | [`wiki/index.md`](wiki/index.md) |
| **Find an entry point by question type** | [`wiki/primer.md`](wiki/primer.md) |
| **See recent activity** | [`wiki/log.md`](wiki/log.md) |

---

## Hard Rules

1. **Never modify `raw/`.** It grows monotonically — new sources append, existing files never change. Wiki citations point back to filenames there.
2. **Flag contradictions explicitly.** Never silently overwrite. Open an entry in [`.claude/workspaces/maintenance/contradictions.md`](.claude/workspaces/maintenance/contradictions.md) when sources disagree.
3. **Update existing pages over creating new ones** when content fits. The wiki compounds; it does not fragment.
4. **Cite every claim.** Specific facts get `(source: [[source-page]])`. Opinion gets `Inference:` or `Hypothesis:`.
5. **Workspaces are siloed.** An ingest agent does not load `.claude/workspaces/research/docs/`. A research agent does not load `.claude/workspaces/ingest/workflows/`. Each workspace's `CONTEXT.md` says exactly what to load.

---

## Session Start Checklist

At the start of every session:
1. Read this file (always loaded).
2. Read [`wiki/domain.md`](wiki/domain.md). If `status: unconfigured`, route to [`SETUP.md`](SETUP.md) and run the configuration interview before anything else.
3. Read [`CONTEXT.md`](CONTEXT.md) to find your task's workspace.
4. Read that workspace's `CONTEXT.md`.
5. Skim the last 5 entries in [`wiki/log.md`](wiki/log.md) to see recent activity.
6. Load only the docs the workspace `CONTEXT.md` says to load. Skip the rest.
