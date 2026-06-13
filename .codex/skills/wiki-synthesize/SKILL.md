---
name: wiki-synthesize
description: Run the wiki synthesis workflow. Use when the user says /wiki-synthesize, wiki-synthesize, synthesize the wiki, run synthesis, or wants a corpus distillation pass.
---

# Wiki Synthesize

Run the synthesis workflow for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/synthesize.md`.
6. Follow the synthesize workflow's Load / Skip list exactly.
7. Draft or apply synthesis output only as the workflow and the user's instructions allow.
8. Run `python3 scripts/rebuild_referenced_by.py` and `python3 scripts/lint.py --tier1` after durable edits.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
