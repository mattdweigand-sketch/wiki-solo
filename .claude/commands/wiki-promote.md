---
description: Route a useful artifact to the right durable wiki home
---

Run the artifact promotion router. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/artifact-promotion.md`, and follow it exactly: that workflow owns the route classification, the `scripts/capture_gate.py` approval gate, and the post-approval validate/rebuild/lint steps. This command is just a Claude Code shortcut; the workflow file is canonical and agent-neutral.

$ARGUMENTS
