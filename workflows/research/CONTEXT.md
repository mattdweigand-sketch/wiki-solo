---
name: wiki-query
description: Use this workflow when the user asks a question that should be answered from the wiki. Read the wiki, synthesize, file substantial analysis, and auto-audit promotion candidates.
---

# Research Workspace

Consumes the wiki to answer a question, files the answer back as a citable analysis when it is substantial, and auto-audits whether the answer created a durable artifact that belongs somewhere else in the wiki. Single task. This `CONTEXT.md` is the whole workflow.

Analysis capture is a prose workflow with an executable preflight. `scripts/capture_gate.py` decides whether a durable write is approved; this workflow decides whether the analysis is actually useful, cited, and worth filing.

## Load / Skip

- **Load:** `wiki/index.md` to locate pages, `wiki/primer.md` for entry points by question type, then only the specific pages the question touches.
- **Skip:** `wiki/SCHEMA.md`, raw sources, and entity folders unrelated to the question.

## Steps

1. Read `wiki/index.md` (and `wiki/primer.md` if unsure where to start) to identify relevant pages
2. Read those pages
3. Synthesize a clear answer with citations to wiki pages (use `[[page-name]]`)
4. File the answer as a citable analysis when **all three** hold: it synthesized 3+ wiki pages, it runs over 300 words, and it answers a durable question about this wiki's configured domain. Before filing, run `python3 scripts/capture_gate.py` with `--phase accepted`, `--domain-context yes`, those criteria, the intended analysis path, and touched pages. If it requires approval, ask first; after approval, re-run with `--approved`, save to `wiki/analyses/<slug>.md`, and notify in one line: "Filed as `analyses/<slug>.md`." If any criterion fails, answer in chat only.
5. Run the capture gate for reusable artifacts. Ask whether the answer created or refined a reusable distinction, ranking, framework, decision, open-question resolution, or future-agent behavior. If yes, include a promotion audit in the final answer. Do not apply promotion unless the user has already asked to promote, save, apply, file, or update the wiki.
6. Append to `wiki/log.md`:

```
## [YYYY-MM-DD] query | <question summary>
Pages consulted: ...
Output filed: yes/no — <filename if yes>
Promotion audit: none | <recommended route>
```

## Capture Gate

Auto-audit promotion when the answer does any of these:

- Creates a reusable distinction or phrase that future agents should apply
- Changes a ranking, framework, or comparison
- Resolves or sharpens an open question
- Identifies an existing page that should be updated
- Says future agents should behave differently

Use this compact final-answer block:

```
Promotion candidate detected.
Artifact: <durable insight>
Recommendation: discard | update existing page | create new page | update workflow/rule | use ingest instead
Primary home: <path or none>
Reason: <why it is reusable>
Say "apply" to promote.
```

If none apply, say nothing unless the user explicitly asked about promotion. The gate is for surfacing real candidates, not adding boilerplate to every answer.
