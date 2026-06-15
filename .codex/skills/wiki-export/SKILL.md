---
name: wiki-export
description: Run the wiki export workflow. Use when the user says /wiki-export, wiki-export, export the wiki, back up the wiki, or wants a zip backup of the corpus.
---

# Wiki Export

Run the export workflow for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/export.md`.
6. Follow the export workflow's Load / Skip list exactly.
7. Build or dry-run the archive with `python3 scripts/export_wiki.py --date YYYY-MM-DD`.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
