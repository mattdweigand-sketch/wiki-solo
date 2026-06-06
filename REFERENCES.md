# References

Stable reference material for the wiki maintainer. The core of this file is the **layer-loading model**: it tells any agent *when* each file loads relative to a task, so you pull only what the current job needs instead of reading the whole repo. Read once to internalize; it is not re-read every session.

---

## Role

The wiki maintainer:

- Ingests raw sources and distills them into structured, cited wiki pages
- Keeps pages consistent, cross-referenced, and current
- Answers questions by reading the wiki — never by re-deriving from `raw/`
- Files good answers back into `wiki/analyses/` so knowledge compounds
- Periodically lints for contradictions, stale claims, and orphan pages

Never modify files in `raw/`. Own everything in `wiki/`.

---

## Layer Architecture (L0–L4)

Every file sits at one of five layers, defined by *when* it loads relative to a task. Knowing the layer tells you whether to read a file unconditionally, on session start, on task entry, or only when a specific reference is needed.

| Layer | When loaded | Files |
|---|---|---|
| **L0** | Always — orientation and routing | `AGENTS.md` (`CLAUDE.md` is the pointer for Claude agents), `CONTEXT.md`, `wiki/domain.md` (config-status gate) |
| **L1** | Session start — completes orientation | `REFERENCES.md`, `wiki/index.md`, `wiki/primer.md` |
| **L2** | Per task — workspace entry + workflow | `workspaces/<workspace>/CONTEXT.md`, `workspaces/ingest/workflows/CONTEXT.md` |
| **L3** | Per task — stable reference, loaded on demand | `workspaces/*/docs/*` (schema, citation-rules, classification, query-protocol, analysis-template, lint-criteria, decision-capture), `wiki/glossary.md`, `wiki/overview.md`, `workspaces/maintenance/{contradictions,sourcing-queue,design-notes}.md` |
| **L4** | During work — content read or written | `wiki/log.md`, `wiki/<entity>/*.md`, `raw/*` |

Loading principle: an agent starting a task loads L0 + L1, then the L2 entry for the task, then pulls L3 references only when that workspace's `CONTEXT.md` calls for them. L4 is read or written as the work proceeds. Each workspace `CONTEXT.md` already declares its own Load / Skip list — this model is the why behind those lists.

---

## Cross-Referencing

Use `[[filename-without-extension]]` for all internal links. Two link sections per page, with different ownership:

- `## Related pages` — curated outbound links you write by hand. Editorial: pick the meaningful ones.
- `## Referenced by` — auto-generated inbound links. **Never hand-edit.** Rebuilt from the `[[ ]]` graph by `rebuild_referenced_by.py`, which the ingest, research, and maintenance workflows run. Write your `[[ ]]` links and the inbound list maintains itself.

`## Related pages` may use lightweight relationship labels to explain why the outbound link matters. The label is plain markdown text; the page reference stays an ordinary `[[wikilink]]`.

Allowed labels:

| Label | Meaning |
|---|---|
| `Supports: [[page]]` | This page strengthens, evidences, or confirms the linked page. |
| `Contradicts: [[page]]` | This page conflicts with or materially challenges the linked page. |
| `Depends on: [[page]]` | This page requires the linked page to be understood first or true. |
| `Derived from: [[page]]` | This page was created from, generalized from, or synthesized out of the linked page. |
| `Part of: [[page]]` | This page is a component of the linked larger system, project, or framework. |
| `Related: [[page]]` | Meaningful connection, but no stronger typed relationship fits. |

Examples:

```markdown
- Depends on: [[agent-harness]]
- Supports: [[context-as-moat]]
- Part of: [[sales-harness-os]]
- Derived from: [[outreach-architecture-of-autonomy]]
- Related: [[agent-security]]
```

Plain links remain valid:

```markdown
- [[page]]
```

Do not mechanically backfill every existing related link. Add labels when touching or adjudicating a page, especially in `## Related pages`. Use `Related:` as the fallback when the relationship matters but is not precise.

When stating a fact, append `(source: [[source-page]])`. When stating an opinion or inference, prefix with `Inference:` or `Hypothesis:`.
