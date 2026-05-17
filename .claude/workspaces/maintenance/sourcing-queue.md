---
title: Sourcing Queue
type: style
created: 2026-05-17
updated: 2026-05-17
sources: []
tags: [meta, sourcing, gaps, planning]
confidence: high
---

Prioritized list of sources to ingest next. Empty entity types in the wiki are not bugs — they are often the most differentiating content, and they require sources beyond the surface-level Help Center / website. This page names the artifact most likely to fill each gap.

Refresh after every ingest. Also runnable as the `refresh-sourcing-queue` workflow described in CLAUDE.md.

---

## How to read this queue

Each entry has:
- **Gap** — what the wiki is missing
- **Best-fit source artifact** — the kind of document/conversation most likely to fill it
- **Probable owner** — who at the organization has it
- **Priority** — P0 highest leverage, P3 lowest
- **Status** — `open`, `in-flight`, `closed`

Status moves to `closed` when the gap is meaningfully filled (not perfectly — the wiki compounds, it doesn't finalize).

---

## Next recommended ingest

_(empty — populate as you discover gaps)_

### Template for new entries

```
### SQ-N: <gap title>
- **Gap:** <what's missing>
- **Best-fit source:** <type of artifact>
- **Probable owner:** <name or role>
- **Priority:** P0 | P1 | P2 | P3
- **Status:** open | in-flight | closed
- **Notes:** <optional>
```
