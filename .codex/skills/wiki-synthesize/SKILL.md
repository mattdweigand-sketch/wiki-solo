---
name: wiki-synthesize
description: Run the wiki synthesis workflow. Use when the user says /wiki-synthesize, wiki-synthesize, synthesize the wiki, run synthesis, or wants a corpus distillation pass.
---

# Wiki Synthesize

Run the synthesis workflow for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/maintenance/synthesize.md`.

Promoting reviewed synthesis uses `python3 scripts/capture_gate.py --kind=synthesis`; the workflow owns the exact gate call and post-approval checks.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
