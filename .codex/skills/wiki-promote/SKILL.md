---
name: wiki-promote
description: Run the wiki artifact-promotion router. Use when the user says /wiki-promote, wiki-promote, promote, save this artifact, file this, or asks where a useful output belongs in the wiki.
---

# Wiki Promote

Run the artifact-promotion router for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/maintenance/artifact-promotion.md`.

The approval boundary is `python3 scripts/capture_gate.py`; the workflow owns when and how to call it.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
