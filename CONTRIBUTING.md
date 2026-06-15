# Contributing

Thanks for improving wiki-solo. This is a template repo — contributions that make it more useful across a wider range of domains, agents, and workflows are welcome.

---

## What's worth contributing

**Good fits:**
- Bug fixes in `rebuild_referenced_by.py`
- Corrections or clarifications to workspace docs (`CONTEXT.md` files, schema, citation rules)
- New `source_type` entries in `wiki/SCHEMA.md` and `workflows/ingest/docs/classification.md` that are broadly applicable
- Improvements to the setup interview flow in `SETUP.md`
- Agent-compatibility improvements (e.g., better `AGENTS.md` for a specific agent runtime)

**Not a good fit:**
- Domain-specific entity types, subfolders, or terminology — those belong in your own configured wiki, not the template
- Opinionated changes to the three-workspace architecture without prior discussion

---

## How to contribute

1. **Fork** the repo and create a branch from `main`.
2. Make your changes. Keep commits focused — one logical change per commit.
3. **Test the workflow end-to-end** if you've touched ingest, research, or maintenance workflows: drop a sample file into `raw/`, run `/wiki-ingest`, ask a question, run `/wiki-lint`, and confirm the output looks right.
4. If you've touched `rebuild_referenced_by.py`, run it against a populated wiki and confirm `## Referenced by` sections update correctly.
5. Open a pull request with a clear description of what changed and why.

---

## Repo conventions

- **Filenames:** kebab-case everywhere (docs, wiki pages, raw files)
- **Internal links:** `[[page-name]]` format — no folder prefix, no extension
- **Prose style:** direct and instructional; written for an AI agent as the primary reader, a human as the secondary reader
- **No hardcoded domain content:** the template must work for any organization. If an example is needed, use generic placeholders (`<organization>`, `[[product-core]]`, `[[customer-acme]]`)
- **Workspace isolation:** each workspace's `CONTEXT.md` controls exactly what that workspace loads — don't add cross-workspace dependencies

---

## Questions

Open an issue before starting significant work. That avoids duplicated effort and ensures the change fits the template's scope.
