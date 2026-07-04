# Wiki Eval

Run this workflow when the task is to verify the wiki system itself: scripts, gates, ledgers, backlink rebuilds, export behavior, stale-text sweep proof, wrapper parity, and the deterministic Tier-1 gate. The `SUITES` registry in `scripts/wiki_eval.py` is the authoritative list of what runs.

This is different from `/wiki-lint`: lint checks wiki content; eval checks the tools that check and protect the wiki.

## Wrapper Surface Contract

The live convenience surfaces are `.claude/commands/wiki-*.md` and `.codex/skills/wiki-*/SKILL.md`. They must cover the same seven shortcuts; `EXPECTED_SKILLS` in `scripts/check_wrapper_parity.py` is the authoritative name registry (the human-facing list lives in `AGENTS.md` and the README command table).

Canonical procedure belongs in `workflows/`. A wrapper is only a thin pointer: canonical routing paths plus at most one `scripts/*.py` command hint. It must not carry a numbered-step list or route-classification procedure. Deleting wrapper folders does not remove the underlying wiki workflow; it only removes that agent surface's shortcut.

`python3 scripts/check_wrapper_parity.py` enforces the checkable part (the `wrapper-parity` suite runs it via `scripts/wiki_eval_wrappers.py`, which also seeds negative fixtures so the checker itself cannot go vacuous):

- both wrapper surfaces cover exactly the expected `wiki-*` names
- no wrapper carries more than one `scripts/*.py` reference
- no wrapper carries a numbered-step list
- every `workflows/*.md` path a wrapper names exists in the tree

It deliberately does not limit how many `workflows/` paths a wrapper names, because naming a workspace `CONTEXT.md` plus the routed task file is the legitimate thin-pointer pattern. It also cannot catch content drift between a wrapper and its twin (one surface carrying a guidance sentence the other lacks); keep wrapper bodies pointer-only so there is nothing to drift.

Historical note: identical global installs under `~/.codex/skills/wiki-*` once created duplicate repo-local and global slash-command entries. That one-time cleanup is complete and its removal machinery was retired 2026-07-01; if duplicate slash entries ever reappear, delete the global copies by hand.

## Load / Skip

- **Load:** `scripts/wiki_eval.py`; `scripts/check_wrapper_parity.py` when the task concerns wrapper parity; any failing suite output if a run fails.
- **Skip:** wiki entity pages, raw sources, unrelated workflow files, and Tier-2/Tier-3 content review.

## Steps

1. From the repo root, run:

   ```bash
   python3 scripts/wiki_eval.py
   ```

2. If it fails, inspect only the failing suite and make the narrowest fix.
3. Re-run `python3 scripts/wiki_eval.py` until it passes or a blocker is clear.
4. Run `git diff --check` before finishing when files changed.

## Failure -> Eval Escalation

When a real tool or workflow failure repeats, has high blast radius, or could silently regress, add the smallest eval fixture that would have caught it. Do not add evals for one-off judgment calls or prose taste. The eval must fail before the fix and pass after the fix; otherwise leave it as a known limitation rather than adding hollow coverage.

## Report

Report whether `wiki_eval.py` passed, which suite failed if any, what was fixed, and whether `git diff --check` passed when relevant.
