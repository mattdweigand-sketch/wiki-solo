Run the ingest workflow. The source to ingest is: $ARGUMENTS

If $ARGUMENTS is empty, check `raw/` for any new unorganized files and proceed with those.

The ingest workflow lives in [`workspaces/ingest/CONTEXT.md`](../../workspaces/ingest/CONTEXT.md). Read that, then route through the 3 stages defined in [`workspaces/ingest/workflows/CONTEXT.md`](../../workspaces/ingest/workflows/CONTEXT.md): triage → extract → link. This command is just a Claude Code shortcut; the workflow files are canonical and agent-neutral.
