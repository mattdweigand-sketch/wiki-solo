---
description: Run a memo-first synthesis pass that surfaces corpus distillation candidates for review
---

Run the synthesize workflow. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/synthesize.md`, and follow the Load / Skip list exactly. Promoting reviewed synthesis uses `python3 scripts/capture_gate.py --kind=synthesis`; the workflow owns the exact gate call and post-approval checks.

This command is just a Claude Code shortcut. The workflow file is canonical and model-agnostic.
