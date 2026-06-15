# <Organization> Wiki

A clonable, agent-readable wiki template for an organization's durable context layer. Grounded in sources. Structured for downstream agents. Designed to compound instead of re-deriving context from raw documents.

`AGENTS.md` is canonical and agent-agnostic. Codex, Cursor, Claude, ChatGPT, or a raw API harness should drive this wiki the same way: read `AGENTS.md`, check `wiki/domain.md` for setup status, route through `CONTEXT.md`, then follow the vendor-neutral prose in `workflows/`. Claude Code reaches the same guidance through the thin `CLAUDE.md` wrapper and tracked `.claude/commands/`. Codex reaches the same guidance through tracked `.codex/commands/` mirrors and tracked repo-local `.codex/skills/` wrappers. Nothing about core operation depends on `.claude/` or `.codex/`.

Start by reading `wiki/domain.md` only far enough to check `status:`. If `status: unconfigured`, route to `SETUP.md` before doing wiki work. If `status: configured`, continue through `CONTEXT.md`.

---

## Directory Structure

- `AGENTS.md` - canonical operating map (this file). `CLAUDE.md` is a thin wrapper that imports it.
- `CONTEXT.md` - task router; read after this file to find the right workflow.
- `SETUP.md` - first-session configuration workflow for a fresh clone.
- `.github/workflows/` - GitHub Actions CI for deterministic wiki checks.
- `workflows/` - vendor-neutral prose workflows grouped into three workspaces, each with a `CONTEXT.md` entry point: `ingest/` (raw -> pages), `research/` (question -> answer), and `maintenance/` (lint, artifact-promotion, capture-decision, capture-experience, refresh-sourcing-queue, synthesize, export, plus the archived wiki-harness stub).
- `.claude/commands/` - tracked Claude Code slash-command wrappers for `wiki-ingest`, `wiki-capture`, `wiki-lint`, `wiki-promote`, `wiki-synthesize`, and `wiki-export`. Keep these wrappers thin; canonical behavior lives in `workflows/` and is routed through `CONTEXT.md`.
- `.codex/commands/` - tracked Codex command mirrors for the same six workflows. Current Codex shortcut discovery uses skills rather than this repo-local command folder, but these mirrors document the command shape.
- `.codex/skills/` - tracked repo-local Codex skill wrappers for the six active wiki shortcuts. Current Codex discovers this directory while working in the repo; do not also install identical `wiki-*` wrappers under `~/.codex/skills/`, or slash-command autocomplete may show duplicate repo and Personal entries. Use `python3 scripts/sync_codex_skills.py --check` to detect duplicate global wiki skills and `python3 scripts/sync_codex_skills.py --remove-global` to remove them.
- `scripts/` - vendor-neutral deterministic tooling, self-contained. `capture_gate.py` is the deterministic approval preflight for analysis capture and artifact promotion; `capture-runs.jsonl` is the structured approval ledger written only by approved capture-gate reruns; `validate_capture_runs.py` checks that ledger's schema, hashes, and approval scope; `synthesis_gate.py` is the deterministic approval preflight before synthesis drafts are promoted, ledgered in `wiki/synthesis.md`, or have draft status/confidence flipped; `synthesis-runs.jsonl` is the structured approval ledger written only by approved synthesis-gate reruns; `validate_synthesis_runs.py` checks that ledger's schema, hashes, and approval scope; `export_wiki.py` builds and verifies complete corpus export zips; `rebuild_referenced_by.py` regenerates `## Referenced by` inbound-link sections; `lint.py --tier1` is the deterministic validation gate; `wiki_eval.py` runs the live guard suites, including both ledger validations; `sync_codex_skills.py` prevents duplicate global `wiki-*` Codex skill installs now that repo-local `.codex/skills/` is discovered directly.
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

Routine command surface only: `/wiki-ingest`, `/wiki-capture`, `/wiki-lint`, `/wiki-promote`, `/wiki-synthesize`, and `/wiki-export`. These commands are shortcuts; canonical behavior stays in `CONTEXT.md`, `workflows/`, `scripts/`, and `wiki/SCHEMA.md`. Claude Code reads `.claude/commands/` in the repo. Codex reads tracked repo-local skills under `.codex/skills/`; duplicate global `wiki-*` skills are local runtime noise, not source of truth.

## Capture Approval Gate

Run `python3 scripts/capture_gate.py` before exactly two routes: filing a research answer as `wiki/analyses/`, and applying an artifact promotion. Every other route skips the gate, including ordinary source ingest, routine page updates, decision capture, experience capture, workflow updates, and setup updates, unless the work is part of an analysis-capture or artifact-promotion route.

If the script prints `APPROVAL REQUIRED`, show the full block and stop until the user approves the displayed durable action, primary destination, and allowed file scope. Plain-language approval such as "approve" or "yes" is enough when it clearly approves the displayed action, destination, and file scope. Re-run with `--approved` only after that approval.

The script owns the checkable approval boundary. The prose workflows own judgment about what to write, how to cite it, where to link it, and how to log it.

The approved rerun writes or confirms the idempotent structured approval record in `scripts/capture-runs.jsonl`. The non-approved gate call is display-only: it must not update `wiki/analyses/`, promoted pages, `scripts/capture-runs.jsonl`, or `wiki/log.md`.

## Synthesis Approval Gate

Run `python3 scripts/synthesis_gate.py` before promoting synthesis output: updating `wiki/synthesis.md`, flipping draft confidence/status because the user reviewed a synthesis draft, or logging a synthesis promotion. The gate must display the draft being approved, primary destination, and full editable file scope. If it prints `APPROVAL REQUIRED`, show the approval request and stop. Re-run with `--approved` only after the user clearly approves the displayed synthesis draft and file scope.

The approved rerun writes or confirms the idempotent structured approval record in `scripts/synthesis-runs.jsonl`. The non-approved gate call is display-only: it must not update `wiki/synthesis.md`, `scripts/synthesis-runs.jsonl`, draft confidence/status, or `wiki/log.md`.

The synthesis gate is separate from `capture_gate.py` because synthesis drafts are routine maintenance until they become approved durable conclusions.

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
