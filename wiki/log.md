---
title: Activity Log
type: log
created: 2026-05-17
updated: 2026-05-17
---

# Activity Log

Append-only history of ingest, lint, query, and decision-capture sessions. Newest entries on top.

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
