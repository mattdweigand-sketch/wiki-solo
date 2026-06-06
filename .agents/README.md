# Shared Agent Workflows

This folder holds provider-neutral workflow instructions for the wiki.

- `commands/` contains reusable command prompts.
- `workspaces/` contains task-specific routing and operating rules.
- `scripts/` contains shared utility scripts.

Provider-specific folders, such as `.claude/`, are adapters only. Do not put canonical workflow logic there. Update `AGENTS.md` when changing startup flow, folder maps, or hard rules.
