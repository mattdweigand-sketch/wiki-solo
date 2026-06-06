# Ingest

## What This Workspace Is

Where new raw sources become structured wiki pages. The user drops a file in `raw/` (or anywhere) and says "ingest" — this workspace handles triage, extraction, and linking. Output: new and updated pages in [`../../../wiki/`](../../../wiki/).

**Upstream:** the user adds files to `../../../raw/`.
**Downstream:** [`../../../wiki/`](../../../wiki/) gains/updates entity pages and indexes; [`../../../wiki/log.md`](../../../wiki/log.md) records the session.

---

## What to Load

| Task | Load These | Skip These |
|---|---|---|
| Triage a new raw file | [`docs/classification.md`](docs/classification.md) | docs/schema.md (not needed yet), citation-rules.md |
| Extract entities from a source | [`docs/schema.md`](docs/schema.md), [`docs/citation-rules.md`](docs/citation-rules.md), the source itself, any existing pages it touches | docs/classification.md |
| Update an existing page from a new source | [`docs/schema.md`](docs/schema.md), [`docs/citation-rules.md`](docs/citation-rules.md), the existing page, the new source | docs/classification.md |
| Link a freshly extracted page set | [`../../../wiki/index.md`](../../../wiki/index.md), [`../../../wiki/glossary.md`](../../../wiki/glossary.md), [`../../../wiki/log.md`](../../../wiki/log.md) | docs/* — already loaded earlier in pipeline |

For the full per-stage routing, see [`workflows/CONTEXT.md`](workflows/CONTEXT.md).

---

## Folder Structure

```
ingest/
├── CONTEXT.md              ← You are here
├── docs/
│   ├── schema.md           ← Entity types, frontmatter spec, source-type templates
│   ├── citation-rules.md   ← How to cite raw sources, when to mark inferences
│   └── classification.md   ← How to triage raw files (subfolder, rename, type)
└── workflows/
    ├── CONTEXT.md          ← Pipeline routing (read this for the actual ingest)
    ├── 01-triage/          ← Stage 1 scratchpads (rare — most work is on raw/ directly)
    ├── 02-extract/         ← Stage 2 scratchpads (drafts, working notes)
    └── 03-link/            ← Stage 3 scratchpads (cross-link plans)
```

The `01-/02-/03-` folders are mostly empty by design — they're scratchpad space for in-flight work. Most ingest output lands in `../../../wiki/` and `../../../raw/<subfolder>/`, not here.

---

## The Process

The ingest pipeline has 3 stages. Detail lives in [`workflows/CONTEXT.md`](workflows/CONTEXT.md).

```
01-triage  →  02-extract  →  03-link
(file ops)    (read+draft)   (index, glossary, log)
```

A single ingest may touch 5–15 wiki pages. That's expected.

---

## Skills & Tools

| Skill / Tool | When | Purpose |
|---|---|---|
| `/pdf` | Triage/extract — source is a `.pdf` | Read PDF text, tables, forms. OCR if scanned. |
| `/xlsx` | Triage/extract — source is `.xlsx`/`.csv`/`.tsv` | Read structured data, summarize tables |
| `/docx` | Triage/extract — source is a `.docx` | Read Word doc, preserve structure |
| `/pptx` | Triage/extract — source is a `.pptx` | Read decks, extract speaker notes and slide text |
| Web Search | Extract — verifying a date, public quote, or external claim | Confirm facts before they enter the wiki at `confidence: high` |

---

## What NOT to Do

- **Never modify `raw/`.** It's immutable. Triage may *move* a new file into a subfolder (e.g., `raw/competitive-intel/`), but it never edits content.
- **Never silently overwrite a contradiction.** When a new source disagrees with an existing page, flag it in [`../maintenance/contradictions.md`](../maintenance/contradictions.md) and mark the page `confidence: contested`. Don't pick a winner.
- **Never skip stage 03.** Extracting pages without updating `wiki/index.md`, `wiki/glossary.md`, and `wiki/log.md` leaves the wiki disconnected. The link stage is what makes the wiki agent-readable.
- **Don't load research/ or maintenance/ docs here.** Different jobs, different context.
