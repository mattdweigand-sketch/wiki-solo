---
name: wiki-capture-experience
description: Use this workflow when the user says "capture observation", "capture field note", or describes a contextual event that should become durable wiki memory.
---

## Load / Skip

- **Load:** `wiki/SCHEMA.md` (frontmatter), `wiki/index.md` when creating a new page, and the most relevant entity folder plus the related pages the observation connects to.
- **Skip:** raw sources and unrelated entity folders.

## Capture Preflight

Observation capture does not require `scripts/capture_gate.py` approval unless it is being applied as part of artifact promotion or analysis capture. This workflow owns judgment about which entity folder fits the observation and what lessons are worth preserving.

## Steps

1. Create or update a page in the most appropriate entity folder. Use frontmatter from `wiki/SCHEMA.md`.
2. Capture:
   - What happened
   - What was learned
   - What would be done differently
   - When it occurred
   - What it connects to
3. Cross-link from related pages back to this page.
4. Add a `wiki/index.md` row if a page was created.
5. Run `python3 scripts/rebuild_referenced_by.py`
6. Run `python3 scripts/lint.py --tier1`
7. Append to `wiki/log.md`:

```
## [YYYY-MM-DD] observation | <observation summary>
Page created/updated: <path>
Connects to: ...
Verification: rebuild_referenced_by.py, lint.py --tier1
```
