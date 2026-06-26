---
name: wiki-capture-decision
description: Use this workflow when the user says "capture decision [topic]" or describes an organizational decision to preserve. Decisions are first-class because they prevent context from turning into folklore.
---

## Load / Skip

- **Load:** `wiki/SCHEMA.md` (decision frontmatter), `wiki/index.md` to check whether an existing decision already owns the topic, and the specific entity pages the decision affects.
- **Skip:** raw sources and unrelated entity folders.

## Capture Preflight

Decision capture does not require `scripts/capture_gate.py` approval unless it is being applied as part of artifact promotion or analysis capture. This workflow owns the quality of the decision record.

## Steps

1. Check `wiki/index.md` and `wiki/decisions/` for an existing decision page that already owns the topic. Update that page when it exists; create a new page in `wiki/decisions/` only when no current page fits. Use frontmatter from `wiki/SCHEMA.md`.
2. Capture:
   - The decision made
   - The reasoning
   - Alternatives rejected and why
   - The date
   - When to revisit
   - Entities affected
3. Cross-link from affected entity pages back to this decision.
4. Add or update the `wiki/index.md` row for the decision page.
5. Run `python3 scripts/rebuild_referenced_by.py`
6. Run `python3 scripts/lint.py --tier1`
7. Append to `wiki/log.md`:

```
## [YYYY-MM-DD] decision | <decision summary>
Page created/updated: decisions/<slug>
Affects: ...
Verification: rebuild_referenced_by.py, lint.py --tier1
```
