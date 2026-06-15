---
name: wiki-artifact-promotion
description: Use this workflow when a useful output, draft, chat answer, script, prompt, or working artifact should be promoted into durable wiki memory.
---

# Artifact Promotion Workflow

Artifact promotion is a router before it is a write. It turns useful work into the right durable layer of the wiki, or decides not to save it. It is not a new entity type. It handles artifacts that start outside the wiki or inside a temporary answer and may deserve to become source, concept, analysis, decision, initiative, style, workflow, schema material, an update to an existing page, or nothing at all.

This workflow remains the prose policy for promotion. The executable gate is `scripts/capture_gate.py`, which standardizes the approval preflight for artifact promotion and analysis capture. Use code for the checkable approval boundary; use this workflow for judgment about the right home, page quality, links, and logging.

Promotion has two modes:

- **Audit only** - evaluate the artifact and recommend one primary route. Do not edit files. Use when the user asks whether or how something should be promoted.
- **Apply** - make the chosen wiki update, rebuild backlinks, run Tier-1 lint, and log the promotion. Use when the user explicitly asks to promote, apply, save, file, or update the wiki after the audit.

The `/wiki-promote` shortcut is a route-first command. It does not mean "create a new promotion page." It means: evaluate the artifact, pick the right durable home, then either return an audit or apply the selected route if durable-write intent is already clear. Use `/wiki-capture` instead when the user is directly recording a decision or lived context, not promoting a separate artifact.

Agents may use `python3 scripts/wiki_promote.py "<artifact>"` as an agent-neutral shortcut to start an audit. The shortcut writes no files. It delegates apply approval to `scripts/capture_gate.py` when run with `--apply`.

At the end of wiki-related work, if a useful reusable insight appears, run an audit automatically and show the recommended route. Apply the promotion only if the user has explicitly asked to promote, apply, save, file, update the wiki, ingest, commit, or otherwise make a durable repo change. Otherwise stop at the audit and ask for confirmation.

Before applying any promotion or filing any analysis capture, run `python3 scripts/capture_gate.py` with the proposed artifact, phase, primary home, touched pages, and analysis criteria or promotion triggers. Ordinary ingest, decision capture, experience capture, workflow updates, setup updates, and routine page updates do not require this approval gate unless they are part of an artifact-promotion or analysis-capture route. If it prints `APPROVAL REQUIRED`, show the full block and do not edit files until the user approves the displayed durable action, primary destination, and allowed file scope. Re-run with `--approved` only after that approval, then run `python3 scripts/validate_capture_runs.py`.

The executable preflight contract is:

```bash
python3 scripts/capture_gate.py \
  --artifact "<what is being evaluated>" \
  --phase drafting|accepted|source|decision|experience|workflow \
  --primary-home "<path or none>" \
  --pages-touched "<comma-separated paths>" \
  [--source-path "<raw path or URL>"] \
  [--synthesized-pages <count>] \
  [--word-count <count>] \
  [--domain-context yes|no] \
  [--trigger reusable_distinction|ranking_or_framework|open_question_resolution|future_agent_behavior|existing_page_update]
```

The script prints the derived mode: `chat-only`, `ingest`, `analysis-capture`, `promotion-audit`, `capture-decision`, `capture-experience`, or `workflow-update`. Approval is required only for the derived `analysis-capture` and `promotion-audit` routes unless re-run with `--approved` after the user approves the displayed durable action, primary destination, and allowed file scope. Approved reruns append or confirm an idempotent structured record in `scripts/capture-runs.jsonl`; validate it with `python3 scripts/validate_capture_runs.py`.

Collaborative drafting is chat-only by default. Requests like "work with me," "let's discuss," "let's define," "refine this," "make this sharper," or "help me think through" are not promotion intent, even when the topic already has a wiki page, the repo is the current working directory, or the result might be reusable. If the draft becomes clearly durable, ask whether to save it; do not edit files first.

## Load / Skip

- **Load:** the artifact to evaluate, `wiki/SCHEMA.md`, `wiki/index.md`, and only the pages the artifact directly touches.
- **Load when changing workflow behavior:** `AGENTS.md`, root `CONTEXT.md`, `REFERENCES.md`, and the relevant `workflows/` file.
- **Skip:** unrelated entity folders, raw sources not cited by the artifact, and broad lint unless a contradiction or broken link appears.

## Promotion Ladder

| Layer | Put it here | Use when | Example |
|---|---|---|---|
| Discard | no file | Useful only in the moment | A one-off explanation |
| Raw source | `raw/` | User provides a source artifact to preserve | Transcript, email, PDF, note |
| Source page | `wiki/sources/` | The artifact is evidence from an external or internal source | Summary of a transcript |
| Concept | `wiki/concepts/` | The artifact names a reusable idea or model | Artifact promotion |
| Analysis | `wiki/analyses/` | The artifact synthesizes multiple pages or answers a durable question | Competitive comparison |
| Decision | `wiki/decisions/` | The artifact records a choice and rationale | Adopt typed relationship labels |
| Initiative update | `wiki/initiatives/` | The artifact changes an active initiative record | Launch scope update |
| Style rule | `wiki/style/` | The artifact governs writing or naming style | Naming pattern |
| Operating rule | `AGENTS.md`, `CONTEXT.md`, `REFERENCES.md`, or `workflows/` | The artifact should change how future agents behave | New maintenance workflow |
| Script | `scripts/` | The artifact is deterministic and repeatable | Link rebuild, lint check |

## Promotion Tests

Promote an artifact only when at least one is true:

