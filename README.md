# <Organization> Wiki

A clonable, agent-readable wiki template for an organization's durable context layer.

The wiki turns raw source documents into structured, cited pages that downstream agents can query, compare, and build on. It follows the Karpathy LLM-wiki pattern, with additional safety rails for durable writes: deterministic lint, generated backlinks, no-write ingest routing, and approval gates for analysis capture and artifact promotion.

## Fresh Clone

Start with [`SETUP.md`](SETUP.md). An agent reads [`AGENTS.md`](AGENTS.md), checks [`wiki/domain.md`](wiki/domain.md), and if `status: unconfigured`, interviews you to configure:

- organization name and domain
- active entity types
- custom entity types
- `raw/` source taxonomy
- example questions the wiki should answer

## How To Use It

Common commands:

- `/ingest` — turn raw sources into durable wiki pages.
- `/capture` — record first-person context, usually decisions or lived experiences.
- `/promote` — route useful artifacts from chats, drafts, scripts, prompts, or work outputs into the right durable home, or decide not to save them.
- `/lint` — run deterministic wiki checks.

### Ask A Question

The analysis workflow answers from the wiki. The agent follows [`CONTEXT.md`](CONTEXT.md) into [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md), reads `wiki/index.md`, pulls only relevant pages, and answers with citations like `(source: [[source-slug]])`.

If the answer becomes substantial cross-page synthesis, the agent can save it as a citable analysis page.

### Preserve A Working Artifact

The promotion workflow is for useful material that is not simply a source and not already a clear analysis. Promotion means deciding the right durable home: an existing page, a new wiki page, a workflow note, a schema change, a fixture, a script, a decision, or an analysis. Direct decisions or lived context use `/capture`; `/promote` is for artifacts whose durable home is not obvious.

Agents can use the shared shortcut `python3 scripts/wiki_promote.py "<artifact>"` to start a promotion audit.

### Add A Source

Put the file under `raw/`, then ask the agent to ingest it. The shared ingest workflow lives in [`workflows/ingest/CONTEXT.md`](workflows/ingest/CONTEXT.md).

Images and screenshots can be ingested too. They route through the visual-evidence harness, and a same-stem `.ocr.txt` sidecar can provide the visible text the agent needs to summarize them safely.

### When Work Gets Saved

- **Analysis:** a saved answer to a wiki question: 3+ wiki pages, over 300 words, and a durable domain question.
- **Promotion:** a routing decision for a useful artifact whose correct home is not obvious.
- **Harness:** inspect no-write artifacts before riskier edits, non-standard ingest, or visual/social sources that need evidence.

### Maintain The Wiki

For linting, promotion, harness evaluation, and other upkeep, route through [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md).

Maintenance includes:

- linting
- artifact promotion
- harness evaluation
- capture via `/capture`: decisions and lived context
- sourcing-queue refresh

## Repo Structure

```text
<wiki-root>/
├── AGENTS.md       Canonical project operating map for agents.
├── CLAUDE.md       Thin Claude Code wrapper that imports AGENTS.md.
├── CONTEXT.md      Task router.
├── REFERENCES.md   Stable conventions and layer model.
├── SETUP.md        First-session configuration workflow.
├── raw/            Immutable source artifacts.
├── wiki/           Knowledge layer and entity pages.
├── workflows/      Vendor-neutral workflow prose.
├── scripts/        Deterministic helpers, workflow shortcuts, and no-write harness.
├── schemas/        JSON schemas for harness artifacts.
├── config/         Provider manifest.
├── tests/          Fixture-backed evals.
└── .claude/        Optional slash-command wrappers.
```

## Default Entity Types

| Type | Purpose |
|---|---|
| Sources | Summaries of raw documents |
| Products | What the organization offers |
| Features | Product capabilities |
| Personas | User and buyer types |
| Customers | Named customers or segments |
| Competitors | Competing vendors and positioning |
| Concepts | Domain ideas and frameworks |
| Initiatives | Strategic bets, launches, programs |
| Decisions | Choices, rationale, alternatives, revisit timing |
| Metrics | KPIs and North Stars |
| People | Roles, teams, stakeholders |
| Analyses | Synthesized outputs: comparisons, briefs, gap analyses |
| Style Rules | Writing and naming conventions for agent output |

The active subset lives in [`wiki/domain.md`](wiki/domain.md). The page format and source taxonomy live in [`wiki/SCHEMA.md`](wiki/SCHEMA.md).

## Conventions

- `AGENTS.md` is canonical; `CLAUDE.md` is a wrapper.
- `raw/` is immutable after a source is placed.
- Use kebab-case filenames with no date prefix.
- Use `[[page-name]]` links.
- Use typed `## Related pages` labels when clear: `Supports`, `Contradicts`, `Depends on`, `Derived from`, `Part of`, `Related`.
- Never hand-edit `## Referenced by`; run `scripts/rebuild_referenced_by.py`.
- Cite factual claims with `(source: [[source-page]])`.
- Mark interpretation with `Inference:` or `Hypothesis:`.

## Why A Wiki Instead Of Plain RAG

RAG retrieves raw chunks at query time. This wiki front-loads distillation at ingest time:

1. Sources become structured, cited entity pages.
2. Contradictions are explicit instead of hidden in retrieved context.
3. Relationships are typed and navigable.
4. Good analyses can become citable pages.
5. Agents load only the task-relevant workflow and pages.
6. Deterministic scripts catch structural drift.

See [`wiki/log.md`](wiki/log.md) for the append-only history of ingests, queries, maintenance, and configuration changes.
