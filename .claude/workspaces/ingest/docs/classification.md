# Classification (Triage Heuristics)

How to decide where a new raw file goes, what to rename it to, and what `source_type` to assign. Loaded during stage 01 (triage) of the ingest pipeline.

---

## Subfolder Decision

A new raw file goes into the subfolder whose contents it most resembles. Do not invent a new subfolder unless none of the existing ones fit.

| Subfolder | What lives here |
|---|---|
| `raw/competitive-intel/` | Battlecards, analyst reports, win/loss notes, competitor collateral |
| `raw/customer-research/` | Customer interview notes, account briefs, call transcripts |
| `raw/internal-meetings/` | Recordings/notes from internal team meetings |
| `raw/internal-memos/` | Exec memos, written-down decisions, narrative docs |
| `raw/board-and-strategy/` | Board decks, multi-year strategy docs, strategy-export artifacts |
| `raw/strategy-export/` | Strategic exports specifically (overlaps with board-and-strategy — pick the more specific one if both fit) |
| `raw/release-notes/` | Shipped-feature announcements, dated changelogs |
| `raw/product-resources/` | Product specs, internal product docs |
| `raw/product-marketing/` | External-facing product positioning, marketing collateral |
| `raw/payments/`, `raw/transactions/` | Payments-product or transactions-product specific artifacts |
| `raw/contracts/` | Contract templates and executed contracts |
| `raw/legal-compliance/`, `raw/security-compliance/` | Compliance docs, audit material |
| `raw/investor-reporting/` | Materials about LP/investor reporting (the function, not the product) |
| `raw/ai-resources/` | Prompts, AI tooling docs, internal AI research |
| `raw/people/` | Org charts, role definitions, internal team docs |
| `raw/pricing/` | Pricing pages, pricing decisions, packaging docs |
| `raw/workshop-library/` | Workshop materials, training content |
| `raw/<help-center-categories>/` | Help Center corpus (if applicable, mirror the help center taxonomy) |

**Edge cases:**
- A board deck about pricing → `board-and-strategy/` (the artifact type wins over the topic).
- A customer call transcript that contains competitive intel → `customer-research/` (the artifact origin wins).
- A help-doc about transactions → mirror the help center category, not `transactions/`.

If none of these fit, propose a new subfolder name to the user before creating it.

---

## Rename Pattern

Every file gets renamed to kebab-case before moving:

| Original | Renamed |
|---|---|
| `Gen II — Sales Battlecard (Battlecard).pdf` | `gen-ii-battlecard.pdf` |
| `2024 LP Research Summary - Final v3.docx` | `2024-lp-research-summary.docx` |
| `Q3 Board Deck.pptx` | `q3-board-deck.pptx` |
| `payments_pricing_v2.xlsx` | `payments-pricing-v2.xlsx` |

Rules:
- Lowercase everything.
- Replace spaces, em dashes, en dashes, parentheses, and underscores with single hyphens.
- Collapse repeated hyphens to one.
- Drop trailing `-final`, `-v3`, `-clean`, etc. only if they're true noise — keep them if they distinguish multiple versions.
- Preserve the original extension.

---

## Source Type

After triage, when you create the `wiki/sources/` page in stage 02, the page gets a `source_type` from this list:

| `source_type` | Use for |
|---|---|
| `help-doc` | Help Center / documentation articles |
| `slack-thread` | Internal Slack conversations |
| `call-transcript` | Customer or partner call recordings/transcripts |
| `exec-memo` | Internal exec narrative docs |
| `deck` | Generic slide deck (not board, not battlecard) |
| `crm-export` | CRM data exports |
| `strategy-doc` | Multi-year strategy or initiative narratives |
| `release-note` | Shipped-feature announcements |
| `press` | Press releases, external announcements |
| `analyst-report` | Third-party analyst material |
| `competitor-collateral` | Competitor's own marketing/sales material |
| `sales-battlecard` | Internal competitor battlecard (treat as own-POV, not neutral) |
| `product-spec` | Engineering or product spec docs |
| `board-doc` | Board decks, board-prep memos |
| `synthesis` | LLM-generated synthesis integrating multiple sources (treat with care) |
| `other` | Doesn't fit anything above |

The full template for what each source type is *trustworthy for* and *should emphasize* is in [`schema.md`](schema.md) under "Source-Type Summary Templates."

---

## Triage Output

When triage is done, confirm to the user:

```
Files triaged:
  - raw/<old-path-or-new-file>  →  raw/<subfolder>/<kebab-name>.<ext>  (source_type: <type>)
  - …

Proceed to extraction?
```

Wait for the user's go before stage 02.
