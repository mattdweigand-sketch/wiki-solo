# raw/

Drop source documents here, organized into the subfolders defined in [`wiki/domain.md`](../wiki/domain.md) under `raw_taxonomy`. Then run the ingest workflow to triage, extract, and link them into wiki pages.

`raw/` is **immutable** — never edit a file already here. New sources append; existing files stay as the canonical artifact that wiki citations point back to.

This folder is `.gitignore`'d by default since source documents can be sensitive. Override per-project if you want to version your raw corpus.
