---
description: Route a useful artifact to the right durable wiki home
---

Run the artifact promotion router. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/artifact-promotion.md`, and follow it exactly: that workflow owns route classification, the `scripts/capture_gate.py` approval gate, and post-approval validation/rebuild/lint steps. Return an audit unless durable-write intent is already clear.

This command is just a Claude Code shortcut. The workflow file is canonical and model-agnostic.

$ARGUMENTS
