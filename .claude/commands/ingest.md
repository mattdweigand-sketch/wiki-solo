Run the ingest workflow. The source to ingest is: $ARGUMENTS

If $ARGUMENTS is empty, check `raw/` for any new unorganized files and proceed with those.

The ingest workflow lives in [`workflows/ingest/CONTEXT.md`](../../workflows/ingest/CONTEXT.md). Read that and follow its route policy, source-page, entity-update, backlink, lint, promotion-audit, and log steps. This command is just a Claude Code shortcut; the workflow files are canonical and agent-neutral.
