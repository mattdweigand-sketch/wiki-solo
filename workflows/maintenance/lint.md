---
name: wiki-lint
description: Use this workflow when the user says "lint the wiki". Reads all pages and reports structural issues.
---

## Load / Skip

- **Load:** all wiki pages because lint is the one task that legitimately needs breadth. Also load `wiki/contradictions.md` and `wiki/sourcing-queue.md` if they exist; otherwise use the maintenance workflow files as the current operating record. During the evidence check in Step 3, verifier agents may also load only the raw files cited by sampled claims.
- **Skip:** unrelated `raw/` sources and the other workflow files.

## Steps

Lint is split by enforcement tier. Machine-checkable rules run as a deterministic script; only the rules that need genuine judgment are read by the agent.

Invoking `/lint`, `/wiki-lint`, or `wiki-lint` is an explicit request to run this full workflow, including the verifier-agent evidence check in Step 3. Do not ask for separate confirmation before using those verifier agents. If the user says "deterministic lint only", "no subagents", or "skip evidence check", skip Step 3 and say so in the final report.

1. Run the deterministic linter from the repo root:

   ```bash
   python3 scripts/lint.py
   ```

   It reports two tiers. **Tier 1** is machine-checkable and exits non-zero on any failure: filename and frontmatter-key validity, type/folder match, invalid `confidence` or `source_type`, malformed dates including `review_by`, dangling `[[links]]`, stale Markdown `.md` links, index coverage, duplicate link stems, empty required block lists, raw source references, raw bucket taxonomy drift against `scripts/raw-buckets.json`, tracked raw artifacts, repo folder-structure hygiene, raw/deliverables hygiene, stray tool-call artifacts, and `.DS_Store` files. These are not judgment calls, so fix them rather than debating them.

   **Tier 2** is ranked candidates the script surfaces but cannot decide: near-duplicate pages, orphans, uncited pages, thin stubs, `confidence: low` pages with enough inbound links to upgrade, missing cross-references, quote/source mismatches that need review, and decisions missing `review_by` outcome checkpoints. Treat Tier 2 as a worklist to adjudicate, not as failures.

   Do not chase Tier 2 to zero. Add links only when the relationship is editorially meaningful. Leave weak candidates unresolved and record settled judgments in `scripts/lint-adjudications.json` so lint stops re-surfacing them.

2. Read the pages to assess the judgment-only checks the script deliberately does not attempt:
   - Contradictions between pages.
   - Stale claims superseded by newer sources.
   - Concepts mentioned but lacking their own page.
   - Terms used inconsistently where the right canonical term is a judgment call.
3. Run the **evidence check**: sampled verification that citations support the claims they are attached to. Tier 1 proves a `[[link]]` resolves and the `quote_mismatch` candidates prove quoted text is verbatim; this step checks the semantic rest: overextension, conflation, mismatch, unsupported inference, and quote-shaped claims whose citation sits elsewhere in the paragraph. The linting agent orchestrates but does not judge its own claims.
   1. Build the sample with a per-run random seed the agent does not choose, so the draw is fresh each run and cannot be curated. Re-sample after a failed plant with a new seed:

      ```bash
      mkdir -p tmp
      grep -rn 'source: \[\[' wiki/ --include='*.md' | grep -v 'Referenced by' > tmp/citations.txt
      awk -v seed="$(od -An -N4 -tu4 < /dev/urandom)" 'BEGIN{srand(seed)} {print rand() "\t" $0}' tmp/citations.txt | sort -n | head -25 | cut -f2-
      ```

      Drop any claim already settled in `scripts/lint-adjudications.json` under `reviewed_quotes` or logged as adjudicated in a prior lint entry.
   2. Add one **plant**: pick one sampled claim and write a deliberately overstated paraphrase of it; include it in the verifier prompt batch as if it were real. The plant exists only in that prompt batch; never write it to a wiki page, `tmp/citations.txt`, or the log. If the verifiers fail to flag the plant, the run's clean verdicts do not count. Note it, retune the verifier prompt, and rerun before trusting the results.
   3. Split the sample across 2-3 verifier agents in fresh contexts that have not seen this session. Contract: try to refute each claim against the cited page and, where a raw file exists, the raw file behind that page; verdicts are VERIFIED / OVEREXTENDED / CONFLATED / MISMATCH / NOT-FOUND, each with the source text or absence of source text that decides it.
   4. Adjudicate flags with the user when needed. Confirmed findings get fixed by softening, relabeling provenance per `wiki/SCHEMA.md`, or correcting the citation. Rejected findings count as false positives; durable false positives go to `scripts/lint-adjudications.json` so they stop resurfacing. When fixing, aim for honest confidence rather than maximum hedging.
4. Propose fixes for Tier-2 candidates, evidence-check findings, and judgment checks, and ask which ones to apply. Tier-1 failures are not optional. Residual Tier-2 candidates are acceptable when reviewed and judged too weak, duplicated, or under-sourced to change.
5. After applying fixes, update the contradiction and sourcing-queue records if present.
6. Rebuild the auto-generated inbound-link sections:

   ```bash
   python3 scripts/rebuild_referenced_by.py
   ```

7. Re-run `python3 scripts/lint.py` and confirm Tier 1 is clean before finishing.
8. Housekeeping: empty `tmp/` if it only contains lint scratch files. Contents of `tmp/` are disposable by rule; do not delete anything outside `tmp/`.
9. Append to `wiki/log.md`:

```text
## [YYYY-MM-DD] lint
Issues found: ...
Fixes applied: ...
Reviewed/no-change: ...
Evidence check: N sampled, M flagged, K fixed, R rejected, plant caught: yes/no
Contradictions opened/closed: ...
```

The evidence-check line grades the check itself: `K/M` is verifier precision. If false positives dominate across repeated runs, retune the verifier contract or consider narrowing the evidence-check step. A zero-flag streak alone is not a reason to retire evidence review; failed plants or persistently bad precision are the real signals.
