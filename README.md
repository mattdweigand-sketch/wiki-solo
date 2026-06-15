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

## Try It In 5 Minutes

1. Use this repository as a GitHub template, then open the new repo with your coding agent.
2. Let the agent follow `AGENTS.md`. Because `wiki/domain.md` starts as `status: unconfigured`, it should route to `SETUP.md`.
3. Configure a small fake or real domain: context owner, one-line domain, active entity types, and 2-3 `raw/` buckets.
4. Add one short source file under a configured bucket, for example `raw/customer-research/q2-onboarding-notes.md`.
5. Ask the agent to ingest it. The ingest should create a `wiki/sources/` page, update or create any relevant entity pages, add Markdown-path rows in `wiki/index.md`, rebuild `## Referenced by`, and append `wiki/log.md`.
6. Run the local checks:

```bash
python3 scripts/wiki_eval.py
python3 scripts/lint.py --tier1
```

If both pass, the template is configured and ready for real sources.

## Slash Commands

Claude Code reads the tracked wrappers in `.claude/commands/` directly from the repo.

Codex discovers the tracked repo-local skills under `.codex/skills/` while working in the repo. If duplicate `wiki-*` commands appear, check for identical global copies:

```bash
python3 scripts/sync_codex_skills.py --check
```

To remove duplicate global copies after reviewing the report:

```bash
python3 scripts/sync_codex_skills.py --remove-global
```

If your Codex home is not `~/.codex`, set `CODEX_HOME`. For template validation, use a temporary `CODEX_HOME` so the user's real install is untouched:

```bash
CODEX_HOME=/path/to/codex-home python3 scripts/sync_codex_skills.py --check
```

---

## Repo Structure

```text
<wiki-root>/
|-- AGENTS.md                  # Canonical operating map for agents
|-- CONTEXT.md                 # Task router
|-- SETUP.md                   # First-session configuration workflow
|-- REFERENCES.md              # Stable conventions and layer model
|-- CLAUDE.md                  # Thin Claude Code wrapper
|
|-- .claude/commands/          # Claude Code slash-command wrappers
|-- .codex/commands/           # Codex command mirrors
|-- .codex/skills/             # Repo-local Codex skill wrappers
|
|-- workflows/                 # Vendor-neutral workflow instructions
|   |-- ingest/                # raw source -> wiki pages
|   |-- research/              # question -> answer
|   `-- maintenance/           # lint, promote, capture, synthesize, export
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

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

The old no-write harness is archived under `archive/wiki-harness/`. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
