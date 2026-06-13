# Decision Capture

How to record a decision as a wiki page. Loaded when the user says "capture decision [topic]" or describes a decision in passing.

Decisions are first-class because they're what makes this a *company context layer* rather than indexed documentation. Capture early and liberally — a half-formed decision page is more useful than a perfect one written six months late.

---

## Page Format

`../../../wiki/decisions/<slug>.md`

```yaml
---
title: <Decision-as-statement, title-cased>
type: decision
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [list of wiki/sources/ pages that informed this — call notes, exec memos, board decks]
tags: [topic tags — pricing, product, gtm, etc.]
confidence: high | medium | low | contested
agent_use_cases:
  - <e.g., "answering 'why did we move off Stripe?'">
  - <e.g., "context for downstream pricing decisions">
revisit: YYYY-MM-DD | "when X happens" | "no scheduled revisit"
decider: <role or person>
---
```

`type: decision` is required. `revisit` and `decider` are required for decisions specifically (they're not in the general entity frontmatter).

---

## Body Structure

```markdown
# <Title>

## Decision
<One sentence. The thing that was decided.>

## Context
<2–4 sentences. What prompted the decision? What was the forcing function?>

## Reasoning
<Why this option won. The case for. Cite sources where applicable.>

## Alternatives Considered (and Why Rejected)
- **<Alternative 1>** — <Why not. Cite if relevant.>
- **<Alternative 2>** — <Why not.>
- (More if material.)

## Affects
- [[<entity-page>]] — <how this decision changes that entity>
- [[<entity-page>]] — <…>

## Revisit
- **When:** <date or trigger>
- **Why revisit:** <what would change the decision>
- **Owner of revisit:** <role or person>

## Open Questions
<Anything unresolved. The decision was made; some implementation questions may not be.>
```

---

## Cross-Linking

A decision page is only useful if it's reachable. After creating:

1. Add a back-link from each entity in the **Affects** list. Add a "Decisions" or "Recent decisions" section to those entity pages if one doesn't exist. If you add the decision under `## Related pages`, use a typed relationship label from [`../../../wiki/SCHEMA.md`](../../../wiki/SCHEMA.md) when the relationship is clear.
2. If the decision has a metric implication, link from [`../../../wiki/metrics/`](../../../wiki/metrics/) too.
3. Run `python3 scripts/rebuild_referenced_by.py` from the repo root to refresh the auto-generated `## Referenced by` sections.

---

## When to Capture

Capture when:
- The user says "capture decision [topic]"
- The user describes a decision in passing during ingest or research ("we decided to…", "we moved off X because…", "the call was to…")
- A research session surfaces a question whose answer turns out to be "we already decided this" — file the decision page so the next agent doesn't re-litigate

Do NOT capture when:
- The "decision" is actually still under discussion. Capture as a [[concept]] or open question, not a decision.
- The decision is implementation detail (which library to use). Decisions are about strategy, scope, or commitments — not about engineering trivia.

---

## Confidence on Decisions

- `high` — the decision was explicitly made by an authoritative decider (exec, board) and recorded in a primary source (memo, deck, meeting notes).
- `medium` — strong signal of the decision but not formalized (e.g., consistent across multiple Slack threads, but no single artifact).
- `low` — inferred from behavior or off-hand mention. Document what would upgrade confidence.
- `contested` — sources disagree on whether the decision was actually made or what it actually was. Flag and link to [`../../../wiki/contradictions.md`](../../../wiki/contradictions.md).

---

## Logging

After creating the page, append to [`../../../wiki/log.md`](../../../wiki/log.md):

```
## [YYYY-MM-DD] decision | <one-line decision summary>
Page created: decisions/<slug>
Affects: <list of affected entity pages>
```
