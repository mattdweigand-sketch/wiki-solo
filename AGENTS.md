# <Organization> Wiki

Shared project instructions for <Organization> Wiki.

`AGENTS.md` is canonical. Codex and other AGENTS-aware tools read it directly. Claude Code reads
it through the thin `CLAUDE.md` wrapper.

## What this project is

A clonable, agent-readable wiki template. Drop source documents into `raw/`, run the ingest workflow, and the wiki builds itself into a structured knowledge base that downstream agents can query and cite. Designed to compound: good answers get filed back into `wiki/analyses/` as first-class citable pages.

## How to work in this repo

Start by reading `wiki/domain.md`. If `status: unconfigured`, route to `SETUP.md` and run the configuration interview before anything else. If `status: configured`, proceed to the task router in `CONTEXT.md`.

Session start:

1. Read this file.
2. Read `wiki/domain.md` and check `status`.
3. Read `CONTEXT.md` to find the right workspace.
4. Read that workspace's `CONTEXT.md`.
5. Skim the last 5 entries in `wiki/log.md`.
6. Load only the docs the workspace `CONTEXT.md` says to load.

Task routing:

| Task | Go here |
|---|---|
| Ingest a new source file | `.claude/workspaces/ingest/CONTEXT.md` |
| Answer a question from the wiki | `.claude/workspaces/research/CONTEXT.md` |
| Lint / contradictions / sourcing queue | `.claude/workspaces/maintenance/CONTEXT.md` |
| Browse what's in the wiki | `wiki/index.md` |

Claude Code shortcuts: `/ingest` and `/lint`. If your agent doesn't support slash commands, follow the prose workflows in the workspace `CONTEXT.md` files.

## Project structure

- `raw/` — source documents. Immutable: new sources append, existing files never change.
- `wiki/` — knowledge layer. Entity pages, indexes, analyses, glossary, domain config, and log.
- `.claude/` — Claude Code slash commands, helper scripts, and workspace routing.
- `CONTEXT.md` — task router for choosing the right workspace.
- `SETUP.md` — first-session configuration workflow when `wiki/domain.md` is unconfigured.
- `CLAUDE.md` — thin Claude Code wrapper that imports this file.

## Conventions

- `AGENTS.md` is the project operating map. Update this file, not `CLAUDE.md`, when changing startup flow, folder maps, or hard rules.
- `CLAUDE.md` is only a Claude Code compatibility wrapper. It must not contain project-specific instructions beyond importing `AGENTS.md`.
- Cite every factual claim. Use `(source: [[source-page]])`. Mark inferences with `Inference:` or `Hypothesis:`.
- Flag contradictions explicitly. Never silently overwrite a contested claim.
- Workspaces are siloed. Each workspace's `CONTEXT.md` says exactly what to load.
- Use kebab-case filenames and `[[page-name-without-extension]]` internal links.
- Meaningful domain answers that synthesize 3+ wiki pages and exceed 300 words are filed to `wiki/analyses/<slug>.md`, logged in `wiki/log.md`, and followed by `python3 .claude/commands/rebuild_referenced_by.py`.

## Do not do without asking

- Modify existing files in `raw/`.
- Silently resolve or overwrite contradictions.
- Bulk-rewrite wiki pages during maintenance.
- Delete entity folders, custom schema rows, or configured taxonomy outside the setup flow.
- Perform external writes, risky deploys, migrations, or irreversible deletions.

## Deeper context

- `wiki/domain.md` — read first to determine whether this wiki is configured and which entity types are active.
- `CONTEXT.md` — read after `wiki/domain.md` to route the current task.
- `.claude/workspaces/ingest/CONTEXT.md` — read when turning raw sources into wiki pages.
- `.claude/workspaces/research/CONTEXT.md` — read when answering questions from the wiki or filing analyses.
- `.claude/workspaces/maintenance/CONTEXT.md` — read when linting, resolving contradictions, refreshing the sourcing queue, or capturing decisions.
- `SETUP.md` — read only when `wiki/domain.md` has `status: unconfigured` or the user asks to refresh setup.
