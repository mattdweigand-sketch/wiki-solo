# <Organization> Wiki

A clonable, agent-readable wiki template for company, project, or personal context layers, built on the [Karpathy LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Source documents go into `raw/`. The AI reads them once and incrementally builds a structured, cited, interlinked wiki in `wiki/`. Downstream agents read the wiki to answer questions about the context owner: a company, team, project, person, body of work, decisions, goals, source material, and operating context.

---

## Why this exists

Most AI stacks re-retrieve context on every query (RAG). Context never compounds.

This wiki inverts that. The AI reads a source once, integrates it into a persistent structure, and throws the retrieval cost away. Future queries hit maintained pages with citations, cross-references, contradictions, and synthesis already in place.

---

## Getting Started

1. Point any agent at the repo. Claude Code reads `CLAUDE.md` automatically; ChatGPT, Codex, Cursor, or a raw API harness start at `AGENTS.md`.
2. If this is a fresh clone, run [`SETUP.md`](SETUP.md) to configure `wiki/domain.md`.
3. Drop a source into `raw/` and say "ingest."
4. Ask questions: "What do we know about X?"

Sources live in `raw/`. Synthesized pages live in `wiki/`. Agents use `AGENTS.md`, `wiki/domain.md`, and `CONTEXT.md` to route each task into the right workflow.

## Agent Setup Prompt

Copy this into your coding agent to download and configure a local wiki from this template:

```text
Download https://github.com/mattdweigand-sketch/wiki-solo locally as a new wiki folder.

Ask me what the local folder should be named and where to put it. Then clone or download the repo, enter the new folder, and read AGENTS.md. Because wiki/domain.md starts as status: unconfigured, follow SETUP.md to configure the wiki for my organization, project, or personal context.

After setup, run the repo checks:
- python3 scripts/wiki_eval.py
- python3 scripts/lint.py --tier1

Report the files you changed, whether the checks passed, and any follow-up choices I need to make.
```

The repo has six common commands. Claude Code and Codex expose them as slash commands; other agents reach the same workflows through `CONTEXT.md`.

| Command | Use it to |
|---|---|
| `/wiki-ingest` | Turn a raw source into durable wiki pages. |
| `/wiki-capture` | Record first-person context, usually a decision or lived experience. |
| `/wiki-promote` | Route a useful artifact into the wiki, or decide not to save it. |
| `/wiki-lint` | Run deterministic checks, judgment candidates, and evidence review. |
| `/wiki-synthesize` | Draft corpus distillations for review and approved promotion. |
| `/wiki-export` | Build a zip backup of the wiki, including raw sources. |

Ask questions in plain language. Research answers can stay in chat or become analyses when they should be durable.

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

The wiki is built to preserve provenance first, then let agents build on it safely.

**Provenance**

Raw artifacts live in `raw/` and are treated as immutable evidence. Ingest creates a source page in `wiki/sources/` for each artifact, then entity pages cite those source pages instead of citing loose files or external URLs directly.

Specific factual claims use `(source: [[source-page]])`. Interpretive claims are marked as `Inference:` or `Hypothesis:`. Pages also carry `confidence:` metadata, so downstream agents can tell the difference between well-supported, thinly supported, and contested knowledge.

The wiki keeps operating records alongside the pages: `wiki/log.md` records meaningful changes, `wiki/sourcing-queue.md` tracks missing evidence, `wiki/contradictions.md` records unresolved conflicts, and `wiki/synthesis.md` tracks approved higher-level distillation.

**Deterministic Controls**

Agents do not decide where to start from scratch. `AGENTS.md` and `CONTEXT.md` route each task to a workflow with an explicit Load / Skip list, which keeps context focused and reduces accidental broad edits.

`wiki/SCHEMA.md` defines valid page types, required frontmatter, confidence values, source types, and citation rules. `scripts/lint.py --tier1` checks the mechanical parts of that contract: structure, links, index coverage, raw-source references, folder hygiene, and other deterministic failures.

Authored relationships and generated backlinks are separated. Humans or agents write `## Related pages`; `scripts/rebuild_referenced_by.py` regenerates `## Referenced by`, so inbound links stay consistent without hand-maintained backlink drift.

Durable judgment has approval boundaries. `capture_gate.py` protects analysis capture and artifact promotion. `synthesis_gate.py` protects promoted synthesis. Approved runs are written to structured JSONL ledgers and validated by ledger-check scripts.

`scripts/wiki_eval.py` tests the machinery itself: lint fixtures, backlink rebuilds, approval gates, ledger validation, export behavior, and command-wrapper sync. Export builds a local backup that includes gitignored raw sources, so the evidence layer can be preserved with the wiki.

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md); task instructions live under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

The old no-write harness is archived under `archive/wiki-harness/`. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
