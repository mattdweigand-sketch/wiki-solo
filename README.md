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

The repo has seven common workflow shortcuts. Claude Code and Codex expose them as slash commands; other agents use the same routes through `CONTEXT.md`.

| Command | Use it to |
|---|---|
| `/wiki-ingest` | Turn a raw source into durable wiki pages. |
| `/wiki-capture` | Record first-person context, usually a decision or lived experience. |
| `/wiki-promote` | Route a useful artifact into the wiki, or decide not to save it. |
| `/wiki-lint` | Run deterministic checks, judgment candidates, and evidence review. |
| `/wiki-eval` | Verify that the wiki tools and guardrails still work. |
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

The wiki has one loop: preserve the evidence, summarize it into pages, connect the pages, then check the result.

1. **Preserve the evidence.** Original files, notes, transcripts, and exports live in `raw/`. Once added, they are treated as read-only so later conclusions can always be traced back to the source.
2. **Turn sources into wiki pages.** Each important source gets a page in `wiki/sources/`. Other pages cite those source pages instead of relying on loose files, memory, or uncaptured links.
3. **Build durable knowledge.** Wiki pages capture the configured domain: products, people, decisions, analyses, projects, concepts, or other entity types. Pages use a shared schema, confidence labels, and citations so agents know what is solid, thin, inferred, or contested.
4. **Connect related context.** Pages link to each other with `[[wiki-links]]`. Agents choose meaningful outgoing links; the repo can rebuild the incoming `## Referenced by` lists automatically.
5. **Check and protect the corpus.** Lint scripts, evals, approval gates, and ledgers catch broken structure, weak sourcing, unsupported conclusions, and high-impact edits that need explicit approval.

The result is a memory system that compounds: new work starts from preserved evidence and existing context instead of being re-derived from scratch.

### What Keeps It Reliable

| Mechanism | Purpose |
|---|---|
| Setup and CI checks | `SETUP.md`, `wiki/domain.md`, and GitHub Actions keep fresh clones configured and run deterministic checks on pushes and pull requests. |
| Route-first workflows | Point agents from `AGENTS.md` to `CONTEXT.md` to the right workflow, so they read the instructions that match the task. |
| Immutable raw evidence | Keeps original source material available for later review. |
| Source pages | Give agents a stable, citable summary of each source. |
| Citations and confidence labels | Separate supported facts from inference, hypothesis, thin evidence, or contested claims. |
| Sourcing queue | `wiki/sourcing-queue.md` keeps track of evidence gaps so weak claims become future work instead of disappearing. |
| Contradiction tracking | Records conflicts in `wiki/contradictions.md` instead of overwriting inconvenient claims. |
| Related pages and backlinks | Agents choose which pages should link out to related context; `scripts/rebuild_referenced_by.py` automatically updates each linked page's `## Referenced by` list. |
| Three-tier lint | Tier 1 catches broken structure and does not need review; Tier 2 surfaces suspicious patterns for review; Tier 3 handles meaning and judgment. |
| Evidence review | Full `/wiki-lint` includes sampled citation checks so claims are tested against their cited source pages and raw evidence. |
| Lint adjudications | `scripts/lint-adjudications.json` records reviewed false positives and accepted exceptions so the same candidates are not re-litigated every lint run. |
| Approval gates and ledgers | Approval gates make the agent ask before saving important conclusions; ledgers record what was approved afterward. |
| Live evals | `/wiki-eval` runs `scripts/wiki_eval.py` to test backlinks, lint fixtures, approval gates, ledgers, exports, and command-wrapper assumptions so the guardrails themselves do not drift. |
| Thin command wrappers | Claude, Codex, and other shortcuts point back to the same vendor-neutral workflows, so the wiki does not depend on one agent surface. |

Detailed workflow ownership lives in [`REFERENCES.md`](REFERENCES.md); task instructions live under [`workflows/`](workflows/).

---

## Configuration

A fresh clone starts unconfigured. The setup guide, [`SETUP.md`](SETUP.md), interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions.

The domain config, [`wiki/domain.md`](wiki/domain.md), records what this wiki is about and which entity types are active. The full schema, [`wiki/SCHEMA.md`](wiki/SCHEMA.md), defines the available page types and page rules.

The archived no-write experiment, `archive/wiki-harness/`, is kept for reference. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
