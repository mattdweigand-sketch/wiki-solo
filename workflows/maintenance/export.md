---
name: wiki-export
description: Use this workflow when the user says "export the wiki" or wants a local corpus zip. Builds a zip of the template, wiki, and gitignored raw/ sources.
---

# Export Workflow

## Load / Skip

- **Load:** nothing beyond this file. The export is mechanical; no wiki content needs to be read.
- **Skip:** all wiki pages, raw sources, other task files.

## Why this exists

`raw/` is gitignored, so the git remote may not hold source artifacts. This export builds a local zip of the corpus and operating framework: wiki pages plus raw sources plus workflows, scripts, wrappers, CI, and top-level docs.

## Steps

1. From the repo root, build and verify the zip into `tmp/` (gitignored), stamped with today's date:

   ```bash
   python3 scripts/export_wiki.py --date YYYY-MM-DD
   ```

   This includes `wiki/`, `raw/`, `workflows/`, `scripts/` with fixtures and ledgers, `.claude/commands/`, `.codex/skills/`, `.github/workflows/`, and the top-level docs. It excludes `.git/`, `tmp/`, `deliverables/`, Claude worktrees, local Claude settings, Finder metadata, `.env`, and generated zip files.

2. If you need to inspect before building, run:

   ```bash
   python3 scripts/export_wiki.py --dry-run --date YYYY-MM-DD
   ```

3. Report the absolute path to the zip. Do not upload it anywhere unless the user explicitly gives a destination.
4. No `wiki/log.md` entry. The export changes no wiki content; the zip in `tmp/` is a disposable artifact until the user moves it.

## Privacy

The corpus may contain sensitive organization data. Do not upload, email, or share an export without explicit user approval for the destination.
