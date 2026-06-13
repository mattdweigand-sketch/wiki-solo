# <Organization> Wiki

A clonable, agent-readable wiki template for an organization's durable context layer. Grounded in sources. Structured for downstream agents. Designed to compound instead of re-deriving context from raw documents.

`AGENTS.md` is canonical and agent-agnostic. Codex, Cursor, Claude, ChatGPT, or a raw API harness should drive this wiki the same way: read `AGENTS.md`, check `wiki/domain.md` for setup status, route through `CONTEXT.md`, then follow the vendor-neutral prose in `workflows/`. Claude Code reaches the same guidance through the thin `CLAUDE.md` wrapper. Nothing about core operation depends on `.claude/` or `.codex/`.

Start by reading `wiki/domain.md` only far enough to check `status:`. If `status: unconfigured`, route to `SETUP.md` before doing wiki work. If `status: configured`, continue through `CONTEXT.md`.

---

## Directory Structure

- `AGENTS.md` - canonical operating map (this file). `CLAUDE.md` is a thin wrapper that imports it.
- `CONTEXT.md` - task router; read after this file to find the right workflow.
- `SETUP.md` - first-session configuration workflow for a fresh clone.
- `.github/workflows/` - GitHub Actions CI for deterministic wiki checks.
- `workflows/` - vendor-neutral prose workflows grouped into three workspaces, each with a `CONTEXT.md` entry point: `ingest/` (raw -> pages), `research/` (question -> answer), and `maintenance/` (lint, artifact-promotion, capture-decision, capture-experience, refresh-sourcing-queue, synthesize, export, plus the archived wiki-harness stub).
- `.claude/commands/` and `.codex/commands/` - optional slash-command wrappers for `wiki-ingest`, `wiki-capture`, `wiki-lint`, `wiki-promote`, `wiki-synthesize`, and `wiki-export`. Keep these wrappers thin; canonical behavior lives in `workflows/` and is routed through `CONTEXT.md`.
- `scripts/` - vendor-neutral deterministic tooling, self-contained. `capture_gate.py` is the deterministic approval preflight for analysis capture and artifact promotion; `rebuild_referenced_by.py` regenerates `## Referenced by` inbound-link sections; `lint.py --tier1` is the deterministic validation gate; `wiki_eval.py` runs the live guard suites.
- `scripts/fixtures/` - eval mini-wikis for live tooling: `wiki-rebuild` guards link-graph invariants and `wiki-lint` proves lint checks can fire.
- `scripts/lint-adjudications.json` - settled Tier-2 lint judgments with reasons and dates, so lint stops re-surfacing what has been adjudicated.
- `archive/wiki-harness/` - archived autonomy harness: route policy, no-write pipeline, schemas, provider manifest, fixtures, and original workflow. Do not run or extend it unless the project deliberately reopens the harness.
- `tmp/` - gitignored scratch space. Everything in it is disposable at all times.
- `deliverables/` - optional gitignored one-off outputs built from wiki content. Contents are not wiki content. Keep outputs inside clearly labeled kebab-case subfolders; do not leave loose files directly under `deliverables/`.
- `raw/` - source artifacts. Existing files are immutable, and new user-provided sources may be placed once during ingest before becoming immutable.
- `wiki/` - knowledge layer: `domain.md`, `index.md`, `overview.md`, `glossary.md`, `primer.md`, `log.md`, `SCHEMA.md`, `sourcing-queue.md`, `contradictions.md`, `design-notes.md`, `synthesis.md`, and entity folders.
- `wiki/<entity-type>/` - one folder per active entity type.

Default entity folders: `sources`, `products`, `features`, `personas`, `customers`, `competitors`, `concepts`, `initiatives`, `decisions`, `metrics`, `people`, `analyses`, `style`.

Create new entity types only during setup or after an explicit schema decision.

---

## Routing

Routing lives in `CONTEXT.md`, the source of truth for which workflow handles which task. Read it after this file, find the task, and open the workflow file it points to. Each workflow opens with its own Load / Skip list.

Routine command surface only: `/wiki-ingest`, `/wiki-capture`, `/wiki-lint`, `/wiki-promote`, `/wiki-synthesize`, and `/wiki-export`. These commands are shortcuts; canonical behavior stays in `CONTEXT.md`, `workflows/`, `scripts/`, and `wiki/SCHEMA.md`.

## Capture Approval Gate

