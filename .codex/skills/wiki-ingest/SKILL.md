---
name: wiki-ingest
description: Run the wiki ingest workflow. Use when the user says /wiki-ingest, wiki-ingest, ingest a source, drop into raw and ingest, or wants a raw artifact turned into wiki pages.
---

# Wiki Ingest

Run the ingest workflow for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/ingest/CONTEXT.md`.

Preserve any new source once under the correct `raw/` subfolder before treating it as immutable.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
