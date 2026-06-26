---
name: wiki-ingest
description: Use this workflow when the user drops a file in raw/ and says "ingest" or "ingest [source]". Handles file organization, source summarization, wiki updates, and promotion-candidate audit.
---

# Ingest Workspace

Turns a raw source into structured wiki pages. Single task: read the source, file it, update the pages and indexes it touches. This `CONTEXT.md` is the whole workflow.

Ingest is a normal durable write. It does not require `scripts/capture_gate.py` approval. Use the capture gate only if the ingest turns into an analysis-capture or artifact-promotion apply route. If an ingest genuinely seems to need staged review before durable edits, raise it with the user instead of running a script.

## Load / Skip

- **Load:** `wiki/SCHEMA.md` (source-type templates + frontmatter), `wiki/domain.md` for active entity types and raw taxonomy, the source file(s) in `raw/`, and the specific existing pages the source touches. At the link step (Step 5), also load `REFERENCES.md` (cross-referencing rules), `wiki/index.md`, `wiki/glossary.md`, and `wiki/log.md`.
- **Skip:** the rest of the wiki, the other workspaces, and `wiki/contradictions.md` unless a clash actually surfaces.

## Calibration Examples

### Good

- Preserve the raw artifact once, then treat it as immutable even if a better title, date, or URL appears later.
- Update the existing pages the source actually changes, then add source-page links and let `rebuild_referenced_by.py` regenerate inbound links.
- Keep source summaries dense and caveated: name what the source claims, what it supports, and what remains unverified.

### Bad

- Rename or edit an existing raw file to make provenance look cleaner.
- Create a new concept page because the source uses a catchy phrase when an existing page already owns the idea.
- Treat customer, metric, market, or strategy claims inside a source as verified facts when the underlying evidence has not been ingested.

## Step 0 - File handling (before reading anything)

`raw/` holds source artifacts. Do not edit existing raw files. If the user provides a new source outside the proper location, place it once under the correct `raw/` subfolder with a kebab-case filename, then treat it as immutable.

1. Check for newly provided files in `raw/` root and any subfolders.
2. For each new file:
   - Decide the right subfolder from `wiki/domain.md` `raw_taxonomy`; check `raw/README.md` and `ls raw/` before inventing a new subfolder.
   - Rename to kebab-case, preserve the extension.
   - Move the file into its subfolder when it is already inside `raw/`; copy or move it into `raw/` when the user provided it elsewhere; do not alter its contents.
3. Confirm the resulting file layout before proceeding.

## Step 1 - Read and discuss

1. Read the source file(s) from `raw/`.
2. Discuss 2-3 key takeaways. Ask clarifying questions only when needed to avoid a wrong durable write; an explicit ingest request should otherwise keep moving.

## Step 2 - Create source page

Create a summary page in `wiki/sources/` named after the source file. Use `source_type` from `wiki/SCHEMA.md` to shape the summary.

## Step 3 - Update existing pages

Identify which existing wiki pages are affected and update them.

## Step 4 - Create new entity pages

Create new entity pages as warranted by the active entity types in `wiki/domain.md` and the schema in `wiki/SCHEMA.md`.

## Step 5 - Update wiki-wide files

1. Update `wiki/glossary.md` with any new or refined terms.
2. Update `wiki/index.md`: add new pages and refresh summaries of changed pages. Index rows must use Markdown links to folder-qualified page paths, such as `[page-slug](concepts/page-slug.md)`, because Tier-1 lint uses those links to verify coverage. Use `[[wikilinks]]` inside authored page bodies and `## Related pages`, not as the index coverage link.
3. Update `wiki/overview.md` if the source shifts the big picture.

## Step 6 - Rebuild inbound links

After all `[[wikilinks]]` are written, refresh the auto-generated `## Referenced by` sections:

```bash
python3 scripts/rebuild_referenced_by.py
```

Run from the repo root. The script is stdlib-only and idempotent. Never hand-edit a `## Referenced by` section; edit `## Related pages` and let the script regenerate the inbound list.

Then run the deterministic Tier-1 gate:

```bash
python3 scripts/lint.py --tier1
```

Tier-1 is machine-checkable: filename and frontmatter-key validity, type/folder match, invalid `confidence` or `source_type`, malformed dates, dangling `[[links]]`, index coverage, repo structure, raw/deliverables hygiene, and related structural rules. Treat failures as must-fix before logging.

Then run full lint and inspect Tier-2 findings only for pages touched by this ingest:

```bash
python3 scripts/lint.py
```

Tier-2 is a review queue, not a failure gate. For newly created or changed pages, check whether the ingest left an orphan source page, missing cross-reference, uncited/thin page, quote mismatch, confidence-upgrade candidate, missing `Open questions / gaps`, or missing `review_by` checkpoint. Fix clear ingest misses before logging; leave unrelated existing candidates for the lint workflow.

## Step 7 - Promotion audit

Before logging, check whether the ingest produced a reusable artifact that belongs outside normal source/concept/analysis updates. Auto-audit if the ingest created or refined:

- A reusable operating rule for future agents.
- A naming, style, or schema convention.
- A repeated workflow step that belongs in `workflows/`.
- A deterministic check that belongs in `scripts/`.
- A durable decision that should live in `wiki/decisions/`.

Do not apply extra promotion automatically unless the user asked to promote, apply, save, file, or update the wiki beyond the ingest. If applying a promotion, run `python3 scripts/capture_gate.py` for that promotion route and stop if it requires approval. Include the recommended route in the log as `Promotion audit: none | <recommended route>`.

## Step 8 - Log

Append to `wiki/log.md`:

```text
## [YYYY-MM-DD] ingest | <source title>
Pages created: ...
Pages updated: ...
Key additions: ...
Contradictions flagged: ...
Promotion audit: none | <recommended route>
```

A single ingest may touch 5-15 wiki pages. That is expected.
