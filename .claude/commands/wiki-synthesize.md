---
description: Run a synthesis pass, drafting distilled wiki content at draft/low for review
---

Run the synthesize workflow. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/synthesize.md`, and follow the Load / Skip list exactly. Use the workflow's `python3 scripts/synthesis_gate.py` step before promotion and `python3 scripts/validate_synthesis_runs.py` after approved reruns.

This command is just a Claude Code shortcut. The workflow file is canonical and model-agnostic.
