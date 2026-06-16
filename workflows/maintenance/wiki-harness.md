# Archived Wiki Harness

The wiki autonomy harness is archived under `archive/wiki-harness/`.

Use this task only when the user asks about the archived harness, wants to inspect its old design, or explicitly decides to reopen it. Ordinary ingest does not run `scripts/wiki_route_policy.py`, `scripts/wiki_pipeline.py`, provider readiness checks, or no-write harness evals.

## Load / Skip

- **Load:** `archive/wiki-harness/README.md` and `archive/wiki-harness/wiki-harness-workflow.md`.
- **Skip:** archived scripts, schemas, and fixtures unless the user explicitly asks to inspect or revive them.

## Current Boundary

The live wiki keeps the parts that proved useful in normal work:

- `scripts/capture_gate.py` for approval on analysis capture and artifact promotion apply routes.
- `scripts/synthesis_gate.py` for approval before synthesis promotion.
- `scripts/rebuild_referenced_by.py` for generated inbound links.
- `/wiki-eval` and `scripts/wiki_eval.py`, plus `scripts/lint.py`, the ledger validators, `scripts/export_wiki.py`, and `scripts/sync_codex_skills.py`, for deterministic maintenance checks.

If staged review seems warranted for a specific ingest, raise it as a workflow judgment call instead of running the archived harness by default.
