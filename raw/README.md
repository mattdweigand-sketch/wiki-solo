# raw/

Source artifacts live here, organized by source type. Drop a file into the right subfolder with a kebab-case filename, then run `/wiki-ingest` to triage, summarize, and link it into `wiki/`.

`raw/` is immutable. Never edit a file already here. New sources append; existing files stay as the canonical artifact that wiki citations point back to.

This folder is gitignored by default since source documents can be sensitive. Only `.gitkeep` and this README are tracked unless a source artifact is intentionally force-added for a committed example.

## Subfolders

This template starts unconfigured. During `SETUP.md`, fill `wiki/domain.md` `raw_taxonomy`, create matching `raw/<bucket>/` folders, and replace or extend the placeholder rows below with the configured buckets. The table must list every actual top-level `raw/` bucket, because `scripts/lint.py --tier1` treats unlisted buckets as structural drift.

| Folder | Holds |
|---|---|
| `customer-research/` | Customer interview notes, support findings, and user research |
| `internal-memos/` | Strategy, planning, and operating memos |
| `release-notes/` | Product, API, and changelog artifacts |
| `ai-research/` | Example AI research and workflow sources, if present in this checkout |
| `social/` | Example social or screenshot captures, if present in this checkout |
| `videos/` | Example video transcript captures, if present in this checkout |
