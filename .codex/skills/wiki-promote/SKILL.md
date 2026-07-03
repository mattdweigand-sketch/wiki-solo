---
name: wiki-promote
description: Run the wiki artifact-promotion router. Use when the user says /wiki-promote, wiki-promote, promote, save this artifact, file this, or asks where a useful output belongs in the wiki.
---

# Wiki Promote

Run the artifact-promotion router for this repo. Read `AGENTS.md`, then `CONTEXT.md`, then `workflows/maintenance/CONTEXT.md` and `workflows/maintenance/artifact-promotion.md`, and follow it exactly: that workflow owns the route classification, the `scripts/capture_gate.py` approval gate, and the post-approval validate/rebuild/lint steps.
