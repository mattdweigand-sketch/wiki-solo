---
name: wiki-lint
description: Run the wiki lint workflow. Use when the user says /wiki-lint, wiki-lint, lint the wiki, run lint, or wants deterministic and judgment-oriented wiki checks.
---

# Wiki Lint

Run the lint workflow for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/maintenance/lint.md`.

Invoking `/lint`, `/wiki-lint`, or `wiki-lint` is an explicit request to run the full lint workflow, including the verifier-agent evidence check described in `workflows/maintenance/lint.md`. Do not ask for separate confirmation before using verifier agents unless the user asks for deterministic-only lint, no subagents, or skipping the evidence check.

Use `python3 scripts/lint.py --tier1` as the deterministic gate.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
