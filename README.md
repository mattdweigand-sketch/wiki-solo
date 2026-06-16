# <Organization> Wiki

A clonable, agent-readable wiki template for company, project, or personal context, based on the [Karpathy LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Put source documents in `raw/`. Agents turn them into structured, cited, interlinked pages in `wiki/`. Future agents answer from the wiki instead of re-reading the same raw material every time.

---

## Why this exists

Most AI workflows retrieve context on every query. The work does not compound.

This repo turns context into maintained memory. A source is read once, integrated into durable pages, and kept traceable through citations, links, contradiction tracking, and synthesis.

---

## Getting Started

1. Clone the repo.
2. Point an agent at it. Claude Code can start at `CLAUDE.md`; other agents start at `AGENTS.md`.
3. Run [`SETUP.md`](SETUP.md) to configure `wiki/domain.md`.
4. Add source files under `raw/`, then ask the agent to ingest them.
5. Ask questions in plain language.

Sources live in `raw/`. Synthesized pages live in `wiki/`. Agents use `AGENTS.md`, `wiki/domain.md`, and `CONTEXT.md` to route each task into the right workflow.

## Agent Setup Prompt

Copy this into your coding agent to download and configure a local wiki from this template:

```text
Download https://github.com/mattdweigand-sketch/wiki-solo locally as a new wiki folder.

Ask me where to put it and what to name the folder. Then clone the repo, enter it, read AGENTS.md, and follow SETUP.md because wiki/domain.md starts as status: unconfigured.

After setup, run the repo checks:
- python3 scripts/wiki_eval.py
- python3 scripts/lint.py --tier1

Report changed files, check results, and any remaining setup choices.
```

The repo has six common workflow shortcuts. Claude Code and Codex expose them as slash commands; other agents use the same routes through `CONTEXT.md`.

| Command | Use it to |
|---|---|
| `/wiki-ingest` | Turn a raw source into durable wiki pages. |
| `/wiki-capture` | Record first-person context, usually a decision or lived experience. |
| `/wiki-promote` | Route a useful artifact into the wiki, or decide not to save it. |
| `/wiki-lint` | Run deterministic checks, judgment candidates, and evidence review. |
| `/wiki-synthesize` | Draft corpus distillations for review and approved promotion. |
| `/wiki-export` | Build a zip backup of the wiki, including raw sources. |

Research answers can stay in chat or become durable analyses when they are worth saving.

## Repo Structure

```text
<wiki-root>/
|-- AGENTS.md                  # Canonical operating map for agents
|-- CONTEXT.md                 # Task router
|-- SETUP.md                   # First-session configuration workflow
|-- REFERENCES.md              # Operating model, stable conventions, and layer model
|-- CLAUDE.md                  # Thin Claude Code wrapper
|
|-- .claude/commands/          # Claude Code slash-command wrappers
|-- .codex/commands/           # Codex command mirrors
|-- .codex/skills/             # Repo-local Codex skill wrappers
|
|-- workflows/                 # Vendor-neutral workflow instructions
|   |-- ingest/                # raw source -> wiki pages
|   |-- research/              # question -> answer
|   `-- maintenance/           # lint, capture, promote, synthesize, sourcing, export
|-- scripts/                   # Deterministic gates, lint, evals, export, link helpers
|-- .github/workflows/         # CI for deterministic wiki checks
|-- archive/wiki-harness/      # Archived no-write autonomy harness
|
|-- raw/                       # Immutable source artifacts
`-- wiki/                      # Maintained knowledge layer
    |-- domain.md              # Context-owner configuration
    |-- SCHEMA.md              # Entity types and page templates
    |-- index.md               # Master catalog
    |-- overview.md            # Big-picture synthesis
    |-- primer.md              # Agent entry points by question type
    |-- glossary.md            # Canonical terminology
    |-- log.md                 # Chronological activity log
    |-- sourcing-queue.md      # Knowledge gaps
    |-- contradictions.md      # Open and resolved contradictions
    |-- synthesis.md           # Synthesis ledger and run history
    `-- <entity folders>/      # sources, products, people, decisions, analyses, etc.
```

---

## How It Works

The operating contract is simple: durable claims should be traceable, structured, checkable, and recoverable.

**Evidence Chain**

Raw artifacts live in `raw/` and are treated as immutable evidence. Ingest turns them into source pages in `wiki/sources/`. Other wiki pages cite those source pages, not loose files or uncaptured URLs.

Factual claims use `(source: [[source-page]])`. Interpretive claims are marked as `Inference:` or `Hypothesis:`. Source conflicts are recorded instead of overwritten.

**Page Contract**

`wiki/SCHEMA.md` defines page types, required frontmatter, source types, confidence values, and citation rules. Pages carry `confidence:` metadata so agents can distinguish well-supported, thinly supported, and contested knowledge.

The wiki also keeps operating records: `wiki/log.md` for changes, `wiki/sourcing-queue.md` for missing evidence, `wiki/contradictions.md` for conflicts, and `wiki/synthesis.md` for approved higher-level distillation.

**Maintenance Checks**

Agents route through `AGENTS.md` and `CONTEXT.md` into workflows with explicit Load / Skip lists. That keeps context focused and reduces accidental broad edits.

`scripts/lint.py --tier1` checks deterministic failures: broken links, invalid frontmatter, index coverage, raw-source references, and folder hygiene. Full lint also surfaces judgment work such as stale claims, contradictions, thin sourcing, and citation-support checks.

Authored relationships and generated backlinks are separate. Agents write `## Related pages`; `scripts/rebuild_referenced_by.py` regenerates `## Referenced by`.

**Approval and Recovery**

Durable judgment has approval boundaries. `capture_gate.py` protects analysis capture and artifact promotion. `synthesis_gate.py` protects promoted synthesis. Approved runs are written to structured JSONL ledgers and validated by ledger-check scripts.

`scripts/wiki_eval.py` tests the machinery: lint fixtures, backlink rebuilds, approval gates, ledger validation, export behavior, and command-wrapper sync. `scripts/export_wiki.py` builds a local backup that includes gitignored raw sources.

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md); task instructions live under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

The old no-write harness is archived under `archive/wiki-harness/`. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
