# AGENTS.md

This file makes the wiki discoverable to OpenAI Codex, Gemini, and any other agent that auto-loads `AGENTS.md`. The canonical instructions and folder map live in [`CLAUDE.md`](CLAUDE.md) — read it next.

---

## What this repo is

A clonable, agent-readable wiki template. Drop source documents into `raw/`, run the ingest workflow, and the wiki builds itself into a structured knowledge base that downstream agents can query and cite. Designed to compound: good answers get filed back into `wiki/analyses/` as first-class citable pages.

---

## First-session check

Read [`wiki/domain.md`](wiki/domain.md). If `status: unconfigured`, route to [`SETUP.md`](SETUP.md) and run the configuration interview before anything else. If `status: configured`, proceed to the task router in [`CONTEXT.md`](CONTEXT.md).

---

## Session start checklist

1. Read [`CLAUDE.md`](CLAUDE.md) — the full folder map and hard rules.
2. Read [`wiki/domain.md`](wiki/domain.md) — check `status`.
3. Read [`CONTEXT.md`](CONTEXT.md) — find your task's workspace.
4. Read that workspace's `CONTEXT.md`.
5. Skim the last 5 entries in [`wiki/log.md`](wiki/log.md).

---

## Task shortcuts

| Task | Go here |
|---|---|
| Ingest a new source file | [`.claude/workspaces/ingest/CONTEXT.md`](.claude/workspaces/ingest/CONTEXT.md) |
| Answer a question from the wiki | [`.claude/workspaces/research/CONTEXT.md`](.claude/workspaces/research/CONTEXT.md) |
| Lint / contradictions / sourcing queue | [`.claude/workspaces/maintenance/CONTEXT.md`](.claude/workspaces/maintenance/CONTEXT.md) |
| Browse what's in the wiki | [`wiki/index.md`](wiki/index.md) |

---

## Slash commands (Claude Code only)

`/ingest` and `/lint` are Claude Code shortcuts. If your agent doesn't support them, follow the prose workflows in the workspace `CONTEXT.md` files linked above — they describe the same steps without the shortcut syntax.

---

## Hard rules

1. **Never modify `raw/`.** It grows monotonically; new sources append, existing files never change.
2. **Flag contradictions explicitly.** Never silently overwrite a contested claim.
3. **Cite every factual claim.** Use `(source: [[source-page]])`. Mark inferences with `Inference:` or `Hypothesis:`.
4. **Workspaces are siloed.** Each workspace's `CONTEXT.md` says exactly what to load — don't cross-load.
