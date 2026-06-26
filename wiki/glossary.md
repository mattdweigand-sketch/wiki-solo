---
title: Glossary
type: glossary
created: 2026-05-17
updated: 2026-06-26
---

# Glossary

Canonical definitions for domain-specific terms used in this wiki. Add an entry whenever a term has a precise meaning that downstream agents shouldn't paraphrase.

Entry template:

```text
### <Term>
Type: domain-term | framework | principle | workflow-convention
Definition: <one or two precise sentences>
Source: [[source-page]] or experience: <brief description>
Related: [[page]], [[page]]
```

## Wiki Operating Terms

- **Analysis capture** - saving a substantial, cross-page research answer as `wiki/analyses/<slug>.md` after the capture gate approves the exact destination and file scope.
- **Artifact promotion** - routing a useful artifact into the right durable layer: discard, ingest, update an existing page, create a page, capture a decision or experience, update a workflow, or add deterministic script logic.
- **Capture gate** - `scripts/capture_gate.py`, the approval preflight for analysis capture, artifact-promotion apply routes, and reviewed synthesis promotion.
- **Confidence** - the page-level trust label from `wiki/SCHEMA.md`: `high`, `medium`, `low`, or `contested`.
- **Evidence review** - the judgment step in the lint workflow that samples cited claims and tries to refute them against source pages and raw evidence.
- **Ingest** - preserving a raw source and turning it into a source page plus any affected entity-page updates.
- **Related pages** - authored outbound `[[wikilinks]]` that name meaningful relationships. Use typed labels when they add signal.
- **Referenced by** - generated inbound-link sections rebuilt by `scripts/rebuild_referenced_by.py`. Do not hand-edit them.
- **Review by** - an optional frontmatter checkpoint (`review_by: YYYY-MM-DD`) that enrolls a page in outcome review.
- **Synthesis** - a bounded pass that asks what the corpus now implies across pages, drafts candidates for review, and promotes only approved conclusions.
