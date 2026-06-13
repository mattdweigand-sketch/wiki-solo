---
name: wiki-capture
description: Run the wiki first-person capture router. Use when the user says /wiki-capture, wiki-capture, capture this decision, remember this experience, or wants a decision, observation, field note, or lived context saved into the wiki.
---

# Wiki Capture

Run the first-person capture router for the current wiki repo.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`.
6. Route to `workflows/maintenance/capture-decision.md` or `workflows/maintenance/capture-experience.md` based on what should be remembered.
7. Follow the selected workflow's Load / Skip list exactly.

Use this for decisions made and lived context. Do not route ordinary first-person capture through artifact promotion unless the user is promoting a separate artifact.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
