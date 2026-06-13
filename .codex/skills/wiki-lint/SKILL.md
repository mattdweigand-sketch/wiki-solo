---
name: wiki-lint
description: Run the wiki lint workflow. Use when the user says /wiki-lint, wiki-lint, lint the wiki, run lint, or wants deterministic and judgment-oriented wiki checks.
---

# Wiki Lint

Run the lint workflow for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/lint.md`.
6. Follow the lint workflow's Load / Skip list exactly.
7. Run the deterministic checks requested by the workflow.
8. Finish with `python3 scripts/lint.py --tier1` clean unless the workflow explicitly identifies a non-local blocker.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
