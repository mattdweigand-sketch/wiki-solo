# Citation Rules

How to cite sources, mark inferences, and signal confidence inside wiki pages. Loaded during stage 02 (extract) of the ingest pipeline.

---

## Citing a Specific Fact

When stating a specific fact pulled from a source, append the source citation in parentheses:

```markdown
The <competitor> battlecard puts our product ahead on portal usability (source: [[<competitor>-battlecard]]).
```

The cited filename is the `wiki/sources/` page name (kebab-case, no extension). That source page itself cites the raw filename in `raw/<subfolder>/`.

**Multiple sources support the same fact:**
```markdown
The organization closed FY24 with 2,000+ customers (source: [[fy24-board-deck]], [[2024-press-release]]).
```

**Two-hop citations are fine:**
```markdown
Customers cited reporting cadence as a top frustration (source: [[2024-customer-research-summary]]).
```
The reader can follow `[[2024-customer-research-summary]]` to its page and from there to the raw interviews.

---

## Marking Inference and Hypothesis

When stating something the agent inferred (not lifted directly from a source), prefix the sentence with `Inference:` or `Hypothesis:`:

```markdown
Inference: <Competitor>'s recent partner-portal push suggests they're targeting the same admin overlap we own.

Hypothesis: If LP reporting consolidation continues, the LP portal becomes the primary distribution channel within 18 months.
```

The difference:
- **Inference** — a reasonable connection from cited facts. Could be defended.
- **Hypothesis** — speculation worth tracking but not yet defensible. Should be revisited when more data arrives.

Neither needs a `(source: ...)` citation, but both benefit from a `(based on: [[page-1]], [[page-2]])` to show what they're built on.

---

## Confidence Marking

Frontmatter must carry a `confidence` value: `high` | `medium` | `low` | `contested`. Definitions live in [`../../../wiki/SCHEMA.md`](../../../wiki/SCHEMA.md).

When `confidence: low` or `contested`, **restate it in the body** — downstream agents may skip frontmatter:

```markdown
> **Confidence: contested** — sources disagree on whether this initiative is funded for FY26. See "Disagreement" below.
```

For `contested`, include a "Disagreement" section that names the sources on each side. Cross-link to the open question in [`../../maintenance/contradictions.md`](../../maintenance/contradictions.md).

---

## Don't

- **Don't paraphrase a quote and cite it.** If you're using exact words, use a blockquote and cite. If you're paraphrasing, paraphrase clearly and cite.
- **Don't bury claims without a source.** If a claim has no `(source: ...)`, no `Inference:`, and no `Hypothesis:`, the reader can't tell where it came from. Fix it before merging.
- **Don't stack 5+ source citations on one fact.** If five sources say the same thing, cite the two strongest and put the rest in a "Sources consulted" appendix.
- **Don't use external URLs as citations.** Always cite a `wiki/sources/` page; that page links to the raw filename. URLs rot.
