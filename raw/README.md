# raw/

Source artifacts live here, organized by source type. Drop a file into the right subfolder with a kebab-case filename, then run `/wiki-ingest` to triage, summarize, and link it into `wiki/`.

`raw/` is immutable. Never edit a file already here. New sources append; existing files stay as the canonical artifact that wiki citations point back to.

This folder is gitignored by default since source documents can be sensitive. Only `.gitkeep` and this README are tracked unless a source artifact is intentionally force-added for a committed example.

## Subfolders

This template starts unconfigured, so no source buckets are listed yet. During `SETUP.md`, fill `wiki/domain.md` `raw_taxonomy`, create matching `raw/<bucket>/` folders, and replace this section with a table:

| Folder | Holds |
|---|---|
| `ai-research/` | Example AI research and workflow sources included with the template |
| `social/` | Example social or screenshot captures included with the template |
| `videos/` | Example video transcript captures included with the template |
