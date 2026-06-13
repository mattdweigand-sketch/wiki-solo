# Archived Wiki Autonomy Harness

This directory preserves the old no-write autonomy harness: route policy, pipeline scripts, provider manifest, schemas, fixtures, and the original workflow prose.

The harness is archived. It is not part of ordinary ingest, research, promotion, capture, lint, synthesis, or export work. Live wiki operation is routed through `AGENTS.md`, `CONTEXT.md`, `workflows/`, and the deterministic scripts that remain under `scripts/`.

## Contents

- `config/` - archived provider manifest.
- `schemas/` - archived JSON schemas for dry-run, semantic, writer, judge, provider, pipeline, and apply-plan artifacts.
- `fixtures/` - archived golden and negative fixtures for the old harness suites.
- `scripts/` - archived `wiki_*` harness scripts.
- `wiki-harness-workflow.md` - the original operational harness workflow.
- `template-modernization-spec.md` - historical spec for the earlier harness-centered modernization pass.
- `legacy-ingest/` - the old nested ingest pipeline notes, retained for context only.

## Reopen Condition

Reopen only after an explicit project decision that the wiki needs staged no-write review again. If reopened, restore the needed scripts and fixtures deliberately, update `AGENTS.md`, `CONTEXT.md`, `REFERENCES.md`, and `workflows/maintenance/wiki-harness.md`, and add current eval coverage before relying on the harness.
