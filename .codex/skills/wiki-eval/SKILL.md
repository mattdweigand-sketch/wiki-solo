---
name: wiki-eval
description: Run the wiki tooling eval workflow. Use when the user says /wiki-eval, wiki-eval, run wiki evals, run the live evals, verify wiki guardrails, or wants to check that the wiki tools still work.
---

# Wiki Eval

Run the eval workflow for the current wiki repo. Read `AGENTS.md`, check `wiki/domain.md`, then route through `CONTEXT.md` to `workflows/maintenance/eval.md`.

This checks the wiki system itself: backlinks, lint fixtures, approval gates, ledgers, exports, wrapper sync, and Tier-1 lint. It is different from `/wiki-lint`, which reviews wiki content.

The canonical command is `python3 scripts/wiki_eval.py`.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
