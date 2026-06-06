# Agent-Agnostic Refactor Plan

## Deployed Shape

`wiki-solo` now uses this split:

- `AGENTS.md` is the canonical operating map.
- `CLAUDE.md` is a thin compatibility pointer to `AGENTS.md`.
- `.agents/` holds shared workflow machinery.
- `.claude/` holds Claude Code adapters only.
- `wiki/domain.md` remains `status: unconfigured`.

## Canonical Paths

```text
.agents/
  README.md
  commands/
    ingest.md
    lint.md
  scripts/
    rebuild_referenced_by.py
  workspaces/
    ingest/
    research/
    maintenance/

.claude/
  commands/
    ingest.md
    lint.md
```

## Rules

- Put shared workflow logic in `.agents/`.
- Put provider-specific compatibility files in provider folders.
- Do not duplicate project instructions in `CLAUDE.md`.
- Keep root startup flow in `AGENTS.md`.
- Keep workspace routing in `CONTEXT.md`.
- Keep `raw/` immutable.

## Validation Checks

Run these after future structural changes:

```bash
git status --short
find .agents -maxdepth 5 -type f | sort
python3 .agents/scripts/rebuild_referenced_by.py
```

Expected result:

- No canonical workflow references point to provider-specific folders.
- Remaining `.claude/` references are adapter-only.
- Backlink rebuild completes from the repo root.
