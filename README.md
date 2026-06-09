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

### Ask A Question

Just ask. The agent follows [`CONTEXT.md`](CONTEXT.md) into [`workflows/research/CONTEXT.md`](workflows/research/CONTEXT.md), reads `wiki/index.md`, pulls only relevant pages, and answers with citations like `(source: [[source-slug]])`.

Substantial answers can be filed to `wiki/analyses/`, but only through `scripts/capture_gate.py`. If approval is required, the agent must show the exact approval block before writing.

### Promote A Reusable Artifact

Use promotion when a chat answer, draft, prompt, script idea, operating rule, or other working artifact should become durable wiki memory. It is the route for useful material that is not simply a raw source ingest and not already a clearly substantial research analysis.

Ask the agent to audit the artifact through [`workflows/maintenance/artifact-promotion.md`](workflows/maintenance/artifact-promotion.md). The workflow has two modes:

| Mode | Meaning |
|---|---|
| `Audit only` | Recommend one primary home without editing files |
| `Apply` | Make the chosen wiki, workflow, schema, script, or fixture update |

Before applying a promotion, the agent runs `scripts/capture_gate.py` with the proposed route. If approval is required, it must show the exact approval block before writing.

### Add A Source

Put the file under `raw/`, then ask the agent to ingest it. Claude users may use `/ingest`; other agents follow [`workflows/ingest/CONTEXT.md`](workflows/ingest/CONTEXT.md).

Every ordinary ingest starts with:

```bash
python3 scripts/wiki_route_policy.py <raw-source>
```

Routes:

| Route | Meaning |
|---|---|
| `direct_edit` | Proceed with normal ingest |
| `full_harness` | Run the no-write harness and inspect artifacts before durable edits |
| `blocked` | Stop until the route is fixed or explicitly re-scoped |

After durable edits, the agent rebuilds inbound links and runs deterministic Tier-1 lint:

```bash
python3 scripts/rebuild_referenced_by.py
python3 scripts/lint.py --tier1
```

### Maintain The Wiki

Claude users may use `/lint`; other agents route through [`workflows/maintenance/CONTEXT.md`](workflows/maintenance/CONTEXT.md).

Maintenance includes:

- linting
- artifact promotion
- harness evaluation
- decision capture
- observation or field-note capture
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
├── scripts/        Deterministic helpers and no-write harness.
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
