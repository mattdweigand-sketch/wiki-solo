---
title: Design Notes — Divergences from the Karpathy LLM-Wiki Pattern
type: style
created: 2026-04-24
updated: 2026-04-24
sources: []
tags: [meta, design, schema, agent-context-layer]
confidence: high
---

The Karpathy LLM-wiki pattern, purpose-fit to serve downstream AI agents (not a single human reader). Documents what we kept, what we changed, and why.

---

## Background

This wiki is built on the [Karpathy LLM-wiki pattern](https://github.com/karpathy) — three layers (raw / wiki / schema), a small set of operations (ingest, query, lint), and persistent compounding artifacts (index + log). The original framing is generic and deliberately abstract; Karpathy's note explicitly says "your LLM can figure out the rest" for any specific instantiation.

This file documents the rest — the choices we made when adapting the pattern into a reusable template for any organization.

---

## What we kept verbatim

| Karpathy element | What it gives us |
|---|---|
| **Three-layer architecture** (raw / wiki / schema) | Clean separation between immutable inputs and the LLM-owned synthesis |
| **Ingest / query / lint operations** | Reproducible workflows, surface in CLAUDE.md |
| **`index.md` + `log.md`** | Content catalog + chronological history; works at this scale without an embedding store |
| **Confidence tiers in frontmatter** | Lets downstream agents weight claims without re-deriving |
| **Citations on every fact** | Traceability back to raw sources |
| **Compounding** — update existing pages, don't overwrite | Knowledge graph grows in place |
| **`[[wikilink]]` cross-references** | Cheap graph structure with no infra |
| **Filing query outputs back as analyses** | Conversations become durable artifacts |

---

## Where the pattern doesn't fit a company context layer — and what we changed

The Karpathy pattern assumes a **single human** reading their own wiki. CLAUDE.md states our purpose is to be a **company context layer for downstream AI agents**. That shift forces several modifications.

### 1. Pages must declare what they are *for*, not just what they contain

**Problem.** A human reader browses the wiki and infers a page's relevance. A downstream agent retrieves *one* page and acts on it. Without explicit guidance, the agent either over-trusts or skips it.

**Change.** Every retrievable page carries an `agent_use_cases` frontmatter field listing the question types it is designed to answer. Pages also carry an explicit "What this page is good for" / "What this page does NOT cover" structure where appropriate.

**Excluded from this rule.** Infrastructure pages — `sources/`, `index.md`, `log.md`, `glossary.md`, and `style/` rules — are not retrievable answers and don't need `agent_use_cases`.

### 2. Sources are heterogeneous and need typed handling

**Problem.** The Karpathy pattern treats sources uniformly. Real-world ingest looks like: Help Center docs, Slack threads, sales call transcripts, exec memos, board decks, CRM dumps, analyst reports, competitor collateral. A blanket summary template wastes the differential signal in each.

**Change.** Source pages carry a `source_type` frontmatter field. CLAUDE.md defines a per-type summary template — what to emphasize, what to treat with care. A `slack-thread` summary highlights who said what and open threads; a `deck` summary captures claims as bullet points; a `crm-export` summary preserves structured data.

### 3. Disagreement is the norm, not the exception

**Problem.** A personal wiki rarely sees multi-source contradiction. A company context layer ingests sales positioning, product reality, and exec narrative — these *will* disagree. Burying disagreement in page bodies makes it invisible to retrieval.

**Change.** Two additions:
- A new `confidence: contested` value, indicating active disagreement across sources. Pages with this confidence must include a "Disagreement" section naming sources on each side.
- A first-class [[contradictions]] tracker that lists every open disagreement, the sources, the affected pages, and resolution status. Lint pass updates it.

### 4. Empty entity types are the differentiating content

**Problem.** Karpathy's pattern says empty index sections "signal coverage gaps." Fine for a personal wiki. For a company context layer, the empty types — **customers, competitors, decisions, metrics, initiatives, people** — are exactly what makes this more valuable than indexed documentation. Help Center docs alone never fill them.

**Change.** A [[sourcing-queue]] page that names the artifact most likely to close each gap (CRM export → customers; win/loss interviews → competitor positioning; board deck → strategic initiatives; KPI dashboard → metrics). The queue is reprioritized after every ingest. CLAUDE.md adds a `refresh-sourcing-queue` workflow.

### 5. Decisions deserve a dedicated capture flow

**Problem.** Decisions surface organically in conversation — "we decided to do X because Y, rejected Z." Karpathy's pattern catches them only on ingest of a written source. Most decisions are never written down.

**Change.** A `capture-decision` workflow in CLAUDE.md. Treats decisions as a first-class operation alongside ingest/query/lint. Captures decision + reasoning + alternatives rejected + revisit-when. Decision pages cross-link to affected products, initiatives, and metrics.

### 6. Cold-start agents need a directed entry point

**Problem.** A human has session context — they remember why they're here. A downstream agent invoked fresh has none. A flat index forces it to over-read or guess.

**Change.** A [[primer]] page: "if you have zero context, here is what to read first based on the question you're answering." Maps question types (sales discovery, product positioning, competitor framing, exec brief) to entry-page sequences.

### 7. Style rules ship with the wiki, not bolted on later

**Problem.** Karpathy lists `style/` as one of many directories. For a wiki that downstream agents *generate content on top of*, voice and naming consistency is load-bearing — not nice-to-have.

**Change.** `style/` is seeded before downstream agents run, not after. Initial pages: voice, naming conventions, citation style, structural patterns for agent-generated outputs.

### 8. We do not optimize for human-UX surfaces

**Problem.** Karpathy's "Tips and tricks" lean heavily on Obsidian (graph view, Dataview, Marp). These are human-reader features. Our primary consumer is an agent.

**Change.** No Obsidian dependency. Markdown-first, retrieval-first. If we add tooling later it should improve agent retrieval (e.g., qmd or similar BM25/vector search), not human browsing.

---

## Operational summary of additions

| Addition | Where it lives | Maintained when |
|---|---|---|
| `agent_use_cases` frontmatter | every retrievable page | created/updated |
| `source_type` frontmatter + summary templates | `wiki/sources/*` and CLAUDE.md | every source ingest |
| `confidence: contested` | any page | when sources disagree |
| [[contradictions]] tracker | `wiki/contradictions.md` | every ingest + lint |
| [[sourcing-queue]] | `wiki/sourcing-queue.md` | every ingest + `refresh-sourcing-queue` |
| `capture-decision` workflow | CLAUDE.md + `wiki/decisions/*` | as decisions surface |
| [[primer]] page | `wiki/primer.md` | when entry-point structure changes |
| Seeded style rules | `wiki/style/*` | as conventions stabilize |

---

## What we are deliberately *not* doing

- **No embedding-based RAG infrastructure.** At ~60–200 pages, the index file is sufficient. Revisit when the index is hard to fit in a single agent context window.
- **No Obsidian, Dataview, or Marp.** Human-UX features. Add only if a clear retrieval need emerges.
- **No automatic source ingestion.** Every ingest is human-initiated and human-supervised. Compounds slower, but quality stays high and the schema co-evolves with the corpus.
- **No per-page change history beyond git.** Git is enough.

---

## When to revisit this document

- After a significant ingest type appears that doesn't fit the existing `source_type` taxonomy
- After downstream agents start consuming the wiki and we observe what they get wrong
- When `index.md` exceeds a comfortable single-read context (suggesting we need search infra)
- When the wiki is used by multiple humans (suggesting we may need stricter conventions or review workflows)

---

## Related pages

- [[primer]] — cold-start guide for downstream agents
- [[sourcing-queue]] — what to ingest next
- [[contradictions]] — open disagreements across sources
- [[index]] — full catalog
- [[overview]] — organization synthesis
