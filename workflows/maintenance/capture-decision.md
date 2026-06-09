---
name: wiki-capture-decision
description: Use this workflow when the user says "capture decision [topic]" or describes an organizational decision to preserve. Decisions are first-class because they prevent context from turning into folklore.
---

## Load / Skip

- **Load:** `wiki/SCHEMA.md` (decision frontmatter) and the specific entity pages the decision affects.
- **Skip:** the full index, raw sources, and unrelated entity folders.

## Capture Preflight

Decision capture does not require `scripts/capture_gate.py` approval unless it is being applied as part of artifact promotion or analysis capture. This workflow owns the quality of the decision record.

## Steps

1. Create a page in `wiki/decisions/`. Use frontmatter from `wiki/SCHEMA.md`.
2. Capture:
   - The decision made
   - The reasoning
   - Alternatives rejected and why
   - The date
   - When to revisit
   - Entities affected
3. Cross-link from affected entity pages back to this decision
4. Run `python3 scripts/rebuild_referenced_by.py`
5. Run `python3 scripts/lint.py --tier1`
6. Append to `wiki/log.md`:

```
## [YYYY-MM-DD] decision | <decision summary>
Page created: decisions/<slug>
Affects: ...
Verification: rebuild_referenced_by.py, lint.py --tier1
```
