# Wiki Schema Reference

Reference spec for entity types, page format, and source-type summary templates. Load during ingest and any time you author or audit a wiki page. Companion files live in `workflows/ingest/docs/`.

---

## Entity Types

| Type | Location | Purpose |
|---|---|---|
| **Source** | `wiki/sources/` | Summary of a raw document — key facts, quotes, metadata, what it informs |
| **Product** | `wiki/products/` | A product offered by the organization (see [[domain]]): positioning, users, core jobs, related features |
| **Feature** | `wiki/features/` | A specific product feature: what it does, who uses it, how it's differentiated |
| **Persona** | `wiki/personas/` | A user or buyer type: role, goals, pain points, objections, buying authority |
| **Customer** | `wiki/customers/` | A named customer or segment: profile, use cases, expansion story, risks |
| **Competitor** | `wiki/competitors/` | A competing vendor: positioning, strengths, weaknesses, where they win/lose |
| **Concept** | `wiki/concepts/` | A domain concept relevant to this wiki's scope (see [[domain]]): definition, why it matters to the organization, common confusions |
| **Initiative** | `wiki/initiatives/` | A strategic bet, launch, or program: goal, owner, status, dependencies |
| **Decision** | `wiki/decisions/` | A decision made, the reasoning, the alternatives rejected, when it should be revisited |
| **Metric** | `wiki/metrics/` | A KPI or North Star: definition, formula, current value, target, owner |
| **Person/Team** | `wiki/people/` | A role, team, or stakeholder (focus on role and responsibility, not biography) |
| **Analysis** | `wiki/analyses/` | A synthesized output: comparison, gap analysis, brief, outline |

---

## Page Format

Every wiki page must have this YAML frontmatter:

```yaml
---
title: <page title>
type: source | product | feature | persona | customer | competitor | concept | initiative | decision | metric | person | analysis
created: YYYY-MM-DD
updated: YYYY-MM-DD
review_by: YYYY-MM-DD         # OPTIONAL — outcome-review checkpoint, especially for decisions
sources: [list of raw source filenames that informed this page]
source_type: help-doc | slack-thread | call-transcript | exec-memo | deck | crm-export | strategy-doc | release-note | press | analyst-report | competitor-collateral | sales-battlecard | product-spec | board-doc | synthesis | other  # SOURCE PAGES ONLY — describes the underlying raw artifact
tags: [relevant tags]
confidence: high | medium | low | contested   # how well-sourced this page is; "contested" means active disagreement across sources
agent_use_cases:                  # which downstream-agent questions this page is meant to answer
  - <e.g., "answering buyer-side product questions">
  - <e.g., "comparing our product to a competitor's">
---
```

`source_type` is required on pages in `wiki/sources/` and omitted elsewhere. `agent_use_cases` is required on every entity page except `sources/`; root meta pages such as `index.md`, `log.md`, and `glossary.md` are infrastructure, not retrievable answers.

`review_by` is optional on most pages and recommended when a claim, forecast, or decision should be graded against future outcomes. Decisions should carry a `review_by` checkpoint unless there is a clear reason not to enroll them in the outcome-review loop.

Followed by:
1. **One-line summary** (used in `index.md` and in agent-retrieved snippets)
2. **Body** — structured with headers, lists, and tables
3. **Open questions / gaps** section — what we don't know yet
4. **Related pages** section — `[[wiki-page-name]]` links, with typed labels when the relationship is clear

**Filenames:** kebab-case, no extension prefix. Page titles in frontmatter may be title-cased.

**Citations:** When stating a specific fact, append `(source: [[source-filename]])`. When stating an opinion or inference, prefix with "Inference:" or "Hypothesis:".

## Related Page Labels

Use lightweight labels in `## Related pages` to say why two pages are connected. The label is plain markdown text; the page reference stays an ordinary `[[wikilink]]` so backlink and index scripts still work.

Allowed labels:

| Label | Meaning |
|---|---|
| `Supports: [[page]]` | This page strengthens, evidences, or confirms the linked page. |
| `Contradicts: [[page]]` | This page conflicts with or materially challenges the linked page. |
| `Depends on: [[page]]` | This page requires the linked page to be understood first or true. |
| `Derived from: [[page]]` | This page was created from, generalized from, or synthesized out of the linked page. |
| `Part of: [[page]]` | This page is a component of the linked larger system, project, or framework. |
| `Related: [[page]]` | Meaningful connection, but no stronger typed relationship fits. |

Examples:

```markdown
## Related pages
- Depends on: [[agent-harness]]
- Supports: [[context-as-moat]]
- Part of: [[sales-harness-os]]
- Derived from: [[outreach-architecture-of-autonomy]]
- Related: [[agent-security]]
```

Plain links remain valid:

```markdown
- [[page]]
```

Do not mechanically backfill every existing related link. Add labels when touching or adjudicating a page, especially in `## Related pages`. Use `Related:` as the fallback when the relationship matters but is not precise.

---

## Source-Type Summary Templates

When ingesting a source, the summary in `wiki/sources/` should be shaped by what that source can be trusted for:

| `source_type` | Trustworthy for | Treat with care | Summary should emphasize |
|---|---|---|---|
| `help-doc` | product surface, terminology | strategy, pricing, customers | feature inventory, user workflows |
| `slack-thread` | informal context, decisions-in-progress | facts (often half-formed) | who said what, decisions reached, open threads |
| `call-transcript` | customer voice, objections, exact quotes | speaker accuracy, abridgements | quotes, named accounts, objections raised |
| `exec-memo` | strategy, intent, internal narrative | implementation status | thesis, assertions, decisions made |
| `deck` | positioning, claims | nuance, caveats | claims as bullet points, audience, date |
| `crm-export` | named accounts, deal stage, structured data | qualitative color | structured tables, totals, ranges |
| `strategy-doc` | initiatives, north stars, multi-year goals | tactical detail | goals, owners, dependencies |
| `release-note` | shipped capabilities, dates | strategy | dated feature list, what changed |
| `press` | external positioning | internal accuracy | quotes, dates, reach |
| `analyst-report` | market view, peer set | internal claims about the organization | market size, peer comparisons, the organization's rating |
| `competitor-collateral` | competitor's stated positioning | objectivity | their claims verbatim, gaps to attack |
| `sales-battlecard` | what we tell sellers about a competitor | factual claims about the competitor (our POV, not neutral) | "Why we win / lose," objection handling, competitor tells |
| `product-spec` | engineering ground truth | GTM framing | requirements, constraints, edge cases |
| `board-doc` | strategic priorities, metric targets | day-to-day truth | priorities, targets, board asks |
| `synthesis` | LLM-synthesized analysis integrating multiple sources | source integration methodology not transparent; may embed interpreter bias | main findings, high-level synthesis, caveats on sources |

---

## Confidence Values

- `high` — multiple sources agree, or an authoritative internal source (spec, exec statement, official doc)
- `medium` — single source, or strong inference from consistent signals
- `low` — speculation, early hypothesis, or single off-hand mention
- `contested` — sources actively disagree; page records both positions and links to [[contradictions]] for the open question

When confidence is `low` or `contested`, state it in the page body too — downstream agents may skip frontmatter. For `contested`, the body must include a "Disagreement" section that names the sources on each side.

## Referenced by

_No inbound links yet._
