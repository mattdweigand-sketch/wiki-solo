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

Raw evidence is source material that should not be edited after it is added. It lives in `raw/`.

A source page is a wiki summary of one raw artifact. Source pages live in `wiki/sources/`. Other wiki pages cite source pages instead of citing loose files or uncaptured URLs.

A citation is the link that shows where a claim came from. Factual claims use `(source: [[source-page]])`.

An interpretation is a conclusion drawn from the evidence. Interpretive claims are labeled `Inference:` or `Hypothesis:` so future readers can tell the difference between sourced facts and reasoning.

A contradiction is a source conflict. Contradictions are recorded instead of silently overwritten.

**Page Contract**

A page contract is the rule set for what each wiki page must contain. The schema file, `wiki/SCHEMA.md`, defines page types, required frontmatter, source types, confidence values, and citation rules.

Confidence is a support label. Pages use `confidence:` metadata so agents can distinguish well-supported, thinly supported, and contested knowledge.

Operating records are the wiki's audit trail. The change log, `wiki/log.md`, records important edits. The evidence queue, `wiki/sourcing-queue.md`, tracks missing support. The conflict register, `wiki/contradictions.md`, tracks unresolved disagreements. The synthesis ledger, `wiki/synthesis.md`, records approved higher-level conclusions.

**Maintenance Checks**

The agent operating map, `AGENTS.md`, explains the repo rules. The task router, `CONTEXT.md`, points each task to the right workflow. Workflows have Load / Skip lists so agents read only the context they need.

The quick deterministic checker, `scripts/lint.py --tier1`, catches mechanical problems: broken links, invalid frontmatter, missing index entries, raw-source reference problems, and folder hygiene issues.

The full lint workflow also surfaces judgment work: stale claims, contradictions, thin sourcing, and citation-support checks.

Related pages are handpicked outgoing links. Agents write them in `## Related pages`.

Backlinks are generated incoming links. The backlink builder, `scripts/rebuild_referenced_by.py`, regenerates `## Referenced by`.

**Approval and Recovery**

An approval boundary is a point where an agent must stop and ask before saving a durable judgment.

The analysis and promotion approval checker, `scripts/capture_gate.py`, protects two actions: saving a research answer as a durable analysis, and promoting a useful artifact into the wiki.

The synthesis approval checker, `scripts/synthesis_gate.py`, protects promoted synthesis: higher-level conclusions that become part of the wiki's durable memory.

A ledger is a structured audit log. Approved runs are written to JSONL ledgers and checked by ledger-validation scripts.

The repo self-test, `scripts/wiki_eval.py`, tests the machinery: lint fixtures, backlink rebuilds, approval gates, ledger validation, export behavior, and command-wrapper sync.

The backup builder, `scripts/export_wiki.py`, creates a local zip backup that includes gitignored raw sources.

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md); task instructions live under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. The setup guide, [`SETUP.md`](SETUP.md), interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions.

The domain config, [`wiki/domain.md`](wiki/domain.md), records what this wiki is about and which entity types are active. The full schema, [`wiki/SCHEMA.md`](wiki/SCHEMA.md), defines the available page types and page rules.

The archived no-write experiment, `archive/wiki-harness/`, is kept for reference. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
