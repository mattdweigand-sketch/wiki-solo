---
name: wiki-export
description: Run the wiki export workflow. Use when the user says /wiki-export, wiki-export, export the wiki, back up the wiki, or wants a zip backup of the corpus.
---

# Wiki Export

Run the export workflow for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/maintenance/export.md`.

The canonical command is `python3 scripts/export_wiki.py --date YYYY-MM-DD`.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
