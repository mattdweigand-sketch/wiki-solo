---
name: wiki-ingest
description: Run the wiki ingest workflow. Use when the user says /wiki-ingest, wiki-ingest, ingest a source, drop into raw and ingest, or wants a raw artifact turned into wiki pages.
---

# Wiki Ingest

Run the ingest workflow for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/ingest/CONTEXT.md`.
6. Follow that workflow's Load / Skip list exactly.
7. Preserve any new source once under the correct `raw/` subfolder before treating it as immutable.
8. Create or update the source page and related pages as the workflow directs.
9. Run `python3 scripts/rebuild_referenced_by.py`.
10. Run `python3 scripts/lint.py --tier1`.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
