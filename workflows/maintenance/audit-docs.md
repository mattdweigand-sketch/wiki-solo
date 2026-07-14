# Audit Governance Documents

Use this workflow to review the root operating documents, workflow routers, or all `CONTEXT.md` files for duplication, stale instructions, dead paths, and drift from live behavior. An audit request is read-only unless the user explicitly asks to apply fixes.

## Load / Skip

- **Load:** the named documents; `AGENTS.md`, root `CONTEXT.md`, and the routed workspace `CONTEXT.md`; every repo `CONTEXT.md` when the request asks for router-wide coverage; and only the scripts, workflow files, registries, or live paths needed to verify a concrete claim.
- **Skip:** wiki entity pages, raw sources, and unrelated workflows unless a document claim cannot be verified without them.

## Steps

1. Record `git status --short` before the audit so pre-existing or concurrent work stays separate.
2. Inventory the requested documents and every `CONTEXT.md` in scope with `rg --files`; do not assume the router list is complete.
3. Check each operational claim against its live authority: file tree and tracked paths for structure, workspace routers for task ownership, script constants or docstrings for executable behavior, and routed workflow Load / Skip lists for context boundaries.
4. Classify findings as incorrect, stale, dead, duplicative-but-aligned, ambiguous, or verified-current. Report file-and-line evidence and distinguish current defects from future drift risks.
5. For an audit-only request, stop after the report. Do not edit files, run write workflows, append to `wiki/log.md`, or create a deliverable.
6. When the user explicitly asks to apply the findings, write a bounded implementation spec, edit only the approved surfaces, and record changed operating rules in `wiki/log.md`. Workflow and documentation updates do not use `capture_gate.py` unless they also cross one of the three approval boundaries in `AGENTS.md`.
7. Verify proportionately: resolve all Markdown targets, run `python3 scripts/check_schema_doc_parity.py`, `python3 scripts/check_wrapper_parity.py`, `python3 scripts/lint.py --tier1`, and `git diff --check`. Run the full eval suite when scripts, wrappers, or enforced contracts changed.
8. Re-check `git status --short` and report any unrelated or concurrent changes separately.

## Report

Lead with findings ordered by impact. Name documents with no issues, list verification commands and outcomes, and state explicitly whether any files changed.
