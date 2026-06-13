---
name: wiki-promote
description: Run the wiki artifact-promotion router. Use when the user says /wiki-promote, wiki-promote, promote, save this artifact, file this, or asks where a useful output belongs in the wiki.
---

# Wiki Promote

Run the artifact-promotion router for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/artifact-promotion.md`.
6. Classify the artifact before editing into exactly one primary route: discard, ingest, analysis-capture, update-existing-page, create-page, capture-decision, capture-experience, workflow-update, or script.
7. Return an audit unless durable-write intent is already clear.
8. Before applying artifact promotion or analysis capture, run `python3 scripts/capture_gate.py` with the proposed route and stop if approval is required.
9. If approved and applied, run `python3 scripts/rebuild_referenced_by.py` and `python3 scripts/lint.py --tier1`.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