1. It will likely be reused by a future agent.
2. It captures a decision, rule, or distinction that would otherwise be re-litigated.
3. It synthesizes 3 or more pages into a useful answer.
4. It changes how the wiki should be maintained.
5. It preserves source-grounded facts that should not be lost.
6. It defines deterministic behavior that can be tested.

Do not promote when all are true:

1. It is only a conversational clarification.
2. It has no durable source, decision, operating, or test value.
3. It duplicates an existing page without a meaningful update.
4. It would create a new category just to hold one artifact.

## Auto-Audit Triggers

Promotion audit auto-triggers after wiki research, ingest, or maintenance work when the answer or work product does any of these:

1. Creates a reusable distinction, label, or phrase future agents should apply.
2. Changes a ranking, framework, comparison, or decision tree.
3. Resolves or sharpens an open question.
4. Identifies an existing page that should be updated.
5. Says future agents should behave differently.
6. Produces a reusable prompt, script idea, checklist, spec, or workflow step.

Auto-audit means classify the artifact and recommend a route. It does not mean editing files. Apply mode still requires explicit durable-write intent.

## Routing Spec

Use this decision order:

1. **Is the user still drafting?** If yes, stay in chat. Do not audit or edit.
2. **Is it a source?** If yes, use ingest, not this workflow.
3. **Does it meet research analysis-capture criteria?** It must synthesize 3+ wiki pages, run over 300 words, and answer a durable domain-context question. If yes, route to `wiki/analyses/<slug>.md`.
4. **Is it already covered by an existing page?** If yes, update that page instead of creating a duplicate.
5. **Is it a durable answer or synthesis that does not meet analysis capture?** If yes, audit before deciding whether to update an existing analysis or keep it chat-only.
6. **Is it a reusable model?** If yes, create or update `wiki/concepts/<slug>.md`.
7. **Is it a decision?** If yes, create or update `wiki/decisions/<slug>.md`.
8. **Is it an initiative state change?** If yes, update the relevant `wiki/initiatives/` page.
9. **Is it an operating instruction for future agents?** If yes, update `AGENTS.md`, root `CONTEXT.md`, `REFERENCES.md`, or the relevant `workflows/` file.
10. **Is it deterministic repeatable logic?** If yes, propose or add a script under `scripts/`.
11. **If none apply, discard it and log only if the user asked for a durable check.**

## Route Outcomes

Use these route labels in audit output and log entries:

| Route | Use when | Workflow to follow |
|---|---|---|
| `discard` | The artifact has no durable source, decision, operating, or reuse value | Stop after audit |
| `ingest` | The artifact is a source that should be preserved before synthesis | `workflows/ingest/CONTEXT.md` |
| `analysis-capture` | The artifact is a substantial synthesis meeting the analysis criteria | `workflows/research/CONTEXT.md` analysis filing step |
| `update-existing-page` | A current wiki page already owns the idea or facts | This workflow plus the target page's schema |
| `create-page` | No current page owns the durable concept, analysis, style rule, or similar artifact | This workflow plus `wiki/SCHEMA.md` |
| `capture-decision` | The artifact records a choice and rationale | `workflows/maintenance/capture-decision.md` |
| `capture-experience` | The artifact records observed or lived context | `workflows/maintenance/capture-experience.md` |
| `workflow-update` | The artifact changes how future agents should behave | Update `AGENTS.md`, `CONTEXT.md`, or `workflows/` |
| `script` | The artifact is deterministic repeatable logic | Add or update `scripts/` with tests when appropriate |

## Audit-Only Output

When the user asks whether, how, or where to promote an artifact, answer with a promotion audit before editing:

```text
Artifact: <what is being evaluated>
Route: discard | ingest | analysis-capture | update-existing-page | create-page | capture-decision | capture-experience | workflow-update | script
Recommendation: <one sentence action>
Primary home: <path or "none">
Reason: <which promotion test it passes or fails>
Pages touched if applied: <short list>
Do not promote because: <only if discarded>
```

Stop after the audit unless the user has already asked to apply the promotion.

## Workflow Steps

1. Identify the artifact and candidate promotion path in one sentence.
2. Search `wiki/index.md` and relevant folders for existing pages.
3. Choose one primary home from the promotion ladder.
4. If the user asked for audit only, return the audit output and stop.
5. Run `python3 scripts/capture_gate.py` for the proposed apply route. If it requires approval, show the exact output and stop. Continue only after approval, re-run with `--approved`, and run `python3 scripts/validate_capture_runs.py`.
6. Update the existing page or create the new page, workflow file, or script.
7. Add or update meaningful `[[wikilinks]]`.
8. Update `wiki/index.md` for new or materially changed wiki pages.
9. Run:

   ```bash
   python3 scripts/rebuild_referenced_by.py
   python3 scripts/lint.py --tier1
   ```

10. Append to `wiki/log.md`:

   ```text
   ## [YYYY-MM-DD] promotion | <artifact summary>
   Artifact: <chat answer/source/draft/script/etc.>
   Promoted to: <path or discarded>
   Reason: <reuse value>
   Pages updated: ...
   Verification: ...
   ```

## Acceptance Checklist

- [ ] A future agent can find the promoted artifact from `wiki/index.md`, root `CONTEXT.md`, or `workflows/maintenance/CONTEXT.md`.
- [ ] The artifact has one primary home.
- [ ] Related pages link to it where the relationship is meaningful.
- [ ] No raw file was modified.
- [ ] The change avoids a new entity type unless the user approved one.
- [ ] `python3 scripts/lint.py --tier1` passes.
