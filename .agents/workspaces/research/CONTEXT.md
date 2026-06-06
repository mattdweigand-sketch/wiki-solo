# Research

## What This Workspace Is

Where the wiki gets *consumed*. The user asks a question — about a customer, competitor, decision, market — and the agent reads the wiki, synthesizes an answer, and (optionally) files it back as an analysis page so future agents can cite it.

**Upstream:** [`../../../wiki/`](../../../wiki/) — the knowledge layer.
**Downstream:** Optionally a new page in [`../../../wiki/analyses/`](../../../wiki/analyses/). Always an entry in [`../../../wiki/log.md`](../../../wiki/log.md).

---

## What to Load

| Task | Always Load | Add for the task | Skip |
|---|---|---|---|
| Answer any question | [`../../../wiki/index.md`](../../../wiki/index.md), [`../../../wiki/primer.md`](../../../wiki/primer.md) | The 3–8 entity pages most relevant to the question | The full wiki. Pull pages on demand from index/primer. |
| Compare entities (products, competitors, customers) | Same as above | Each entity's page; relevant analyses if any exist | Pages outside the comparison set |
| Build a brief or memo | Same as above | [`docs/analysis-template.md`](docs/analysis-template.md), entity pages, recent `log.md` entries | `ingest/docs/`, `maintenance/docs/` |
| Quick factual lookup | [`../../../wiki/index.md`](../../../wiki/index.md) only | The single page that answers it | primer, glossary unless the term is ambiguous |

[`docs/query-protocol.md`](docs/query-protocol.md) — read once to internalize the read → synthesize → cite → ask flow.
[`docs/analysis-template.md`](docs/analysis-template.md) — load when filing an answer as a wiki page.

---

## Folder Structure

```
research/
├── CONTEXT.md                ← You are here
└── docs/
    ├── query-protocol.md     ← How to answer a question against the wiki
    └── analysis-template.md  ← Structure for filing an answer as wiki/analyses/
```

No `content/` or `output/` folder here. Filed analyses live in [`../../../wiki/analyses/`](../../../wiki/analyses/) so they're first-class citable entities, not orphaned in a research silo.

---

## The Process

A research session flows like a conversation, not a pipeline:

1. **Orient.** Read [`../../../wiki/index.md`](../../../wiki/index.md). If the question is fuzzy, also read [`../../../wiki/primer.md`](../../../wiki/primer.md) — it routes by question type.
2. **Pull pages.** Identify and read the 3–8 wiki pages most relevant. Don't load the whole wiki.
3. **Synthesize.** Answer with citations. Use `[[page-name]]` for internal references. Mark inferences with `Inference:` and speculation with `Hypothesis:`. (See [`../ingest/docs/citation-rules.md`](../ingest/docs/citation-rules.md) — the same rules apply.)
4. **Auto-file if meaningful.** If the answer synthesized **3+ wiki pages** and is **>300 words**, file it to `../../../wiki/analyses/<slug>.md` using [`docs/analysis-template.md`](docs/analysis-template.md). **Don't ask first.** Notify in one line: *"Filed as `analyses/<slug>.md` — delete if not useful."* Pick a slug that names the *question* (e.g., `<product>-vs-<competitor>-<topic>-positioning.md`, not `<product>-wins-on-<topic>.md`). If the answer doesn't meet both criteria, skip filing.
5. **Log.** Append to [`../../../wiki/log.md`](../../../wiki/log.md):
   ```
   ## [YYYY-MM-DD] query | <question summary>
   Pages consulted: ...
   Output filed: yes/no — <filename if yes>
   ```
   Then run `python3 .agents/scripts/rebuild_referenced_by.py` from the repo root if a file was created.

---

## Skills & Tools

| Skill / Tool | When | Purpose |
|---|---|---|
| Web Search | Question depends on currency (e.g., "is this still true?", "did the M&A close?") | Verify time-sensitive claims; the wiki may be stale on external facts |
| Web Search | Question is about a public competitor's recent move | Confirm with primary sources before citing |

External research goes into the answer — but **anything that becomes a durable claim needs to flow through ingest**, not get embedded directly into the wiki by the research workspace. Research produces analyses (synthesis); ingest produces sources (raw → page).

---

## Output Formats

The default is a markdown answer. When the user asks (or the question warrants it), shift to:

- **Comparison table** — side-by-side products, competitors, or personas
- **Brief** — structured 1-page summary for a specific audience (exec, sales, eng)
- **Gap analysis** — what we know vs. what we don't (and what would close the gap)
- **Decision memo** — framing a decision with options and trade-offs
- **Persona card** — structured persona summary for GTM use
- **Glossary entry** — ready to append to [`../../../wiki/glossary.md`](../../../wiki/glossary.md)

If the format isn't obvious, ask before producing.

---

## What NOT to Do

- **Don't read the full wiki to answer one question.** That's what [`../../../wiki/index.md`](../../../wiki/index.md) and [`../../../wiki/primer.md`](../../../wiki/primer.md) exist to prevent.
- **Don't bypass the wiki and re-derive from `raw/`.** If a wiki page is wrong or thin, that's an ingest job — flag it for the user, don't silently work around it.
- **Don't write to entity folders.** Research only writes to [`../../../wiki/analyses/`](../../../wiki/analyses/) (filed answers) and [`../../../wiki/log.md`](../../../wiki/log.md). Updating an entity page is an ingest task.
- **Don't load `ingest/workflows/` or `maintenance/docs/`.** Different jobs.
