Run the ingest workflow. The source to ingest is: $ARGUMENTS

If $ARGUMENTS is empty, check `raw/` for any new unorganized files and proceed with those.

The ingest workflow lives in [`.claude/workspaces/ingest/CONTEXT.md`](../workspaces/ingest/CONTEXT.md). Read that, then route through the 3 stages defined in [`.claude/workspaces/ingest/workflows/CONTEXT.md`](../workspaces/ingest/workflows/CONTEXT.md): triage → extract → link.
