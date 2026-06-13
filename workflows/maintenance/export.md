---
name: wiki-export
description: Use this workflow when the user says "export the wiki" or wants a local backup. Builds a zip of the corpus, including gitignored raw/ sources.
---

# Export Workflow

## Load / Skip

- **Load:** nothing beyond this file. The export is mechanical; no wiki content needs to be read.
- **Skip:** all wiki pages, raw sources, other task files.

## Why this exists

`raw/` is gitignored, so the git remote may not hold source artifacts. This export builds a local backup of the corpus: wiki pages plus raw sources plus workflows, scripts, archive, command wrappers, and top-level docs.

## Steps

1. From the repo root, build the zip into `tmp/` (gitignored), stamped with today's date:

   ```bash
   mkdir -p tmp
   zip -r tmp/wiki-export-YYYY-MM-DD.zip . \
     -x ".git/*" -x "tmp/*" -x "deliverables/*" \
     -x ".claude/worktrees/*" -x ".claude/settings.local.json" \
     -x "*.DS_Store" -x ".env" -x "*.zip"
   ```

2. Verify the archive:
   - `unzip -l tmp/wiki-export-YYYY-MM-DD.zip` and confirm it contains files under both `wiki/` and `raw/`.
   - Spot-check the file count against:

     ```bash
     find . -type f -not -path "./.git/*" -not -path "./tmp/*" -not -path "./deliverables/*" | wc -l
     ```

3. Report the absolute path to the zip. Do not upload it anywhere unless the user explicitly gives a destination.
4. No `wiki/log.md` entry. The export changes no wiki content; the zip in `tmp/` is a disposable artifact until the user moves it.

## Privacy

The corpus may contain sensitive organization data. Do not upload, email, or share an export without explicit user approval for the destination.
