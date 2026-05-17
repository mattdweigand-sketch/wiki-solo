# Ingest Pipeline

Three stages. Each stage's output is the next stage's input. Forward flow only.

```
01-triage  →  02-extract  →  03-link
```

---

## Stage Routing

| Stage | Input | Also Load | Output | Skills |
|---|---|---|---|---|
| **01-triage** | New file in `../../../../raw/` (often the root, or a misclassified subfolder) | [`../docs/classification.md`](../docs/classification.md) | File renamed to kebab-case and moved into the right `raw/<subfolder>/`. Confirm layout to user before proceeding. | `/pdf`, `/xlsx`, `/docx`, `/pptx` (just to peek at the file type) |
| **02-extract** | Triaged file in `raw/<subfolder>/` | [`../docs/schema.md`](../docs/schema.md), [`../docs/citation-rules.md`](../docs/citation-rules.md), any existing wiki pages this source touches | Source page in `../../../../wiki/sources/`. New or updated entity pages in `../../../../wiki/<entity-type>/`. | Web Search (verify external claims), file-type skills as needed |
| **03-link** | Extracted entity pages from stage 02 | [`../../../../wiki/index.md`](../../../../wiki/index.md), [`../../../../wiki/glossary.md`](../../../../wiki/glossary.md), [`../../../../wiki/log.md`](../../../../wiki/log.md) | Updated `index.md` (new pages added, changed pages refreshed). Updated `glossary.md` (new/refined terms). New entry appended to `log.md`. Updated `overview.md` if the source shifts the big picture. | — |

Skills accumulate as you move forward: triage uses file readers to peek; extract uses the same readers plus Web Search for verification; link is mostly bookkeeping inside `../../../../wiki/`.

---

## Stage 01 — Triage

When the user says "ingest" (with or without arguments):

1. Scan `../../../../raw/` for files that don't yet sit in an organized subfolder. Check the root and any unfamiliar subfolders.
2. For each new file, decide the right destination subfolder by content type. Reuse existing subfolders when possible:
   - `raw/competitive-intel/` — battlecards, analyst reports, win/loss notes
   - `raw/customer-research/` — interview notes, account briefs
   - `raw/internal-memos/`, `raw/internal-meetings/` — exec/team comms
   - `raw/board-and-strategy/` — board decks, strategy docs
   - `raw/release-notes/`, `raw/product-resources/`, `raw/product-marketing/`
   - `raw/payments/`, `raw/transactions/`, `raw/contracts/`, `raw/legal-compliance/`, `raw/security-compliance/`, `raw/investor-reporting/`
   - `raw/ai-resources/`, `raw/people/`, `raw/pricing/`
   - …and any other established subfolder. Create a new one only if no existing one fits.
3. Rename to kebab-case, preserve the extension. Example: `Gen II — Sales Battlecard (Battlecard).pdf` → `gen-ii-battlecard.pdf`.
4. **Move (don't copy)** into the destination. One copy only.
5. Confirm the resulting layout to the user before proceeding to stage 02.

See [`../docs/classification.md`](../docs/classification.md) for the heuristics that decide subfolder, source type, and rename.

---

## Stage 02 — Extract

For each triaged file:

1. Read the source.
2. Discuss 2–3 key takeaways with the user; ask clarifying questions about context and emphasis.
3. Create a summary page in `../../../../wiki/sources/` named after the source file. Required fields: `source_type`, `confidence`, citations back to the raw filename. Battlecards and other internal sales-enablement artifacts get `source_type: sales-battlecard` so downstream agents weight claims as own-POV, not neutral analysis.
4. Identify which existing wiki pages this source affects. Update them — don't create parallel versions. When the new source disagrees with an existing page, flag it (mark `confidence: contested`, log to [`../../maintenance/contradictions.md`](../../maintenance/contradictions.md)).
5. Create new entity pages as warranted (products, features, personas, customers, competitors, concepts, initiatives, decisions, metrics, people).

Frontmatter spec, source-type templates, and confidence values are all in [`../docs/schema.md`](../docs/schema.md). Citation patterns are in [`../docs/citation-rules.md`](../docs/citation-rules.md).

---

## Stage 03 — Link

After extraction:

1. Update [`../../../../wiki/index.md`](../../../../wiki/index.md) — add new pages, refresh summaries of changed pages.
2. Update [`../../../../wiki/glossary.md`](../../../../wiki/glossary.md) with new or refined terms. If a new term conflicts with an existing entry, reconcile and note the deprecated form.
3. Update [`../../../../wiki/overview.md`](../../../../wiki/overview.md) if the source shifts the big picture.
4. Add back-links: products link to features; features link back to products; customers link to products used, personas involved, competitors considered; decisions link to the initiatives, products, or metrics they affect.
5. Append an entry to [`../../../../wiki/log.md`](../../../../wiki/log.md):
   ```
   ## [YYYY-MM-DD] ingest | <source title>
   Pages created: ...
   Pages updated: ...
   Key additions: ...
   Contradictions flagged: ...
   ```
6. Run `python ../../../commands/rebuild_referenced_by.py` from the repo root to refresh `## Referenced by` sections.

---

## Pipeline Rules

1. **Forward flow only.** Triage → extract → link. No skipping. Changed source → re-run downstream stages.
2. **Each stage loads only what it needs.** See the routing table above.
3. **Never modify `raw/` content.** Triage *moves* and *renames* files; extraction *reads* them. Renaming is a path change, not a content change.
4. **Contradictions get flagged, not resolved.** Flagging is a stage-02 output (mark page `contested`, log to [`../../maintenance/contradictions.md`](../../maintenance/contradictions.md)). Resolution is a maintenance-workspace job.
5. **Stage 03 is non-negotiable.** No ingest is "done" until index, glossary, and log are updated.
