# Analysis Page Template

Use this template when filing a research answer as a page in [`../../../../wiki/analyses/`](../../../../wiki/analyses/). Analyses are first-class wiki entities — frontmatter spec lives in [`../../ingest/docs/schema.md`](../../ingest/docs/schema.md).

---

## Frontmatter

```yaml
---
title: <question-as-statement, title-cased>
type: analysis
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [list of wiki/sources/ pages this synthesis draws from]
tags: [relevant tags — e.g., competitive, customer-segment, pricing]
confidence: high | medium | low | contested
agent_use_cases:
  - <e.g., "answering 'how does Acme compete with Foo on pricing?'">
  - <e.g., "exec briefing on next-FY pricing question">
---
```

`type: analysis` is required. `agent_use_cases` is required (it's how downstream agents find this page).

---

## Body Structure

```markdown
# <Title>

## Summary
<One paragraph. The bottom-line answer. Cite the most important supporting source.>

## Question
<Restate the question that prompted this analysis. Frame it as a question.>

## Key Findings
- **<Finding 1>** (source: [[page-name]])
- **<Finding 2>** (source: [[page-name]], [[page-name]])
- Inference: <reasoning that follows from the cited facts>

## <Topic Section 1>
<Detail. Continue to cite. Mark inferences and hypotheses.>

## <Topic Section 2>
<…>

## Open Questions / Gaps
- <What we don't know yet, and what artifact would close the gap>
- <If a question can't be answered without new sourcing, name it>

## Related Pages
- [[<entity-page-1>]]
- [[<entity-page-2>]]
- [[<other-analysis-if-relevant>]]
```

---

## Length

A typical analysis is **300–800 words**. Longer than that suggests two analyses, or content that should be split into entity pages.

A "Brief" output format (executive 1-pager) caps at 400 words and skips most subsections.

---

## What Makes a Good Analysis Page

- **Standalone.** A reader can understand it without going back to the cited pages — but the citations are there if they want depth.
- **Question-first.** The slug, title, and Question section all name the question. Future agents can search by question and find this page.
- **Honest about confidence.** If the synthesis rests on contested or thin sources, say so — don't smooth it over.
- **Linked back.** Every cited entity page should have this analysis added under its "Related pages" section. (Run `python ../../../commands/rebuild_referenced_by.py` to refresh the auto-generated `## Referenced by` sections after filing.)

---

## What Doesn't Belong as an Analysis

- A single-fact lookup ("when did Customer X sign?") — that's already on the customer page.
- A new entity ("here's a profile of Allvue") — that's an ingest job, not a research output.
- A decision ("we should raise prices") — capture as a decision page via [`../../maintenance/CONTEXT.md`](../../maintenance/CONTEXT.md).