Run `python3 scripts/capture_gate.py` before exactly two routes: filing a research answer as `wiki/analyses/`, and applying an artifact promotion. Every other route skips the gate, including ordinary source ingest, routine page updates, decision capture, experience capture, workflow updates, and setup updates, unless the work is part of an analysis-capture or artifact-promotion route.

If the script prints `APPROVAL REQUIRED`, show the full block and stop until the user approves the displayed durable action, primary destination, and allowed file scope. Re-run with `--approved` only after that approval.

The script owns the checkable approval boundary. The prose workflows own judgment about what to write, how to cite it, where to link it, and how to log it.

## Archived Autonomy Harness

The route preflight and no-write harness are archived under `archive/wiki-harness/`. Ordinary source ingest proceeds directly through the ingest workflow; no preflight script runs. If an ingest genuinely seems to need staged review before durable edits, that is a judgment call for the prose workflows and the user, not a script.

---

## Session Start

1. Read this file.
2. Read `wiki/domain.md` only far enough to check `status:`.
3. If `status: unconfigured`, open `SETUP.md` and follow it.
4. If `status: configured`, read `CONTEXT.md` to route the task.
5. Open only the routed workspace `CONTEXT.md` or task file.
6. Follow that workflow's Load / Skip list.
7. Load `REFERENCES.md`, `wiki/index.md`, `wiki/log.md`, and other wiki files only when the routed workflow asks for them.
8. If no task was provided, ask what to do after reading this file, `wiki/domain.md`, and `CONTEXT.md`.

---

## Naming Conventions

All filenames are kebab-case, lowercase, no extension prefix, no date prefix. Chronology lives in `wiki/log.md`.

Repo structure is linted. `scripts/lint.py --tier1` fails on unknown repo-root entries, unknown `wiki/` root entries, unknown top-level `raw/` buckets after setup, loose top-level `raw/` or `deliverables/` files, non-kebab-case `deliverables/` subfolders, and Finder `.DS_Store` metadata outside `.git`. Fix those as structural violations; do not work around them.

| Entity | Pattern | Example |
|---|---|---|
| Source page | kebab-case from source title | `q3-board-deck.md` |
| Person/team page | kebab-case role, team, or name | `enterprise-sales.md` |
| Decision page | kebab-case from decision topic | `pricing-packaging.md` |
| Product / feature / persona / customer / competitor / concept / initiative / metric / analysis / style | kebab-case from canonical term | `workflow-automation.md` |
| Workspace entry | `workflows/<workspace>/CONTEXT.md` | `workflows/ingest/CONTEXT.md` |
| Maintenance task file | kebab-case verb or noun | `workflows/maintenance/artifact-promotion.md` |

Predictable names let any agent find, organize, and reference files without reading the whole repo.

---

## Cross-Referencing

Use `[[filename-without-extension]]` for all internal links. Two link sections have different ownership:

- `## Related pages` - curated outbound links written by hand. Pick meaningful links. When the relationship is clear, prefix the link with a typed relationship label:
  - `Supports: [[page]]` - this page strengthens, evidences, or confirms the linked page
  - `Contradicts: [[page]]` - this page conflicts with or materially challenges the linked page
  - `Depends on: [[page]]` - this page requires the linked page to be understood or true
  - `Derived from: [[page]]` - this page was created from, generalized from, or synthesized out of the linked page
  - `Part of: [[page]]` - this page is a component of the linked larger system, project, or framework
  - `Related: [[page]]` - meaningful connection, but no stronger typed relationship fits
- `## Referenced by` - auto-generated inbound links. Never hand-edit this section. It is rebuilt from the `[[ ]]` graph by `scripts/rebuild_referenced_by.py`.

The script is an optional convenience: if it is never run, `## Related pages` still works and the wiki stays operable. It just means inbound links will not auto-refresh.

## Terminology

New terms go in `wiki/glossary.md`. Conflicts get flagged explicitly. Always use the canonical glossary term once it exists.

## Hard Rules

- Do not edit existing files in `raw/`.
- Flag contradictions before updating; never silently overwrite contested claims.
- Prefer updating existing pages over creating new ones.
- Write for AI agents first: structured, dense, cited.
- Keep tool-specific wrappers thin; canonical behavior belongs in `AGENTS.md`, `CONTEXT.md`, `REFERENCES.md`, `workflows/`, `scripts/`, and `wiki/SCHEMA.md`.
