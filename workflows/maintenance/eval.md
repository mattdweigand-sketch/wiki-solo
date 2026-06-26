---
name: wiki-eval
description: Run the wiki tooling eval workflow. Use when the user says /wiki-eval, wiki-eval, run wiki evals, run the live evals, or wants to verify that the wiki guardrails still work.
---

# Wiki Eval

Run this workflow when the task is to verify the wiki system itself: shared parsing, scripts, gates, the approval ledger, backlink rebuilds, export behavior, wrapper sync, review_due, and the deterministic Tier-1 gate.

This is different from `/wiki-lint`: lint checks wiki content; eval checks the tools that check and protect the wiki.

## Wrapper Surface Contract

The live convenience surfaces are `.claude/commands/wiki-*.md` and `.codex/skills/wiki-*/SKILL.md`. They must cover the same seven shortcuts: `wiki-ingest`, `wiki-capture`, `wiki-lint`, `wiki-eval`, `wiki-promote`, `wiki-synthesize`, and `wiki-export`.

Canonical procedure belongs in `workflows/`. A wrapper is only a thin pointer: canonical routing paths plus at most one `scripts/*.py` command hint. It must not carry a numbered-step list or route-classification procedure. Deleting wrapper folders does not remove the underlying wiki workflow; it only removes that agent surface's shortcut.

`scripts/sync_codex_skills.py --wrapper-parity` enforces the checkable part:

- both wrapper surfaces cover exactly the expected `wiki-*` names
- no wrapper carries more than one `scripts/*.py` reference
- no wrapper carries a numbered-step list

It deliberately does not limit how many `workflows/` paths a wrapper names, because naming a workspace `CONTEXT.md` plus the routed task file is the legitimate thin-pointer pattern.

Codex also discovers repo-local `.codex/skills/wiki-*` while working in the repo. Identical global installs under `~/.codex/skills/wiki-*` create duplicate repo and Personal entries. Use:

```bash
python3 scripts/sync_codex_skills.py --check
python3 scripts/sync_codex_skills.py --remove-global --dry-run
python3 scripts/sync_codex_skills.py --remove-global
```

`--remove-global` deletes only byte-identical copies. Divergent global copies are reported and left for manual review.

## Load / Skip

- **Load:** `scripts/wiki_eval.py`; `scripts/sync_codex_skills.py` when wrapper parity or duplicate Codex skills are in scope; any failing suite output if a run fails.
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
