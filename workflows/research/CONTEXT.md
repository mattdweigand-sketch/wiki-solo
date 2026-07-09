---
name: wiki-research
description: Router and default workflow for wiki-grounded research. Use wiki-swarm only when its runtime preflight accepts the request.
---

# Research Workspace

Consumes the wiki to answer a question, files the answer back as a citable analysis when it is substantial, and auto-audits whether the answer created a durable artifact that belongs somewhere else in the wiki. This file is the default research workflow; `wiki-swarm.md` is an explicit-invocation overlay that starts here, loads this workflow, and reuses its durable-write path.

Use [`wiki-swarm.md`](wiki-swarm.md) only after `python3 scripts/wiki_swarm.py preflight --question "<request>"` accepts the request. If the preflight rejects it, stay in this default workflow.

Analysis capture is a prose workflow with an executable approval gate. `scripts/capture_gate.py` decides whether a durable write is approved; this workflow decides whether the analysis is useful, cited, and worth filing.

## Load / Skip

- **Load:** `wiki/index.md` to locate pages, `wiki/primer.md` for entry points by question type, then only the specific pages the question touches. When filing an analysis through Analysis Capture, also load `wiki/SCHEMA.md`'s citation/provenance rules.
- **Skip:** the rest of `wiki/SCHEMA.md`, raw sources, and entity folders unrelated to the question.

## Calibration Examples

### Good

- Answer from the smallest set of relevant pages, cite them with `[[page]]`, and separate source-backed facts from inference.
- File an analysis only when the answer synthesizes 3+ pages, is substantial, and creates durable value for the configured domain.
- Surface a promotion candidate when the answer creates a reusable distinction, but keep the audit chat-only unless the user asked to apply it.

### Bad

- Read broad folders because the question feels important.
- File a polished answer as an analysis when it is really a one-off clarification.
- Update a durable page just because the answer could be reusable; first identify the owning page and ask whether the change should be applied.

## Steps

1. Read `wiki/index.md` and `wiki/primer.md` if unsure where to start.
2. Read only the relevant pages.
3. Synthesize a clear answer with citations to wiki pages using `[[page-name]]`.
4. Follow the Analysis Capture section below when the answer should be filed as a citable analysis.
5. Audit promotion candidates. Ask whether the answer created or refined a reusable distinction, ranking, framework, decision, open-question resolution, or future-agent behavior. If yes, include a promotion audit in the final answer. The audit itself is chat-only: do not run `scripts/capture_gate.py` and do not apply the promotion unless the user has already asked to promote, save, apply, file, or update the wiki. The gate runs as part of the apply route in `workflows/maintenance/artifact-promotion.md`.
6. Append to `wiki/log.md` only when an analysis was filed or the user explicitly asked to record the research session:

## Analysis Capture

File the answer as a citable analysis when **all three** hold: it synthesized 3+ wiki pages, it runs over 300 words, and it answers a durable question about this wiki's configured domain. Before filing, stage the draft in `tmp/<slug>.md`, then run the gate:

```bash
python3 scripts/capture_gate.py --artifact "<answer summary>" --phase accepted \
  --synthesized-pages <count> --domain-context yes \
  --primary-home "wiki/analyses/<slug>.md" --pages-touched "<full edit scope>" \
  --path "tmp/<draft>.md"
```

On `APPROVAL REQUIRED`, follow `AGENTS.md`: ask first, re-run with `--approved` after the user approves, then run `python3 scripts/validate_capture_runs.py`. Save to `wiki/analyses/<slug>.md`, add or update the `wiki/index.md` row, run `python3 scripts/rebuild_referenced_by.py`, and run `python3 scripts/lint.py --tier1`. Notify in one line: `Filed as analyses/<slug>.md.` If any criterion fails, answer in chat only and do not write `wiki/log.md`.

```text
## [YYYY-MM-DD] query | <question summary>
Pages consulted: ...
Output filed: yes - <filename>
Promotion audit: none | <recommended route>
```

## Promotion Audit Triggers

Auto-audit promotion when the answer does any of these:

- Creates a reusable distinction or phrase that future agents should apply.
- Changes a ranking, framework, or comparison.
- Resolves or sharpens an open question.
- Identifies an existing page that should be updated.
- Says future agents should behave differently.

Use this compact final-answer block:

```text
Promotion candidate detected.
Artifact: <durable insight>
Recommendation: discard | update existing page | create new page | update workflow/rule | use ingest instead
Primary home: <path or none>
Reason: <why it is reusable>
Say "apply" to promote.
```

If none apply, say nothing unless the user explicitly asked about promotion. The audit is for surfacing real candidates, not adding boilerplate to every answer.
