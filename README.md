# <Organization> Wiki

A clonable, agent-readable wiki template for company, project, or personal context layers, built on the [Karpathy LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Source documents go into `raw/`. The AI reads them once and incrementally builds a structured, cited, interlinked wiki in `wiki/`. Downstream agents read the wiki to answer questions about the context owner: a company, team, project, person, body of work, decisions, goals, source material, and operating context.

---

## Why this exists

Most AI stacks re-retrieve raw context on every query. The context never compounds.

This wiki inverts that. The AI reads a source once, integrates it into a persistent structure, and throws the retrieval cost away. Future queries hit maintained pages with citations, cross-references, contradictions, and synthesis already in place.

---

## Getting Started

1. Point any agent at the repo. Claude Code reads `CLAUDE.md` automatically; ChatGPT, Codex, Cursor, or a raw API harness start at `AGENTS.md`.
2. If this is a fresh clone, run [`SETUP.md`](SETUP.md) to configure `wiki/domain.md`.
3. Drop a source into `raw/` and say "ingest."
4. Ask questions: "What do we know about X?"

Sources live in `raw/`. Synthesized pages live in `wiki/`. Agents use `AGENTS.md`, `wiki/domain.md`, and `CONTEXT.md` to route each task into the right workflow.

The repo has six common commands, available as slash commands in Claude Code and Codex. All share the `wiki-` prefix, so typing `/wiki` groups them in autocomplete. Other agents reach the same workflows in plain language through `CONTEXT.md` routing.

- `/wiki-ingest` turns a raw source into durable wiki pages.
- `/wiki-capture` records first-person context, usually a decision or lived experience.
- `/wiki-promote` routes useful artifacts from chats, drafts, scripts, prompts, or work outputs into the right durable home, or decides not to save them.
- `/wiki-lint` runs deterministic Tier-1 checks plus Tier-2 judgment candidates.
- `/wiki-synthesize` drafts corpus distillations at draft/low confidence for review.
- `/wiki-export` builds a zip backup of the corpus, including raw sources.

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

---

## Repo Structure

```text
<wiki-root>/
|-- AGENTS.md                   # Canonical operating map for agents
|-- CLAUDE.md                   # Thin Claude Code wrapper that imports AGENTS.md
|-- CONTEXT.md                  # Task router
|-- REFERENCES.md               # Stable conventions and layer model
|-- SETUP.md                    # First-session configuration workflow
|-- .github/workflows/          # CI for deterministic wiki checks
|-- archive/wiki-harness/       # Archived no-write autonomy harness
|-- scripts/                    # Deterministic gates, lint, link helpers, eval fixtures
|-- workflows/                  # Vendor-neutral workflows, grouped into 3 workspaces
|   |-- ingest/CONTEXT.md       #   raw source -> wiki pages
|   |-- research/CONTEXT.md     #   question -> answer, filed as analysis when substantial
|   `-- maintenance/            #   hygiene, promotion, capture, synthesize, export
|-- .claude/commands/           # Optional Claude Code wrappers over workflows/
|-- .codex/commands/            # Optional Codex wrappers over the same workflows
|-- raw/                        # Source artifacts; existing files are immutable
`-- wiki/                       # Knowledge layer
    |-- domain.md               # Organization configuration
    |-- SCHEMA.md               # Entity types, frontmatter spec, templates
    |-- index.md                # Master catalog
    |-- overview.md             # Big-picture synthesis
    |-- glossary.md             # Canonical terminology
    |-- primer.md               # Agent entry points by question type
    |-- log.md                  # Chronological activity log
    |-- sourcing-queue.md       # Knowledge gaps and how to fill them
    |-- contradictions.md       # Open and resolved contradictions
    |-- synthesis.md            # Synthesis ledger and run history
    |-- sources/    products/   features/    personas/
    |-- customers/  competitors/ concepts/   initiatives/
    `-- decisions/  metrics/    people/      analyses/    style/
```

---

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the context owner, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

The old no-write harness is archived under `archive/wiki-harness/`. Ordinary ingest does not run a harness preflight.

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
