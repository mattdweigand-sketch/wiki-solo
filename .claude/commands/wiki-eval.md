---
description: Run the wiki tooling eval workflow
---

Run the wiki eval workflow. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/eval.md`, and follow the Load / Skip list exactly.

This command verifies the wiki system itself: backlinks, lint fixtures, approval gates, ledgers, exports, wrapper sync, and Tier-1 lint. It is different from `/wiki-lint`, which reviews wiki content.

This command is just a Claude Code shortcut. The workflow file is canonical and model-agnostic.

$ARGUMENTS
