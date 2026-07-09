---
name: wiki-export
description: Run the wiki export workflow. Use when the user says /wiki-export, wiki-export, export the wiki, back up the wiki, or wants a zip backup of the corpus.
---

# Wiki Export

Run the export workflow for this repo. Read `AGENTS.md`, then `CONTEXT.md`, then `workflows/maintenance/CONTEXT.md` and `workflows/maintenance/export.md`, and follow that workflow's Load / Skip list exactly. Use `python3 scripts/export_wiki.py --date YYYY-MM-DD` to build and verify the zip; use the workflow's explicit upload options only when the user gives a destination.
