---
name: wiki-review
description: Use this workflow to review pages whose review_by date is due and record outcome judgments.
---

# Review Workflow

Surfaces pages whose `review_by` checkpoint is due, then lets the user decide whether the page's prediction, decision, or analysis still holds.

## Load / Skip

- **Load:** `python3 scripts/review_due.py` output, the due pages selected for review, `wiki/SCHEMA.md`, and `REFERENCES.md` if cross-links or confidence changes are needed.
- **Skip:** unrelated entity folders, raw sources unless the due page cites one that must be checked, and unrelated workflow files.

## Steps

1. Run `python3 scripts/review_due.py`.
2. Pick only the due pages the user wants reviewed now.
3. For each page, compare the checkpoint against current wiki evidence and the user's judgment.
4. If updating the page, record the outcome in the page body, adjust `confidence:` only when justified, and advance or remove `review_by`.
5. Run `python3 scripts/rebuild_referenced_by.py` and `python3 scripts/lint.py --tier1` after durable edits.
6. Log material review outcomes in `wiki/log.md`.

Review is judgment work. The script only surfaces due pages; it does not decide whether an outcome succeeded, failed, or remains open.
