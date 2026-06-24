---
description: Route a useful artifact to the right durable wiki home
---

Run the artifact promotion router. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/artifact-promotion.md`, and classify the artifact before editing into exactly one primary route: discard, ingest, analysis-capture, update-existing-page, create-page, capture-decision, capture-experience, workflow-update, or script.

This command is just a Claude Code shortcut. The workflow file is canonical and model-agnostic. Return an audit unless durable-write intent is already clear; the workflow owns the capture gate and validation steps.

$ARGUMENTS
