# Wiki References

Stable reference material for the wiki maintainer. Consult when authoring pages, checking cross-reference conventions, or when a routed workflow calls for it. Not a routing file and not loaded on every session.

---

## Role

The wiki maintainer:

- Ingests sources and extracts knowledge into structured wiki pages.
- Keeps pages consistent, cross-referenced, and up to date.
- Answers queries by reading the wiki, not by re-deriving from raw sources.
- Files substantial answers back into the wiki when the research workflow criteria are met, using `scripts/capture_gate.py` before analysis capture and artifact promotion.
- Audits reusable artifacts for promotion when they should compound elsewhere.
- Periodically lints for contradictions, stale content, and orphan pages.

Own everything in `wiki/`. `raw/` holds source artifacts: do not edit existing raw files. During ingest, if the user provides a new source outside the proper location, place it once under the correct `raw/` subfolder with a kebab-case filename, then treat it as immutable.

---

## Operating Model

This repo is a durable context system, not a document dump. Raw sources are preserved, then distilled into structured pages that downstream agents can reuse without re-reading every source.

The system has four layers of responsibility:

| Layer | Owns |
|---|---|
| Sources | `raw/` stores source artifacts. Existing raw files are immutable. |
| Knowledge | `wiki/` stores maintained, cited pages and wiki-wide records. |
| Workflow | `AGENTS.md`, `CONTEXT.md`, and `workflows/` route tasks and define what to load, skip, edit, and verify. |
| Mechanisms | `scripts/` performs deterministic checks, backlink rebuilds, approval-ledger validation, exports, and wrapper validation. |

The workflow map is:

| Workflow | Route | Owns |
|---|---|---|
| Setup | `SETUP.md` | First-session configuration: context owner, domain, active entity types, raw taxonomy, and example questions. |
| Ingest | `workflows/ingest/CONTEXT.md` | Raw source handling, `wiki/sources/` summaries, affected entity-page updates, index rows, backlinks, Tier-1 lint, and ingest log entries. |
| Research | `workflows/research/CONTEXT.md` | Wiki-grounded answers, selective page loading, optional analysis capture, and promotion-candidate audits. |
| Capture decision | `workflows/maintenance/capture-decision.md` | Decision pages with rationale, alternatives, affected entities, cross-links, verification, and log entries. |
| Capture experience | `workflows/maintenance/capture-experience.md` | Field notes or lived context stored in the most relevant entity folder with lessons and links. |
| Artifact promotion | `workflows/maintenance/artifact-promotion.md` | Routing useful external or conversational artifacts to source, concept, analysis, decision, initiative, style, workflow, script, existing page update, or discard. |
| Lint | `workflows/maintenance/lint.md` | Deterministic structure checks, Tier-2 quality candidates, judgment checks, and citation evidence review. |
| Synthesis | `workflows/maintenance/synthesize.md` | Drafting and approving corpus-level distillations: overview refreshes, gap resolutions, cluster analyses, and primer updates. |
| Track knowledge gaps | `workflows/maintenance/refresh-sourcing-queue.md` | Maintaining `wiki/sourcing-queue.md`, the list of missing sources or open evidence gaps the wiki should fill next. |
| Export | `workflows/maintenance/export.md` | Local corpus backup, including gitignored raw sources, without reading wiki content or uploading anywhere. |

The main control mechanisms are:

| Mechanism | Purpose |
|---|---|
| Route-first loading | Start with `AGENTS.md`, check `wiki/domain.md`, route through `CONTEXT.md`, then open only the selected workflow and its Load / Skip list. |
| Schema and citations | `wiki/SCHEMA.md` defines page types, frontmatter, source types, confidence values, and citation rules. Specific facts cite `wiki/sources/` pages. |
| Link graph | Authors maintain `## Related pages`; `scripts/rebuild_referenced_by.py` regenerates `## Referenced by`. |
| Deterministic lint | `scripts/lint.py --tier1` catches structural failures. Full lint also surfaces Tier-2 candidates for human or agent judgment. |
| Live evals | `scripts/wiki_eval.py` runs fixture-backed checks for lint, backlinks, gates, ledgers, export, and wrapper sync. |
| Capture gate | `scripts/capture_gate.py` guards analysis capture and artifact-promotion apply routes, then records approved boundaries in `scripts/capture-runs.jsonl`. |
| Synthesis gate | `scripts/synthesis_gate.py` guards promotion of synthesis drafts and records approved boundaries in `scripts/synthesis-runs.jsonl`. |
| Synthesis ledger | `wiki/synthesis.md` orients future synthesis runs; cite source pages, not the ledger, when making claims. |
| Export | `scripts/export_wiki.py` builds a local backup that includes gitignored `raw/` sources. |
| Thin wrappers | `.claude/commands/`, `.codex/commands/`, and `.codex/skills/` expose shortcuts but do not own canonical behavior. |

---

## Cross-Referencing Rules

