# Query Protocol

How to answer a user question against the wiki. Read once to internalize.

---

## The Flow

```
1. Orient     — read index, optionally primer
2. Pull       — load 3–8 entity pages
3. Synthesize — answer with citations
4. Auto-file  — file to wiki/analyses/ if meaningful (no ask)
5. Log        — append to wiki/log.md, rebuild backlinks if filed
```

---

## 1. Orient

Always start with [`../../../../wiki/index.md`](../../../../wiki/index.md). It lists every wiki page with a one-line summary. Skim until you can identify which 3–8 pages are most relevant.

If the question type is fuzzy ("what should we know about X?" or "help me think through Y"), also read [`../../../../wiki/primer.md`](../../../../wiki/primer.md) — it points to the right entry pages by question type (sales question, product question, strategy question, etc.).

If the question hinges on a specific term, also check [`../../../../wiki/glossary.md`](../../../../wiki/glossary.md) to confirm the canonical definition.

**Don't** read more than these three top-level files at the orientation step.

---

## 2. Pull

Read the 3–8 entity pages you identified. Heuristics:

- For a customer question → the customer page + the products they use + relevant personas
- For a competitor question → the competitor page + the products being compared + any sales-battlecard sources
- For a decision question → the decision page + the initiatives/products it affects
- For a market or strategy question → `wiki/overview.md` + relevant initiatives + relevant decisions
- For a "what's our position on X" question → start at [`../../../../wiki/primer.md`](../../../../wiki/primer.md), follow the routing

If after reading those pages you're still missing context, pull 1–2 more. **Stop at 8.** If 8 pages don't answer the question, that's a signal the wiki has a gap — see step 4.

---

## 3. Synthesize

Write the answer in markdown. Apply the citation rules from [`../../ingest/docs/citation-rules.md`](../../ingest/docs/citation-rules.md):

- Specific facts get `(source: [[page-name]])`.
- Cross-references between wiki pages use `[[page-name]]`.
- Things you inferred from the cited facts get prefixed `Inference:`.
- Things you're speculating about get `Hypothesis:` and a `(based on: ...)` note.
- Confidence-low or contested claims get an explicit caveat in the body.

The answer should stand alone. Someone reading it without the wiki should still understand which claims are well-sourced and which are inferred.

---

## 4. Auto-File if Meaningful

**File the answer to `../../../../wiki/analyses/<slug>.md` automatically when both are true:**

1. The answer synthesized **3+ wiki pages** (real cross-page synthesis, not a lookup).
2. The answer is **>300 words** (substantive, not a quick fact).

**Don't ask first.** Notify in one line after filing:

> Filed as `analyses/<slug>.md` — delete if not useful.

Pick a slug that names the *question*, not the answer (e.g., `acme-vs-foo-pricing-positioning.md`, not `acme-wins-on-pricing.md`).

When filing:
- Use [`analysis-template.md`](analysis-template.md) for structure.
- Add proper frontmatter (`type: analysis`, `confidence`, `agent_use_cases`, etc. — see [`../../ingest/docs/schema.md`](../../ingest/docs/schema.md)).
- Add cross-references back to the entity pages cited.
- Update [`../../../../wiki/index.md`](../../../../wiki/index.md) with a one-line summary of the new analysis.

If both criteria aren't met, skip filing — the answer stays in chat. Deletion is cheaper than recall, so err on the side of filing when the criteria are met.

If you noticed a wiki gap (step 2 ran out of pages, or a key claim had no cited source), flag it — either suggest filing a new entity page, or suggest adding to [`../../maintenance/sourcing-queue.md`](../../maintenance/sourcing-queue.md).

---

## 5. Log

Append to [`../../../../wiki/log.md`](../../../../wiki/log.md):

```
## [YYYY-MM-DD] query | <one-line question>
Pages consulted: ...
Output filed: yes — analyses/<slug>.md   (or: no)
Wiki gaps noticed: ... (if any)
```

If a file was created, run `python3 ../../../commands/rebuild_referenced_by.py` to refresh backlinks across the wiki.

Even if the answer wasn't filed, the log entry is useful — it shows what was asked and what existed at the time.

---

## When the Wiki Can't Answer

If the wiki genuinely lacks the answer, say so explicitly. Do **not** silently fill the gap by re-deriving from `raw/`. The right responses, in order of preference:

1. Tell the user the wiki is thin on this topic. Name what's missing.
2. Suggest a sourcing-queue addition (specific raw artifact that would close the gap).
3. If the user wants an answer anyway, label it clearly: "**This answer is not from the wiki — it's an inference from public information.** Confidence: low."
4. Use Web Search if the gap is about an external/public fact (a competitor's recent announcement, etc.) — and clearly cite the URL, marking confidence accordingly.

A wiki gap that an agent papers over is worse than an honest "we don't know yet."
