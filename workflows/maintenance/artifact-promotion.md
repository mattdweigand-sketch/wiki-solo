---
name: wiki-artifact-promotion
description: Use this workflow when a useful output, draft, chat answer, script, prompt, or working artifact should be promoted into durable wiki memory.
---

# Artifact Promotion Workflow

Artifact promotion turns useful work into the right durable layer of the wiki. It is not a new entity type. It is a routing decision for artifacts that start outside the wiki or inside a temporary answer and may deserve to become source, concept, analysis, decision, initiative, style, workflow, schema, or script material.

This workflow is both the PRD and implementation spec for promotion. The executable gate is `scripts/capture_gate.py`, which standardizes the approval preflight for artifact promotion and analysis capture. Use code for the checkable approval boundary; use this workflow for judgment about the right home, page quality, links, and logging.

Promotion has two modes:

- **Audit only** — evaluate the artifact and recommend one primary route. Do not edit files. Use when the user asks whether or how something should be promoted.
- **Apply** — make the chosen wiki update, rebuild backlinks, run Tier-1 lint, and log the promotion. Use when the user explicitly asks to promote, apply, save, file, or update the wiki after the audit.

At the end of wiki-related work, if a useful reusable insight appears, run an audit automatically and show the recommended route. Apply the promotion only if the user has explicitly asked to promote, apply, save, file, update the wiki, ingest, commit, or otherwise make a durable repo change.

Before applying any promotion or filing any analysis capture, run `python3 scripts/capture_gate.py` with the proposed artifact, phase, primary home, touched pages, and analysis criteria or promotion triggers. Ordinary ingest, decision capture, observation capture, workflow updates, and routine page updates do not require this approval gate unless they are part of an artifact-promotion or analysis-capture route.

If the script prints `APPROVAL REQUIRED`, show that exact block and do not edit files until the user approves the exact route. Re-run with `--approved` only after that approval.

## Executable Contract

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

The script prints the derived mode: `chat-only`, `ingest`, `analysis-capture`, `promotion-audit`, `capture-decision`, `capture-experience`, or `workflow-update`. Approval is required only for `analysis-capture` and `promotion-audit` unless the command is re-run with `--approved`.

Collaborative drafting is chat-only by default. Requests like "work with me," "let's discuss," "refine this," "make this sharper," or "help me think through" are not promotion intent. If the draft becomes clearly durable, ask whether to save it; do not edit files first.

## Load / Skip

- **Load:** the artifact to evaluate, `wiki/SCHEMA.md`, `wiki/index.md`, and only the pages the artifact directly touches.
- **Load when changing workflow behavior:** `AGENTS.md`, root `CONTEXT.md`, `REFERENCES.md`, and the relevant `workflows/` file.
- **Skip:** unrelated entity folders, raw sources not cited by the artifact, and broad lint unless a contradiction or broken link appears.

## PRD

### Problem

Useful outputs are created during chats, research answers, emails, scripts, prompts, source reviews, and ingest work. If they stay in chat or ad hoc files, future agents must re-derive them. If every useful output becomes a new page, the wiki bloats. The wiki needs a simple promotion rule that decides what should be saved, where it should live, and when it should change future agent behavior.

### Goal

Preserve only artifacts with durable reuse value, place each artifact at the right layer, and make future agents able to find and apply it without reading the original context again.

### Non-Goals

- Do not create a generic `outputs/` entity type unless repeated artifacts stop fitting existing entity types.
- Do not preserve every answer.
- Do not modify `raw/`.
- Do not put canonical behavior only in tool-specific wrappers.
- Do not bypass contradiction checks, provenance, schema, or lint.

### Users

- Future AI agents maintaining the wiki.
- Operators using the wiki as an organizational context layer.
- Any tool surface over the repo, including Codex, Claude, Cursor, or a raw API harness.

### Success Criteria

- The artifact is either intentionally discarded or promoted to exactly one primary home.
- The promoted artifact has provenance, links, and an index entry when it is a wiki page.
- If the artifact changes future behavior, the relevant workflow file or operating doc is updated.
- `scripts/rebuild_referenced_by.py` and `scripts/lint.py --tier1` pass after changes.
- `wiki/log.md` records the promotion decision.

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
| Harness fixture/schema | `schemas/`, `tests/fixtures/`, `config/` | The artifact defines or validates no-write automation behavior | Route-policy fixture |

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
6. Produces a reusable prompt, script idea, checklist, spec, schema, fixture, or workflow step.

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
10. **Is it deterministic repeatable logic?** If yes, propose or add a script under `scripts/`, plus schema or fixtures when needed.
11. **If none apply, discard it and log only if the user asked for a durable check.**

## Audit-Only Output

When the user asks whether, how, or where to promote an artifact, answer with a promotion audit before editing:

```text
Artifact: <what is being evaluated>
Recommendation: discard | update existing page | create new page | update workflow/rule | use ingest instead
Primary home: <path or "none">
Reason: <which promotion test it passes or fails>
Pages touched if applied: <short list>
Do not promote because: <only if discarded>
```

Stop after the audit unless the user has already asked to apply the promotion.

## Page Requirements

When creating a wiki page:

1. Use `wiki/SCHEMA.md` frontmatter.
2. Add `agent_use_cases` unless the page type is exempt.
3. Include a one-line summary.
4. Cite source pages with `(source: [[page]])` when stating specific facts.
5. Use `## Related pages` with typed relationship labels when clear.
6. Update `wiki/index.md`.
7. Run `python3 scripts/rebuild_referenced_by.py`.

When updating operating docs:

1. Keep canonical rules in `AGENTS.md`, root `CONTEXT.md`, `REFERENCES.md`, or `workflows/`.
2. Avoid putting canonical behavior only in tool-specific wrappers.
3. Keep the rule short enough for future agents to follow.
4. Update route tables if the workflow must be discoverable.

## Workflow Steps

1. Identify the artifact and candidate promotion path in one sentence.
2. Search `wiki/index.md` and relevant folders for existing pages.
3. Choose one primary home from the promotion ladder.
4. If the user asked for audit only, return the audit output and stop.
5. Run `python3 scripts/capture_gate.py` for the proposed apply route. If it requires approval, show the exact output and stop. Continue only after approval and re-run with `--approved`.
6. Update the existing page or create the new page, workflow file, script, schema, or fixture.
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

## Examples

### Chat answer becomes analysis

A long answer compares several competitor pages and a pricing decision. It synthesizes multiple pages and will be reused. Promote it to `wiki/analyses/<slug>.md`, link the cited pages, update `wiki/index.md`, rebuild backlinks, and log.

### Chat answer updates an existing page

A short answer refines the definition of a market category already covered in `wiki/concepts/`. Audit-only recommendation: update that concept page; do not create a new page.

### Repeated behavior becomes workflow

A chat answer says future agents should classify artifacts by durable value before saving them. If that behavior should repeat, promote it into this workflow and route it through maintenance.

### One-off explanation is discarded

A short answer explains a term for the current conversation. It does not change a decision, concept, source, initiative, or workflow. Do not save it.
