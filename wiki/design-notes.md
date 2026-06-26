---
title: Design Notes
type: maintenance
created: 2026-05-17
updated: 2026-06-26
---

# Design Notes

A running record of where this wiki diverges from the [Karpathy LLM-wiki pattern](https://karpathy.ai/zero-to-one/), and why. Useful when revisiting structural decisions later.

## Starter Decisions

### Raw Artifacts Stay Immutable

Raw source artifacts live in `raw/` and are treated as read-only after placement. The wiki layer interprets sources; it does not rewrite them.

### Source Pages Are the Citation Surface

Entity pages cite `wiki/sources/` pages rather than loose raw files wherever possible. This gives future agents a compact, inspectable source summary before they decide whether to open raw evidence.

### Confidence and Contradictions Are First-Class

Pages carry `confidence:` in frontmatter, and contested claims are recorded in [[contradictions]] before they are overwritten. The goal is traceable uncertainty, not forced consensus.

### Sourcing Gaps Stay Visible

Known missing evidence belongs in [[sourcing-queue]] so weak claims become future work instead of disappearing from the operating context.

### Backlinks Are Generated

Agents author `## Related pages`; `scripts/rebuild_referenced_by.py` owns `## Referenced by`. Generated backlinks are a convenience layer, not source material.

### Volatile State Has One Owner

Moving values such as statuses, dates, targets, prices, rates, and stage labels should live on one owner page. Other pages link the owner with stable pointer language instead of copying values that will drift.

### No Specific App Is Required

The wiki uses plain Markdown, scripts, and vendor-neutral workflows. Claude Code, Codex, Cursor, ChatGPT, or a raw API harness can all operate it by following `AGENTS.md`, `CONTEXT.md`, and `workflows/`.
