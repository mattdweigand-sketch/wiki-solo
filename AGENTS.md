# <Organization> Wiki

A clonable, agent-readable wiki template for an organization's durable context layer. Grounded in sources. Structured for downstream agents. Designed to compound instead of re-deriving context from raw documents.

`AGENTS.md` is canonical and agent-agnostic. Codex, Cursor, Claude, ChatGPT, or a raw API harness should drive this wiki the same way: read `AGENTS.md`, check `wiki/domain.md`, route through `CONTEXT.md`, then follow the vendor-neutral prose in `workflows/`. Claude Code reaches the same guidance through the thin `CLAUDE.md` wrapper. Nothing about core operation depends on `.claude/` or `.codex/`.

Start by reading `wiki/domain.md`. If `status: unconfigured`, route to `SETUP.md` before doing wiki work. If `status: configured`, continue through `CONTEXT.md`.

---

## Directory Structure

- `AGENTS.md` — canonical operating map (this file). `CLAUDE.md` is a thin wrapper that imports it.
- `CONTEXT.md` — task router; read after this file to find the right workflow.
- `SETUP.md` — first-session configuration workflow for a fresh clone.
- `workflows/` — vendor-neutral prose workflows grouped into three workflow areas: `ingest/`, `research/`, and `maintenance/`.
- `.claude/commands/` and `.codex/commands/` — optional slash-command wrappers for the routine command surface: `/ingest`, `/capture`, `/lint`, and `/promote`.
- `scripts/` — vendor-neutral helper scripts and workflow shortcuts. `wiki_promote.py` starts a no-write promotion audit; `capture_gate.py` guards analysis capture and artifact promotion apply routes; `wiki_route_policy.py` is the no-write route preflight before ingest edits; `wiki_pipeline.py` and related `wiki_*` scripts run the no-write harness under `tmp/wiki-runs/`; `rebuild_referenced_by.py` regenerates inbound links; `lint.py --tier1` is the deterministic validation gate.
- `config/` — harness/provider manifests.
- `schemas/` — JSON schemas for harness packets, provider artifacts, apply plans, and manifests.
- `tests/fixtures/` — golden and negative fixtures for ingest, policy, route, run, semantic, provider, pipeline, apply-plan, and Tier-1 behavior.
- `raw/` — source artifacts; existing files are immutable.
- `wiki/` — knowledge layer: `domain.md`, `index.md`, `overview.md`, `glossary.md`, `primer.md`, `log.md`, `SCHEMA.md`, and entity folders.

Default entity folders: `sources`, `products`, `features`, `personas`, `customers`, `competitors`, `concepts`, `initiatives`, `decisions`, `metrics`, `people`, `analyses`, `style`.

Create new entity types only during setup or after an explicit schema decision.

---

## Routing

Routing lives in `CONTEXT.md`, the source of truth for which workflow handles which task. Read it after this file, find the task, and open the workflow file it points to. Each workflow opens with its own Load / Skip list.

Routine command surface only: `/ingest`, `/capture`, `/lint`, and `/promote`. `/ingest` turns raw sources into durable wiki pages. `/capture` records first-person context, usually decisions or lived experiences. `/promote` routes useful artifacts from chats, drafts, scripts, prompts, or work outputs into the right durable home, or decides not to save them. `/lint` runs deterministic wiki checks. These commands are shortcuts; canonical behavior stays in `CONTEXT.md`, `workflows/`, `scripts/`, and `wiki/SCHEMA.md`.

## Capture Approval Gate

Use `scripts/capture_gate.py` with the workflow-specific arguments only before filing a research answer as `wiki/analyses/` or applying an artifact promotion. Ordinary source ingest does not require this approval gate; neither do routine page updates, decision capture, observation capture, workflow updates, or project updates unless they are part of an analysis-capture or artifact-promotion route.

If the script prints `APPROVAL REQUIRED`, show that exact block and stop until the user approves the exact mode, primary home, and touched files. Re-run with `--approved` only after that approval.

The script owns the checkable approval boundary. The prose workflows own judgment about what to write, how to cite it, where to link it, and how to log it.

## Harness Route Policy

Before an ordinary source ingest writes durable wiki files, run:

```bash
python3 scripts/wiki_route_policy.py <raw-source>
```

This writes no files. It returns `direct_edit`, `full_harness`, or `blocked`. `direct_edit` continues through the normal ingest workflow. `full_harness` runs the no-write harness for review before durable edits. `blocked` stops until the route is fixed or explicitly re-scoped.

---

## Session Start

1. Read this file.
2. Read `wiki/domain.md`; if unconfigured, route to `SETUP.md`.
3. Read `CONTEXT.md` to route the task.
4. Read `REFERENCES.md`.
5. Read `wiki/index.md`.
6. Read the last 5 entries in `wiki/log.md`.
7. Ask what to do, unless the user already gave a clear task.

---

## Naming Conventions

All filenames are kebab-case, lowercase, no extension prefix, no date prefix. Chronology lives in `wiki/log.md`.

| Entity | Pattern | Example |
|---|---|---|
| Source page | kebab-case from source title | `q3-board-deck.md` |
| Person/team page | kebab-case role, team, or name | `enterprise-sales.md` |
| Decision page | kebab-case from decision topic | `pricing-packaging.md` |
| Product / feature / persona / customer / competitor / concept / initiative / metric / analysis / style | kebab-case from canonical term | `workflow-automation.md` |
| Workflow entry | `workflows/<workspace>/CONTEXT.md` | `workflows/ingest/CONTEXT.md` |
| Maintenance task file | kebab-case verb or noun | `workflows/maintenance/artifact-promotion.md` |

Predictable names let any agent find, organize, and reference files without reading the whole repo.

---

## Cross-Referencing

Use `[[filename-without-extension]]` for all internal links. Two link sections have different ownership:

- `## Related pages` — curated outbound links written by hand. Pick meaningful links. When the relationship is clear, prefix the link with a typed relationship label:
  - `Supports: [[page]]` — this page strengthens, evidences, or confirms the linked page
  - `Contradicts: [[page]]` — this page conflicts with or materially challenges the linked page
  - `Depends on: [[page]]` — this page requires the linked page to be understood or true
  - `Derived from: [[page]]` — this page was created from, generalized from, or synthesized out of the linked page
  - `Part of: [[page]]` — this page is a component of the linked larger system, project, or framework
  - `Related: [[page]]` — meaningful connection, but no stronger typed relationship fits
- `## Referenced by` — auto-generated inbound links. Never hand-edit this section. It is rebuilt from the `[[ ]]` graph by `scripts/rebuild_referenced_by.py`.

## Terminology

New terms go in `wiki/glossary.md`. Conflicts get flagged explicitly. Always use the canonical glossary term once it exists.

## Hard Rules

- Do not edit existing files in `raw/`.
- Flag contradictions before updating; never silently overwrite contested claims.
- Prefer updating existing pages over creating new ones.
- Write for AI agents first: structured, dense, cited.
- Keep tool-specific wrappers thin; canonical behavior belongs in `AGENTS.md`, `CONTEXT.md`, `REFERENCES.md`, `workflows/`, `scripts/`, and `wiki/SCHEMA.md`.