Use `[[filename-without-extension]]` for all internal links.

In `## Related pages`, use typed relationship labels when the relationship is clear:

| Label | Meaning |
|---|---|
| `Supports` | This page strengthens, evidences, or confirms the linked page |
| `Contradicts` | This page conflicts with or materially challenges the linked page |
| `Depends on` | This page requires the linked page to be understood or true |
| `Derived from` | This page was created from, generalized from, or synthesized out of the linked page |
| `Part of` | This page is a component of the linked larger system, project, or framework |
| `Related` | Meaningful connection, but no stronger typed relationship fits |

Format each item as `- Label: [[page]]`. Do not invent new labels casually; if a new relationship type is repeatedly needed, add it here and to `AGENTS.md` / `wiki/SCHEMA.md`. Existing untyped related links remain valid, but new or touched pages should prefer labels where they add signal.

When stating a specific fact, append `(source: [[source-filename]])`. When stating an opinion or inference, prefix with `Inference:` or `Hypothesis:`.

---

## Key Reference Files

| File | Purpose |
|---|---|
| `wiki/domain.md` | Organization name, scope, active entity types, raw taxonomy, setup status |
| `wiki/index.md` | Master catalog: read for browsing, research, promotion, explicit lookup, and ingest link/index steps; not startup context |
| `wiki/SCHEMA.md` | Entity types, frontmatter spec, source-type templates; read when authoring any new page |
| `wiki/glossary.md` | Canonical term definitions |
| `wiki/design-notes.md` | Why the wiki is designed this way; read before proposing structural changes |
| `wiki/contradictions.md` | Open disagreements between sources; check before updating contested pages |
| `wiki/sourcing-queue.md` | Knowledge gaps and what sources would fill them |
| `wiki/overview.md` | Big-picture synthesis of the configured organization or domain |
| `wiki/synthesis.md` | Current-state digest and append-only synthesis run ledger |

## Support Files

| File or folder | Purpose |
|---|---|
| `raw/README.md` | Source-artifact handling note for the ignored `raw/` corpus |
| `scripts/lint-adjudications.json` | Settled Tier-2 lint judgments with reasons and dates; lint suppresses what it lists |
| `scripts/fixtures/` | Fixture data for live tooling evals |
| `archive/wiki-harness/` | Archived autonomy harness: scripts, schemas, provider manifest, fixtures, and original workflow |

## Capture Boundary

The wiki separates deterministic capture approval from prose judgment:

- `scripts/capture_gate.py` guards analysis capture and artifact promotion approval.
- Workflow prose decides quality: what belongs in the page, which evidence matters, how links should be written, and how contradictions should be handled.
- Do not replace route-specific workflows with scripts unless the behavior is objectively checkable.

## Harness Boundary (Archived)

The wiki autonomy harness and its route preflight are archived under `archive/wiki-harness/`.

- Ordinary ingest proceeds directly through the ingest workflow; no preflight script runs.
- If a piece of work genuinely seems to need staged review before durable edits, that is a judgment call for the prose workflows and the user.
- The live guards that survived the archive are `scripts/wiki_eval.py`, `scripts/lint.py`, `scripts/rebuild_referenced_by.py`, `scripts/capture_gate.py`, `scripts/synthesis_gate.py`, the approval-ledger validators, `scripts/export_wiki.py`, `scripts/sync_codex_skills.py`, and their fixtures.

---

## Layer Architecture (L0-L4)

Every file in this project sits at one of five layers, defined by when it loads relative to a task. Knowing the layer tells a downstream agent whether to read a file unconditionally, on task entry, or only when a specific reference is needed.

| Layer | When loaded | Files |
|---|---|---|
| **L0** | Always: orientation and routing | `AGENTS.md` (`CLAUDE.md` is a pointer for Claude agents), `wiki/domain.md` status check, `CONTEXT.md` |
| **L1** | Route entry: selected by `CONTEXT.md` | `workflows/<workspace>/CONTEXT.md`, `SETUP.md`, or `wiki/index.md` only for browsing |
| **L2** | Task workflow: selected by route entry | `workflows/maintenance/*.md` and any task-specific workflow file named by the L1 route |
| **L3** | Per task: stable reference, loaded on demand | `REFERENCES.md`, `wiki/index.md`, `wiki/SCHEMA.md`, `wiki/glossary.md`, `wiki/primer.md`, `wiki/design-notes.md`, `wiki/contradictions.md`, `wiki/sourcing-queue.md`, `wiki/overview.md` |
| **L4** | During work: content read or written | `wiki/log.md`, `wiki/<entity>/*.md`, `raw/*` |

Loading principle: an agent starting a task should load L0, use `CONTEXT.md` to choose the route, then open only the routed workflow's Load / Skip list. Pull L3 references only when the workflow calls for them. `wiki/index.md` is on-demand for browsing, research, promotion, explicit lookup, and ingest link/index steps; it is not startup context.
