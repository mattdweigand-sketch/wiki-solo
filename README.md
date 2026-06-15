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

Think of the wiki as a compounding context loop:

1. **Configure the domain.** A fresh clone starts unconfigured. `SETUP.md` fills in who or what the wiki is about, which entity types matter, and how raw sources should be organized.
2. **Add sources.** Source artifacts live in `raw/`. They are treated as immutable evidence.
3. **Ingest sources into pages.** The ingest workflow summarizes each source in `wiki/sources/`, then updates the relevant entity pages in `wiki/`.
4. **Use the wiki to answer questions.** Research reads the maintained wiki pages first, not every raw source again. Substantial answers can be saved as analyses.
5. **Capture what should persist.** Decisions, observations, reusable artifacts, and operating rules can be routed into the right durable home instead of staying buried in chat.
6. **Maintain and synthesize.** Lint finds broken structure, stale claims, contradictions, citation issues, and source gaps. Synthesis turns accumulated pages into higher-level overview updates, open questions, and cluster analyses.
7. **Back up the corpus.** Export builds a local zip that includes both the wiki and gitignored raw sources.

The key safeguards are:

- Agents route through `AGENTS.md` and `CONTEXT.md` so they load only the workflow they need.
- Facts cite `wiki/sources/` pages; inferred claims are marked as inference or hypothesis.
- Authored links live in `## Related pages`; generated backlinks live in `## Referenced by`.
- `wiki/log.md`, `wiki/sourcing-queue.md`, and `wiki/synthesis.md` track what changed, what evidence is still missing, and what has been distilled.
- Approval gates protect analysis capture, artifact promotion, and synthesis promotion.
- Deterministic scripts rebuild backlinks, lint structure, validate approval ledgers, test the workflow machinery, and export backups.

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md) and the files under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

The old no-write harness is archived under `archive/wiki-harness/`. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
