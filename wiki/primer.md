---
title: Primer for Downstream Agents
type: style
created: 2026-05-17
updated: 2026-05-17
sources: []
tags: [primer, cold-start, agent-onboarding]
confidence: high
---

Cold-start guide for any AI agent retrieving from this wiki for the first time. Start here if you have no prior context.

---

## What this wiki is

The company / project context layer. Authoritative on whatever has been ingested so far — products, customers, competitors, decisions, terminology, people. Less complete on anything that hasn't been sourced yet (see [`sourcing-queue.md`](../.claude/workspaces/maintenance/sourcing-queue.md) when populated).

If you only read three pages: [[overview]], [[glossary]], [[index]].

---

## How to retrieve from this wiki

1. **Read [[index]] first.** It is the master catalog, grouped by entity type. Every page has a one-line summary and a confidence rating.
2. **Use `agent_use_cases` frontmatter** on each page to confirm fit before relying on it. A page's title is not enough.
3. **Trust `confidence: high` pages directly.** Treat `medium` as probable, `low` as a hypothesis, `contested` as an open question (cross-reference [[contradictions]]).
4. **Citations matter.** Every specific claim links back to a source. If a source is `help-doc`, the claim is product-truth. If it's a `slack-thread` or `call-transcript`, the claim is human-stated and may be informal.
5. **Don't reinvent definitions.** Check [[glossary]] before paraphrasing any domain term — they are precise and often legally or contractually loaded.

---

## Question-type → entry-page map

Use this to find the right starting pages without reading the whole index.

### "What does this organization do?"
- [[overview]] — big-picture synthesis
- [[index#products]] — product surfaces

### "What is product X?" / "How does feature Y work?"
- [[index#products]] for product surfaces
- [[index#features]] for specific features
- Each feature page links back to its product and to the relevant concepts

### "What does this domain term mean?"
- [[glossary]] — canonical definitions
- For deeper treatment, follow the glossary's pointer to the matching `concepts/` page

### "Who uses the product?" (segmentation, persona work)
- [[index#personas]] — buyer / user types
- For named customers: [[index#customers]]

### "Who do we compete with?" (competitive framing)
- [[index#competitors]]
- Do not fabricate competitive claims — flag the gap if a competitor isn't covered

### "What is the strategy?" (initiatives, decisions, metrics)
- [[index#initiatives]], [[index#decisions]], [[index#metrics]]
- Do not invent strategy from product features — mark as inference

### "Where do sources disagree?"
- [[contradictions]] — first-class tracker (in `.claude/workspaces/maintenance/`)
- Pages with `confidence: contested` carry the local view

### "What's the latest activity?"
- [[log]] — chronological record of ingests, queries, decisions, lints
- Last 5 entries usually enough

---

## Voice and citation rules for content you generate on top of this wiki

If you are writing output (a brief, an email, a deck) drawing on this wiki:
- Read [[style]] rules before drafting (when populated)
- Cite the wiki page, not the raw source, in agent-to-human output: "According to the investor portal product page, …"
- Mark inferences as inferences. If the wiki marks something `confidence: low` or `contested`, you must too.
- Use canonical terminology from [[glossary]]. Don't invent acronyms.

---

## Failure modes to avoid

- **Treating a `confidence: medium` page as ground truth.** Especially personas — they're often inferred until customer data lands.
- **Filling competitor or customer pages from your training data.** The wiki being empty here is intentional; fabricating breaks the trust model.
- **Paraphrasing precise domain terms.** Always check [[glossary]] first.
- **Skipping [[contradictions]] when a topic shows up across multiple sources.** If two sources disagreed, the wiki has flagged it — don't pick one silently.

---

## Related pages

- [[index]]
- [[overview]]
- [[glossary]]
