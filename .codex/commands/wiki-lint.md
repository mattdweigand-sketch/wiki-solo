# Wiki Lint

Run the lint workflow. Read `workflows/maintenance/CONTEXT.md`, then `workflows/maintenance/lint.md`, and follow the Load / Skip list exactly. Treat Tier-1 as must-fix and Tier-2 as judgment candidates to adjudicate.

Invoking `/lint`, `/wiki-lint`, or `wiki-lint` is authorization to run the full lint workflow, including the verifier-agent evidence check. Skip that evidence check only if the user asks for deterministic-only lint, no subagents, or skipping the evidence check.

This command is just a Codex shortcut. The workflow file is canonical and model-agnostic.
