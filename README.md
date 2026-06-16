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

The wiki has four jobs:

- preserve evidence
- organize knowledge
- check for mistakes
- protect durable judgments

**1. Preserve Evidence**

| Plain idea | What it means |
|---|---|
| Raw evidence | Original source material. Add it once to `raw/`, then treat it as read-only. |
| Source page | A wiki summary of one raw artifact. Source pages live in `wiki/sources/`. Other pages cite them instead of loose files or uncaptured URLs. |
| Citation | A link that shows where a claim came from, written as `(source: [[source-page]])`. |
| Interpretation | Reasoning drawn from evidence, not a direct fact. Mark it as `Inference:` or `Hypothesis:`. |
| Contradiction | A source conflict recorded in `wiki/contradictions.md` instead of silently overwriting one claim with another. |

**2. Organize Knowledge**

| Plain idea | What it means |
|---|---|
| Page contract | The rule set for what each wiki page must contain, defined in `wiki/SCHEMA.md`. |
| Confidence | A support label in `confidence:` metadata that tells agents whether a page is well-supported, thinly supported, or contested. |
| Change log | The audit trail for important wiki edits, kept in `wiki/log.md`. |
| Evidence queue | A list of claims or questions that still need better sourcing, kept in `wiki/sourcing-queue.md`. |
| Synthesis ledger | The record of approved higher-level conclusions, kept in `wiki/synthesis.md`. |

**3. Keep It Checkable**

| Plain idea | What it means |
|---|---|
| Agent operating map | The repo rules every agent starts from, kept in `AGENTS.md`. |
| Task router | The file that points each task to the right workflow, kept in `CONTEXT.md`. |
| Workflow instructions | Step-by-step task instructions in `workflows/`, with Load / Skip lists so agents read only what they need. |
| Quick checker | `scripts/lint.py --tier1` catches broken links, invalid page metadata, missing index entries, raw-source reference problems, and folder hygiene issues. |
| Full lint workflow | `/wiki-lint` runs the broader review for stale claims, contradictions, thin sourcing, and citation-support problems. |
| Related pages | Handpicked outgoing links written by agents in `## Related pages`. |
| Backlinks | Generated incoming links. `scripts/rebuild_referenced_by.py` rebuilds the `## Referenced by` sections. |

**4. Protect and Recover**

| Plain idea | What it means |
|---|---|
| Approval boundary | A point where an agent must stop and ask before saving a durable judgment. |
| Analysis and promotion approval checker | `scripts/capture_gate.py` protects two actions: saving a research answer as a durable analysis, and promoting a useful artifact into the wiki. |
| Synthesis approval checker | `scripts/synthesis_gate.py` protects promoted synthesis: higher-level conclusions that become part of durable wiki memory. |
| Ledger | A structured audit log of approved runs, written as JSONL and checked by validation scripts. |
| Repo self-test | `scripts/wiki_eval.py` tests lint fixtures, backlink rebuilds, approval gates, ledger validation, export behavior, and command-wrapper sync. |
| Backup builder | `scripts/export_wiki.py` creates a local zip backup that includes gitignored raw sources. |

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md); task instructions live under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. The setup guide, [`SETUP.md`](SETUP.md), interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions.

The domain config, [`wiki/domain.md`](wiki/domain.md), records what this wiki is about and which entity types are active. The full schema, [`wiki/SCHEMA.md`](wiki/SCHEMA.md), defines the available page types and page rules.

The archived no-write experiment, `archive/wiki-harness/`, is kept for reference. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
