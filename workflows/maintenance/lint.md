---
name: wiki-lint
description: Use this workflow when the user says "lint the wiki". Reads all pages and reports structural issues.
---

## Load / Skip

- **Load:** all wiki pages because lint is the one task that legitimately needs breadth. Also load `wiki/contradictions.md` and `wiki/sourcing-queue.md` if they exist; otherwise use the maintenance workflow files as the current operating record.
- **Skip:** `raw/` sources and the other workflow files.

## Steps

Lint is split by enforcement tier. Machine-checkable rules run as a deterministic script; only the rules that need genuine judgment are read by the agent.

1. Run the deterministic linter from the repo root:

   ```bash
   python3 scripts/lint.py
   ```

   It reports two tiers. **Tier 1** is machine-checkable and exits non-zero on any failure: filename and frontmatter-key validity, type/folder match, invalid `confidence` or `source_type`, malformed dates, dangling `[[links]]`, index coverage, duplicate link stems, raw source references, repo folder-structure hygiene, raw/deliverables hygiene, and `.DS_Store` files. These are not judgment calls, so fix them rather than debating them.

   **Tier 2** is ranked candidates the script surfaces but cannot decide: near-duplicate pages, orphans, uncited pages, thin stubs, `confidence: low` pages with enough inbound links to upgrade, missing cross-references, and quote/source mismatches that need review. Treat Tier 2 as a worklist to adjudicate, not as failures.

   Do not chase Tier 2 to zero. Add links only when the relationship is editorially meaningful. Leave weak candidates unresolved and record settled judgments in `scripts/lint-adjudications.json` so lint stops re-surfacing them.

2. Read the pages to assess the judgment-only checks the script deliberately does not attempt:
   - Contradictions between pages.
   - Stale claims superseded by newer sources.
   - Concepts mentioned but lacking their own page.
   - Terms used inconsistently where the right canonical term is a judgment call.
3. Propose fixes for Tier-2 candidates and judgment checks, and ask which ones to apply. Tier-1 failures are not optional.
4. After applying fixes, update the contradiction and sourcing-queue records if present.
5. Rebuild the auto-generated inbound-link sections:

   ```bash
   python3 scripts/rebuild_referenced_by.py
   ```

6. Re-run `python3 scripts/lint.py` and confirm Tier 1 is clean before finishing.
7. Append to `wiki/log.md`:

```text
## [YYYY-MM-DD] lint
Issues found: ...
Fixes applied: ...
Reviewed/no-change: ...
Contradictions opened/closed: ...
```
