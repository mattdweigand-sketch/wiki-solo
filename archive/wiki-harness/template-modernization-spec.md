# Wiki-Solo Template Modernization Spec

## Purpose

Modernize `wiki-solo` from an early agent-readable wiki sketch into the generalized, clonable version of the newer wiki operating architecture.

The refactor ports the control layer that makes the current wiki safer and more maintainable while keeping `wiki-solo` organization-oriented rather than personal-life-specific.

## Problem

The sketch repo had the right core idea: immutable raw sources, a structured wiki, agent-readable routing, generated backlinks, and lint. It lagged the newer architecture in four important ways:

1. Research could auto-file substantial analyses without an approval gate.
2. Ingest wrote durable wiki files without a no-write route preflight.
3. Maintenance workflows were bundled into one broad file instead of routeable task files.
4. The repo used older `workspaces/` naming and lacked schemas, fixtures, provider manifests, and harness scripts.

Without these upgrades, the template teaches a weaker pattern than the live architecture.

## Goals

- Keep `wiki-solo` a public, clonable organization wiki template.
- Move canonical workflow prose to `workflows/`.
- Add deterministic route policy before durable ingest writes.
- Add `capture_gate.py` for analysis capture and artifact promotion.
- Add the no-write harness scripts, schemas, provider manifest, and fixtures.
- Preserve the organization/product/company taxonomy from `wiki-solo`.
- Avoid importing personal wiki entity types or personal-life language.

## Non-Goals

- Do not copy private content or personal wiki pages.
- Do not change the license or repository identity.
- Do not require Claude-specific features for core operation.
- Do not make the full harness mandatory for every ingest.
- Do not add a new entity type just to store temporary outputs.

## Architecture

### Control Flow

```text
AGENTS.md -> wiki/domain.md -> CONTEXT.md -> workflows/<workspace>/CONTEXT.md -> task workflow
```

### Ingest Safety

```text
raw source -> wiki_route_policy.py -> direct_edit | full_harness | blocked
```

- `direct_edit`: continue through ordinary ingest.
- `full_harness`: run `wiki_pipeline.py`, inspect artifacts, then decide whether to proceed.
- `blocked`: stop until the route is fixed or explicitly re-scoped.

### Analysis And Promotion Safety

```text
research answer or reusable artifact -> capture_gate.py -> chat-only | ingest | analysis-capture | promotion-audit | capture-decision | capture-experience | workflow-update
```

Approval is required only for `analysis-capture` and `promotion-audit`.

### Harness Boundary

The harness is no-write by default. It may create review artifacts under `tmp/wiki-runs/<run-id>/`, but it must not write durable `wiki/` files unless a future apply workflow explicitly crosses that boundary with user approval.

## Files To Keep Generalized

| Area | Rule |
|---|---|
| Root docs | Use organization/domain language, not personal-life language |
| Schema | Keep product, feature, persona, customer, competitor, initiative, metric taxonomy |
| Setup | Keep the first-session interview and configurable entity types |
| Scripts | Keep stdlib-only deterministic helpers |
| Workflows | Keep vendor-neutral prose; `.claude/` and `.codex/` remain optional wrappers for `/ingest`, `/capture`, `/lint`, and `/promote` |
| Capture gate | Prefer `--domain-context`; keep backward-compatible hidden `--life-context` only for compatibility |

## Acceptance Criteria

- `AGENTS.md`, `CONTEXT.md`, `REFERENCES.md`, and `README.md` describe the same architecture.
- `workflows/` exists and root docs no longer route to `workspaces/`.
- `wiki/SCHEMA.md` is the stable schema reference.
- Ingest workflow requires `scripts/wiki_route_policy.py <raw-source>` before durable wiki edits.
- Research workflow uses `scripts/capture_gate.py` before filing analyses.
- Artifact promotion has audit-only and apply modes.
- `scripts/rebuild_referenced_by.py` and `scripts/lint.py --tier1` pass.
- Harness evals can be run from `scripts/wiki_eval.py`.
- Public template prose does not refer to Matt or the personal wiki.

## Verification

Run from repo root:

```bash
python3 scripts/rebuild_referenced_by.py
python3 scripts/lint.py --tier1
python3 scripts/wiki_eval.py --suite route
python3 scripts/wiki_eval.py --suite policy
python3 scripts/wiki_eval.py --suite pipeline
git diff --check
```

If the schema or fixtures are changed, also run:

```bash
python3 scripts/wiki_eval.py --suite semantic
python3 scripts/wiki_eval.py --suite provider
python3 scripts/wiki_eval.py --suite apply
```

## Migration Notes

- The old `workspaces/` folder was renamed to `workflows/`.
- The old `workflows/ingest/workflows/` nested pipeline is retained for backwards context but the main ingest entry is now `workflows/ingest/CONTEXT.md`.
- `wiki/SCHEMA.md` mirrors the organization template schema so agents have a stable wiki-level schema path.
- `.claude/commands/` and `.codex/commands/` should remain thin wrappers over `workflows/`; do not put canonical rules there. Keep only `/ingest`, `/capture`, `/lint`, and `/promote` as command wrappers unless repeated real usage proves another workflow deserves a shortcut.
