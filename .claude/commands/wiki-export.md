---
description: Export a zip backup of the entire wiki corpus, including raw sources
---

Run the export workflow. Read `workflows/maintenance/export.md` (via `workflows/maintenance/CONTEXT.md`) and follow it exactly, including its Load / Skip list. Use `python3 scripts/export_wiki.py --date YYYY-MM-DD` to build and verify the zip; use the workflow's explicit upload options only when the user gives a destination. This command is just a Claude Code shortcut; the workflow file is canonical and agent-neutral.

$ARGUMENTS
