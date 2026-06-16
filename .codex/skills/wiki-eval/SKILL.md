---
name: wiki-eval
description: Run the wiki tooling eval workflow. Use when the user says /wiki-eval, wiki-eval, run wiki evals, run the live evals, verify wiki guardrails, or wants to check that the wiki tools still work.
---

# Wiki Eval

Run the eval workflow for the current wiki repo.

This checks the wiki system itself: backlinks, lint fixtures, approval gates, ledgers, exports, wrapper sync, and Tier-1 lint. It is different from `/wiki-lint`, which reviews wiki content.

## Procedure

1. Work from the repo root that contains `AGENTS.md`.
2. Read `AGENTS.md`.
3. Check `wiki/domain.md` for setup status; if `status: unconfigured`, route to `SETUP.md` first.
4. Read `CONTEXT.md`.
5. Open `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/eval.md`.
6. Follow the eval workflow's Load / Skip list exactly.
7. Run `python3 scripts/wiki_eval.py`.
8. If files changed, finish with `git diff --check` clean.

This is a tracked Codex skill wrapper. Canonical behavior lives in the repo workflow files.
