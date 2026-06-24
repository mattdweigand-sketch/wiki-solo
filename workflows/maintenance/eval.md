---
name: wiki-eval
description: Run the wiki tooling eval workflow. Use when the user says /wiki-eval, wiki-eval, run wiki evals, run the live evals, or wants to verify that the wiki guardrails still work.
---

# Wiki Eval

Run this workflow when the task is to verify the wiki system itself: shared parsing, scripts, gates, the approval ledger, backlink rebuilds, export behavior, wrapper sync, review_due, and the deterministic Tier-1 gate.

This is different from `/wiki-lint`: lint checks wiki content; eval checks the tools that check and protect the wiki.

## Load / Skip

- **Load:** `scripts/wiki_eval.py` and any failing suite output if a run fails.
- **Skip:** wiki entity pages, raw sources, unrelated workflow files, and Tier-2/Tier-3 content review.

## Steps

1. From the repo root, run:

   ```bash
   python3 scripts/wiki_eval.py
   ```

2. If it fails, inspect only the failing suite and make the narrowest fix.
3. Re-run `python3 scripts/wiki_eval.py` until it passes or a blocker is clear.
4. Run `git diff --check` before finishing when files changed.

## Report

Report whether `wiki_eval.py` passed, which suite failed if any, what was fixed, and whether `git diff --check` passed when relevant.
