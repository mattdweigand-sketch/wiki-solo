# <Organization> Wiki

A clonable, agent-readable wiki template for an organization's durable context layer, built on the [Karpathy LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Source documents go into `raw/`. The AI reads them once and incrementally builds a structured, cited, interlinked wiki in `wiki/`. Downstream agents read the wiki to answer questions about the organization, its products, customers, competitors, decisions, metrics, and operating context.

---

## Why this exists

Most AI stacks re-retrieve raw context on every query. The context never compounds.

This wiki inverts that. The AI reads a source once, integrates it into a persistent structure, and throws the retrieval cost away. Future queries hit maintained pages with citations, cross-references, contradictions, and synthesis already in place.

---

## Getting Started

1. Point any agent at the repo. Claude Code reads `CLAUDE.md` automatically; ChatGPT, Codex, Cursor, or a raw API harness start at `AGENTS.md`, then `CONTEXT.md`.
2. If this is a fresh clone, run [`SETUP.md`](SETUP.md) to configure `wiki/domain.md`.
3. Drop a source into `raw/` and say "ingest."
4. Ask questions: "What do we know about X?"

Sources live in `raw/`. Synthesized pages live in `wiki/`. Agents use `AGENTS.md`, `wiki/domain.md`, and `CONTEXT.md` to route each task into the right workflow.

The repo has four common commands, available as slash commands in Claude Code and Codex. Other agents reach the same workflows in plain language through `CONTEXT.md` routing.

- `/ingest` — turn raw sources into durable wiki pages.
- `/capture` — record first-person context, usually decisions or lived experiences.
- `/promote` — route useful artifacts from chats, drafts, scripts, prompts, or work outputs into the right durable home, or decide not to save them.
- `/lint` — run deterministic wiki checks.

Ask questions in plain language. Research answers can stay in chat or become analyses when they should be durable.

---

## Repo Structure

```text
<wiki-root>/
├── AGENTS.md                   # Canonical operating map for agents
├── CLAUDE.md                   # Thin Claude Code wrapper that imports AGENTS.md
├── CONTEXT.md                  # Task router
├── REFERENCES.md               # Stable conventions and layer model
├── SETUP.md                    # First-session configuration workflow
├── config/                     # Harness/provider manifests
├── schemas/                    # Harness artifact schemas
├── scripts/                    # Vendor-neutral gates, harness, lint, and link helpers
├── tests/fixtures/             # Golden and negative harness fixtures
├── workflows/                  # Vendor-neutral workflows, grouped into 3 workspaces
│   ├── ingest/CONTEXT.md       #   raw source -> wiki pages
│   ├── research/CONTEXT.md     #   question -> answer, filed as analysis when substantial
│   └── maintenance/            #   hygiene, harness, artifact promotion, capture
│       ├── CONTEXT.md
│       ├── lint.md
│       ├── wiki-harness.md
│       ├── artifact-promotion.md
│       ├── capture-decision.md
│       ├── capture-experience.md
│       └── refresh-sourcing-queue.md
├── .claude/commands/           # Optional Claude Code wrappers over workflows/
├── .codex/commands/            # Optional Codex wrappers over the same workflows
├── raw/                        # Source artifacts; existing files are immutable
└── wiki/                       # Knowledge layer
    ├── domain.md               # Organization configuration
    ├── SCHEMA.md               # Entity types, frontmatter spec, templates
    ├── index.md                # Master catalog
    ├── overview.md             # Big-picture synthesis
    ├── glossary.md             # Canonical terminology
    ├── primer.md               # Agent entry points by question type
    ├── log.md                  # Chronological activity log
    ├── sourcing-queue.md       # Knowledge gaps and how to fill them
    ├── contradictions.md       # Open and resolved contradictions
    ├── sources/    products/   features/    personas/
    ├── customers/  competitors/ concepts/   initiatives/
    └── decisions/  metrics/    people/      analyses/    style/
```

---

## Configuration

A fresh clone starts unconfigured. `SETUP.md` interviews the user for the organization name, domain, active entity types, custom entity types, `raw/` taxonomy, and example questions. The active entity set lives in [`wiki/domain.md`](wiki/domain.md). The full schema lives in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

---

## Credits

- Pattern by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
