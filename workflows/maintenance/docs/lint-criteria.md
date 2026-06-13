# Lint Criteria

What a "lint" pass looks for. Loaded when the user says "lint the wiki."

A lint is **diagnosis, not surgery.** Report findings. The user approves fixes. Then apply.

---

## Run the deterministic linter first

Before reading any pages, run `python3 scripts/lint.py` from the repo root. It splits the wiki's rules by how they can be enforced:

- **Tier 1 (deterministic):** machine-checkable structure with no judgment involved — frontmatter keys, `type` matching its folder, valid `confidence` and `source_type` values, kebab-case filenames, dangling `[[links]]`, index coverage, duplicate link stems, raw source references, repo structure, raw/deliverables hygiene, and `.DS_Store` files. These are hard failures. The script exits non-zero when any fail, so they can gate a commit. Fix every Tier-1 finding before anything else.
- **Tier 2 (ranked candidates):** signals a maintainer cannot eyeball across hundreds of pages — orphans, near-duplicates, uncited pages, thin pages, confidence-upgrade candidates, missing cross-references by co-citation, and quote/source mismatches. The script ranks them; a human or agent decides. Tier 2 never fails the run unless you pass `--strict`.
- **Tier 3 (genuine judgment):** contradictions, stale claims, terminology drift, concepts mentioned without a page, confidence downgrades. A script cannot decide these. They are the checklist below.

The checklist below is tagged by tier. The Tier-1 and Tier-2 items are already computed by `scripts/lint.py` — use its output instead of eyeballing them. Spend your reading on Tier 3, where judgment is the whole job.

---

## What to Check

### 1. Contradictions (Tier 3 — judgment)
Two or more pages making incompatible claims about the same entity. Most common forms:
- Different facts (Customer X uses Product A vs. Product B)
- Different framings (Competitor Y is "weak on payments" vs. "strong on payments")
- Different time windows treated as "current" (a stale claim hasn't been superseded)

When found: open or update an entry in [`../../../wiki/contradictions.md`](../../../wiki/contradictions.md). Update the affected pages to `confidence: contested` if not already.

### 2. Stale Claims (Tier 3 — judgment)
A claim superseded by a newer source but not yet reflected on the page.

Signals:
- The page's `updated:` is older than the most recent source it cites
- A newer source in `wiki/sources/` references the same entity
- The page makes a time-bound claim ("currently…", "as of Q2…") that has aged out

When found: propose the update. After applying, refresh the page's `updated:` date.

### 3. Orphan Pages (Tier 2 — `scripts/lint.py` lists them)
A page with no inbound `[[links]]` from other wiki pages. Either:
- It needs back-links added (the page is fine but no one links to it)
- It belongs in the index/glossary/overview but isn't there yet
- It's genuinely vestigial and should be merged or deleted

When found: propose adding back-links from the obvious candidates (the products it relates to, the customers it affects, the initiatives it informs). If genuinely vestigial, ask the user before deleting.

### 4. Missing Cross-References (Tier 2 co-citation; completeness stays Tier 3)
Two pages that *should* link to each other but don't. This splits across tiers:

- **Co-citation candidates (Tier 2):** `scripts/lint.py` ranks pairs that share 3+ outbound links but don't link to each other. Review and decide.
- **Completeness (Tier 3):** whether a product links to all its features, or a customer to every product it uses, needs judgment about the ground-truth set. No script decides it.

Patterns to check:
- Products ↔ features (every product page should link to its features; every feature should link back to its parent product)
- Customers ↔ products (each customer page links to the products they use)
- Customers ↔ personas (each customer page links to the personas involved in the buy)
- Competitors ↔ products (each competitor page names the products it competes with)
- Decisions ↔ initiatives/products/metrics (each decision links to what it affects)
- Analyses → entity pages cited (and entity pages → analyses that reference them)

When adding or adjudicating links in `## Related pages`, prefer the allowed relationship labels from [`../../ingest/docs/schema.md`](../../ingest/docs/schema.md): `Supports:`, `Contradicts:`, `Depends on:`, `Derived from:`, `Part of:`, or `Related:`. Keep the target as a normal `[[wikilink]]`. Plain `- [[page]]` remains valid, and labels should not be mass-backfilled without judgment.

The auto-generated `## Referenced by` section is rebuilt by running `python3 scripts/rebuild_referenced_by.py` from the repo root — do this as part of every lint cycle to catch these mechanically.

### 5. Terminology Drift (Tier 3 — judgment)
The same concept being called by different names across pages.

Process:
- Check [`../../../wiki/glossary.md`](../../../wiki/glossary.md) for the canonical term.
- Find pages using non-canonical synonyms.
- Propose normalizing them (or, if a synonym is genuinely the audience-appropriate term in context, note the deprecated mapping in `glossary.md`).

Domain-specific terms defined in the glossary must be used precisely and consistently. Don't allow agents to paraphrase terms that have an exact definition.

### 6. Concepts Mentioned Without Their Own Page (Tier 3 — judgment)
A page references a concept (e.g., "GP-led secondary," "NAV facility") that lacks a `wiki/concepts/<term>.md` of its own. The reader can't follow the link.

When found: propose creating the concept page. If it would be substantial enough to warrant ingestion of a source, add to [`../../../wiki/sourcing-queue.md`](../../../wiki/sourcing-queue.md) instead.

### 7. Confidence Upgrades (Tier 2 — `scripts/lint.py` flags low-confidence pages with inbound links)
Pages currently marked `confidence: low` that have accumulated enough sources since their last update to upgrade to `medium` or `high`.

When found: propose the upgrade. Apply on approval.

### 8. Confidence Downgrades / `contested` Surfacing (Tier 3 — judgment)
Inverse of #7. A page marked `high` that turns out to rest on a single thin source. Or a page where the contributing sources have started disagreeing.

When found: propose the downgrade or the `contested` flag.

---

## Lint Report Format

Group findings by category. Cap at 10–15 top items. Order by impact (contradictions before terminology drift).

```markdown
## Lint Report — YYYY-MM-DD

### Contradictions (2 new, 1 unresolved)
- [[customer-acme]] vs. [[customer-acme-secondary]]: …
- …

### Stale (3)
- [[product-core]] last updated 2024-12-01; superseded by [[2025-core-product-spec]]
- …

### Orphans (5)
- [[concept-example-term]]: no inbound links — propose adding from [[product-core]], [[customer-acme]]
- …

### Missing Cross-Refs (4)
- [[customer-acme]] uses the core product but doesn't link to [[product-core]]
- …

### Terminology Drift (2)
- "widget" vs. "component" — glossary canonical is "component"
- …

### Confidence Upgrades (2)
- [[product-portal]]: low → medium (3 supporting sources now)
- …
```

After approval and application:
- Update [`../../../wiki/contradictions.md`](../../../wiki/contradictions.md) — opened, closed, status changes.
- Update [`../../../wiki/sourcing-queue.md`](../../../wiki/sourcing-queue.md) — gaps that closed, new gaps surfaced.
- Run `python3 scripts/rebuild_referenced_by.py` from the repo root.
- Log it.
