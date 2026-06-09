# Wiki References

Stable reference material for the wiki maintainer. This is not the task router; load it for orientation, schema conventions, and cross-reference rules.

---

## Role

The wiki maintainer:

- Ingests sources and distills them into structured, cited wiki pages.
- Keeps pages consistent, cross-referenced, and current.
- Answers questions by reading the wiki, not by re-deriving from `raw/`.
- Files substantial answers back into `wiki/analyses/` when the research workflow criteria are met and the capture gate allows it.
- Audits reusable artifacts for promotion when they should compound elsewhere.
- Periodically lints for contradictions, stale content, and orphan pages.

Own everything in `wiki/`. Never edit existing files in `raw/`.

---

## Cross-Referencing Rules

Use `[[filename-without-extension]]` for internal links.

In `## Related pages`, use typed relationship labels when the relationship is clear:

| Label | Meaning |
|---|---|
| `Supports` | This page strengthens, evidences, or confirms the linked page |
| `Contradicts` | This page conflicts with or materially challenges the linked page |
| `Depends on` | This page requires the linked page to be understood or true |
| `Derived from` | This page was created from, generalized from, or synthesized out of the linked page |
| `Part of` | This page is a component of the linked larger system, project, or framework |
| `Related` | Meaningful connection, but no stronger typed relationship fits |

Format each item as `- Label: [[page]]`. Do not invent new labels casually; if a new relationship type is repeatedly needed, add it here, `AGENTS.md`, and `wiki/SCHEMA.md`.

When stating a fact, append `(source: [[source-page]])`. When stating an opinion or inference, prefix with `Inference:` or `Hypothesis:`.

---

## Key Reference Files

| File | Purpose |
|---|---|
| `wiki/domain.md` | Organization name, scope, active entity types, raw taxonomy, setup status |
| `wiki/SCHEMA.md` | Entity types, frontmatter spec, source-type templates |
| `wiki/glossary.md` | Canonical terminology |
| `wiki/overview.md` | High-level synthesis of the configured organization or domain |
| `wiki/index.md` | Master catalog of pages |
| `workflows/maintenance/lint.md` | Judgment lint workflow |
| `workflows/maintenance/artifact-promotion.md` | Promotion audit and apply workflow |

## Support Files

| File or folder | Purpose |
|---|---|
| `raw/README.md` | Source-artifact handling note |
| `config/wiki-provider-manifest.json` | Harness provider slots and supported providers |
| `schemas/` | JSON schemas for dry-run, semantic, writer, judge, provider, pipeline, and apply-plan artifacts |
| `tests/fixtures/` | Golden and negative fixture data for deterministic harness evals |

---

## Capture Boundary

The wiki separates deterministic approval from prose judgment:

- `scripts/capture_gate.py` guards analysis capture and artifact promotion approval.
- Workflow prose decides quality: what belongs in a page, which evidence matters, how links should be written, and how contradictions should be handled.
- Ordinary source ingest, decision capture, observation capture, and workflow updates do not require the approval gate unless they are part of analysis capture or artifact promotion.

## Harness Boundary

The wiki autonomy harness is a no-write review layer around risky or review-triggered work. It does not replace the ingest, research, promotion, or lint workflows.

- `scripts/wiki_route_policy.py <raw-source>` is the lightweight preflight before durable ingest edits.
- `direct_edit` continues through normal ingest.
- `full_harness` runs `scripts/wiki_pipeline.py` and inspects artifacts under `tmp/wiki-runs/<run-id>/` before durable edits.
- `blocked` stops until the route is fixed or explicitly re-scoped.
- Local, cloud, and stub are provider choices inside the same harness slots, not separate workflows.
- Harness scripts must keep proposed writes in `tmp/wiki-runs/` unless a later durable apply workflow exists and is explicitly approved.

---

## Layer Architecture (L0-L4)

Every file sits at one of five layers, defined by when it loads relative to a task.

| Layer | When loaded | Files |
|---|---|---|
| L0 | Always: orientation and routing | `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, `wiki/domain.md` |
| L1 | Session start: completes orientation | `REFERENCES.md`, `wiki/index.md`, `wiki/primer.md` |
| L2 | Per task: workflow entry and task definition | `workflows/<workspace>/CONTEXT.md`, `workflows/maintenance/*.md` |
| L3 | Per task: stable reference, loaded on demand | `wiki/SCHEMA.md`, `wiki/glossary.md`, `wiki/overview.md`, `workflows/*/docs/*` |
| L4 | During work: content read or written | `wiki/log.md`, `wiki/<entity>/*.md`, `raw/*` |

Loading principle: load L0 and L1, then the L2 workflow for the task, then pull L3 references only when the workflow calls for them. L4 is read or written as the work proceeds.
