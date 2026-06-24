---
title: Activity Log
type: log
created: 2026-05-17
updated: 2026-05-17
---

# Activity Log

Append-only history of ingest, lint, query, and decision-capture sessions. Newest entries on top.

---

## 2026-06-16 — maintenance | promotion apply phase clarity

Change: `workflows/maintenance/artifact-promotion.md` now states that an apply route uses `--phase accepted` (in the mode-description paragraph and in step 5). The direct `capture_gate.py` path no longer leaves the approval-triggering phase unspecified.
Reason: Ported from the personal wiki audit. `--phase drafting` derives `chat-only` and exits 0, so an agent that picked the wrong phase for an apply could skip the promotion approval gate. No other audit finding transferred: the operational eval suite already covers wrapper sync, the Codex synthesize skill already names the synthesis gate, the log is correctly newest-on-top, and the content-level fixes have no template content to touch.
Validation: PASS — Tier-1 lint, full `wiki_eval.py`, and `git diff --check`.

---

## 2026-06-15 — maintenance | audit cleanup and operational coverage

Change: Cleaned up root-accountability audit findings: research chat-only answers no longer require log writes, promotion apply intent excludes ordinary ingest/commit requests, capture workflows update the index for new pages, setup/domain docs use the correct 13 default entity types, export verification checks promised coverage and excludes `.agents/`, duplicate global Codex skill removal refuses divergent copies, and operational evals now cover export, promotion, sync, and approved ledger validators.
Reason: The template should keep deterministic checks clean, avoid unintended writes, and preserve generic wrapper/export boundaries without relying on manual validation.
Validation: PASS — Tier-1 lint, full wiki eval including operational helpers, export dry-run, ledger validators, py_compile, temporary `CODEX_HOME` duplicate-skill checks, and `git diff --check`.

---

## 2026-06-15 — maintenance | command-surface refactor alignment

Change: Aligned the template command surface with the current wiki operating model: repo-local Codex skills are canonical, duplicate global `wiki-*` skills are detected and removable, `/wiki-lint` authorizes the full lint workflow with verifier evidence checks by default, and artifact promotion now states the no-mid-draft/no-context-only write-intent safeguards.
Reason: The template should preserve the recent workflow-control improvements without copying personal wiki content or personal entity assumptions.
Validation: PASS — `py_compile`, Tier-1 lint, capture/synthesis ledger validators, export dry-run, temp `CODEX_HOME` duplicate-skill detect/remove check, full wiki eval, and `git diff --check`.

---

## 2026-06-15 — maintenance | structured command guardrails

Change: Ported structured approval ledgers, capture/synthesis ledger validators, the synthesis approval gate, export zip builder, and updated command workflow docs and wrappers.
Reason: The template should keep deterministic approval and export boundaries in scripts while preserving generic, repo-local workflow judgment.
Validation: PASS — capture/synthesis ledger validators, gate evals, export dry-run, full wiki eval, lint, temp `CODEX_HOME` Codex skill sync check, `py_compile`, and `git diff --check`.

---

## 2026-06-13 — maintenance | tracked Codex skill wrappers

Change: Added tracked `.codex/skills/wiki-*` Codex skill wrappers, documented the Claude/Codex wrapper split, and added `scripts/sync_codex_skills.py` for installing the tracked Codex wrappers into a user's local Codex skill directory.
Reason: General users should be able to use `/wiki-ingest`, `/wiki-capture`, `/wiki-promote`, `/wiki-lint`, `/wiki-synthesize`, and `/wiki-export` in Codex without relying on untracked local skill files.
Validation: PASS — temp `CODEX_HOME` sync plus `--check`, `py_compile`, Tier-1 lint, full wiki eval, and `git diff --check`.

---

## 2026-06-08 — maintenance | agent-neutral promotion shortcut

Change: Added an agent-neutral promotion audit workflow, documented it in root routing, and clarified the README boundary between analysis and promotion.
Reason: Promotion should have a convenient entrypoint without making `.claude/commands/` canonical, and readers should understand that analysis is a saved answer while promotion is a routing decision for ambiguous durable artifacts.
Validation: PASS — shortcut audit mode, apply-gate approval path, `py_compile`, backlink rebuild, Tier-1 lint, provider manifest validation, full wiki eval, and `git diff --check`.

---

## 2026-06-08 — maintenance | README promotion workflow

Change: Simplified README usage sections for reusable-output promotion, image/screenshot source ingest, and save/review thresholds.
Reason: The README should explain the agent-agnostic user-facing routes without command-heavy route tables. Detailed route-policy, lint, approval, visual-evidence, and tool-shortcut mechanics stay in the workflow docs.
Validation: PASS — doc-audit loop, Tier-1 lint, full wiki eval, markdown-link audit, and `git diff --check`.

---

## 2026-06-08 — maintenance | doc-refactor alignment

Change: Audited root, setup, reference, source, research, and maintenance docs against the template-modernization refactor.
Fixes: Aligned default entity-type counts with `wiki/SCHEMA.md`; corrected moved contradiction and sourcing-queue paths; updated research and root capture-gate instructions to use `scripts/capture_gate.py` with required route arguments; replaced a stale harness PRD pointer with the live modernization spec.
Validation: PASS — `rebuild_referenced_by.py`, `lint.py --tier1`, `wiki_validate_provider_manifest.py`, full `wiki_eval.py`, markdown-link audit, and `git diff --check`.

---

## 2026-06-06 — maintenance | typed related-page labels

Change: Added lightweight typed labels for `## Related pages` links while preserving ordinary `[[wikilink]]` syntax.
Allowed labels: `Supports:`, `Contradicts:`, `Depends on:`, `Derived from:`, `Part of:`, `Related:`.
Validation: PASS — backlink rebuild completed; `python3 scripts/lint.py` and `git diff --check` passed.

---

## 2026-05-17 — template initialized

Template state. Awaiting domain configuration — see [`SETUP.md`](../SETUP.md) and [`domain.md`](domain.md).
