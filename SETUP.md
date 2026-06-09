# SETUP — First Session After Clone

**Audience: the AI agent in a freshly-cloned wiki.** A human can read this too, but the intent is that an agent picks this up automatically on first session and runs the interview itself.

---

## Trigger

At session start, the repo's canonical map file routes you to [`wiki/domain.md`](wiki/domain.md):

- **OpenAI Codex, Cursor, and other AGENTS-aware tools:** read [`AGENTS.md`](AGENTS.md) first. It is canonical.
- **Claude Code:** auto-loads [`CLAUDE.md`](CLAUDE.md), which is only a thin wrapper that imports `AGENTS.md`.
- **Other agents:** point yourself at `AGENTS.md` manually.

In all cases, the checklist tells you to read [`wiki/domain.md`](wiki/domain.md). If that file has `status: unconfigured` in its frontmatter, **do this before answering any other question.** Tell the user:

> "This wiki is in template state. I can interview you for ~2 minutes to configure it for your organization — or you can skip and just start dropping sources into `raw/`. Want to run setup?"

If the user declines, stop and let them proceed however they want. Don't gate other actions on setup.

If they accept, run the interview below.

---

## Interview

Ask these in order. Keep it conversational; one question at a time unless the user is rapid-firing answers.

1. **Organization name.** "What's the name of the organization, team, or project this wiki is about?"
2. **Domain.** "One line — what subject area does this wiki cover? (Examples: 'private-markets fintech,' 'developer tools for payments,' 'biotech research at a Series B startup.')"
3. **Entity types.** Show the user the 14 default types from [`wiki/SCHEMA.md`](wiki/SCHEMA.md) and ask which to keep. Default is all 14. Common drops: a B2C product may not need `customer` as named accounts; a research lab may not need `competitor`.
4. **Custom entity types.** "Any entity types specific to your domain that aren't in the default 14? (Examples: 'integrations' for a SaaS product, 'experiments' for a research lab, 'regulations' for a compliance team.)"
5. **Source taxonomy.** "What subfolders should exist under `raw/`? Pick categories that match where your source documents come from. (Examples: `competitive-intel`, `customer-research`, `internal-memos`, `release-notes`, `press`.)"
6. **Example queries.** "3–5 questions you want this wiki to answer well. These guide what to ingest first and what `agent_use_cases` to write into entity pages."

---

## What to write after the interview

In order:

### 1. Fill `wiki/domain.md`

Replace the placeholder values in the frontmatter with the user's answers. Flip `status: unconfigured` → `status: configured`. Update `updated:` to today's date.

### 2. Replace `<Organization>` placeholders

Three files have `<Organization>` placeholders that need the user's org name:

| File | Line | What to replace |
|---|---|---|
| [`README.md`](README.md) | 1 | `# <Organization> Wiki` → `# <Their Org> Wiki` |
| [`AGENTS.md`](AGENTS.md) | 1 | `# <Organization> Wiki` → `# <Their Org> Wiki` |
| [`CONTEXT.md`](CONTEXT.md) | 1 | `# <Organization> Wiki — Task Router` → `# <Their Org> Wiki — Task Router` |

Other framework files reference [`domain.md`](wiki/domain.md) or [`wiki/SCHEMA.md`](wiki/SCHEMA.md) rather than hardcoding a name, so no further edits needed there.

Do not rewrite [`CLAUDE.md`](CLAUDE.md) during setup or future operating-map updates. It stays a wrapper around `AGENTS.md`.

### 3. Create raw/ subfolders

For each entry in `raw_taxonomy`, create `raw/<name>/` with a `.gitkeep` file inside.

### 4. Drop unused entity folders

For each of the 14 default entity types **not** in `entity_types_active`, delete the corresponding `wiki/<type>/` folder. For each entry in `entity_types_custom`, create a new `wiki/<type>/` folder with a `.gitkeep`.

If you add custom entity types, also append a row for each to the "Entity Types" table in [`wiki/SCHEMA.md`](wiki/SCHEMA.md) so the ingest workflow knows about them.

### 5. Log the configuration

Append an entry to [`wiki/log.md`](wiki/log.md):

```
## 2026-MM-DD — domain configured

Org: <Org name>
Domain: <one-line summary>
Active entity types: <list>
Custom entity types: <list or "none">
Raw taxonomy: <list>
```

### 6. Confirm with the user

Show a one-paragraph summary of what changed and what's next: "Configured. Drop your first source into `raw/<one of their subfolders>` and run `/ingest`."

---

## What NOT to touch during setup

Hands off:

- [`scripts/`](scripts/) — deterministic helpers and the no-write harness
- [`.claude/commands/`](.claude/commands/) — Claude Code slash-command wrappers
- [`workflows/*/CONTEXT.md`](workflows/) — workflow routers
- [`workflows/maintenance/*.md`](workflows/maintenance/) — maintenance task workflows
- The schema's "Page Format," "Source-Type Summary Templates," and "Confidence Values" sections in [`wiki/SCHEMA.md`](wiki/SCHEMA.md) — domain-agnostic infrastructure

The only schema edit during setup is appending custom entity-type rows to the "Entity Types" table (step 4 above).

---

## Idempotency

If `domain.md` already has `status: configured`, do not re-run setup unless the user explicitly asks. If they ask for a refresh, treat the existing values as defaults in the interview and confirm each one rather than starting from scratch.
