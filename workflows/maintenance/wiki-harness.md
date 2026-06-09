# Wiki Harness Workflow

Use this task when running, extending, or debugging the wiki autonomy harness.

The harness exists to keep the wiki workflow observable and testable before any durable write. It does not replace the ingest, research, promotion, or lint workflows.

## Load / Skip

- **Load:** relevant `scripts/wiki_*.py`, relevant `schemas/`, relevant `tests/fixtures/`, and the specific raw source named by a run or fixture. If a local harness PRD exists in `wiki/analyses/`, load it too.
- **Skip:** unrelated wiki entity folders, unrelated raw sources, and model/provider implementation details unless the task explicitly touches a provider adapter.

## Fixed pipeline

The pipeline is invariant:

```text
dry-run -> policy -> semantic providers -> writer provider -> judge provider -> validate run -> apply plan -> apply boundary -> human review/apply
```

Local, cloud, and stub are providers, not workflows. They occupy semantic, writer, or judge provider slots behind the same inputs, outputs, policy checks, and evals.

Do not create separate local and cloud workflows. Add provider adapters only when they preserve the same run artifact contract.

Provider readiness is checked by:

```bash
python3 scripts/wiki_provider_readiness.py <raw-source> --run-id <id> --overwrite
python3 scripts/wiki_eval.py --suite provider
```

The current readiness gate uses only `stub` providers. Future local or cloud providers must fit the same slots, write only under `tmp/wiki-runs/<run-id>/`, declare `writes_wiki: false`, require human review, and pass the existing semantic, run, apply-plan, and pipeline validators.

## Route policy

Every ingest should pass through the lightweight route policy before durable wiki edits:

```bash
python3 scripts/wiki_route_policy.py <raw-source>
```

The route policy writes no files. It runs the deterministic dry-run and diff policy, then emits one of three routes:

| Route | Trigger | Meaning |
|---|---|---|
| `direct_edit` | `task_type=ingest` and diff policy `pass` | Continue with the normal ingest workflow |
| `full_harness` | diff policy `review` | Run the full no-write harness before durable edits |
| `full_harness` | non-`ingest` task type | Use the full no-write harness before durable edits |
| `blocked` | diff policy `reject` | Stop; do not write durable wiki files |

The route policy is the clear boundary between lightweight preflight and full harness use. The full harness is not required for every ingest; it is required whenever deterministic policy returns `review`, when the task is not a plain ingest, or when a future workflow explicitly calls for it.

The provider surface is declared in:

```text
config/wiki-provider-manifest.json
schemas/wiki-provider-manifest.schema.json
```

Validate it directly with:

```bash
python3 scripts/wiki_validate_provider_manifest.py
```

Negative provider manifest fixtures live under:

```text
tests/fixtures/wiki-provider-manifest/
```

These fixtures check that malformed manifests fail for missing or extra slots, unsupported providers, durable-write claims, missing human-review requirements, wrong output artifacts, and wrong readiness/eval commands.

Negative provider readiness fixtures live under:

```text
tests/fixtures/wiki-provider/
```

These fixtures check that the readiness gate catches missing provider artifacts, provider-name mismatches, durable-write claims, missing human-review requirements, visual-source evidence violations, and semantic/run/apply-plan validator failures. Fixtures with `expected_errors: []` are positive provider-readiness cases and must pass after mutation.

## Current artifact contract

`scripts/wiki_run.py` creates a run directory:

```text
tmp/wiki-runs/<run-id>/
  packet.json
  review.md
  policy.json
  draft/
```

`scripts/wiki_writer.py` adds:

```text
tmp/wiki-runs/<run-id>/
  writer.json
  draft/README.md
  draft/manifest.json
  draft/<target-slug>.md.stub
```

`writer.json` includes `provider_metadata.visual_source_evidence`. For non-visual sources this records `required: false`. For visual sources, including screenshot/social artifacts, it records whether evidence extraction was performed, the evidence source (`visual`, `ocr`, `human_verified`, or `none`), and a visible-text summary.

`scripts/wiki_judge.py` adds:

```text
tmp/wiki-runs/<run-id>/judge.json
```

`judge.json` uses the same `provider_metadata.visual_source_evidence` contract. A judge provider must not score `source_fidelity` for a visual source unless evidence extraction was performed and the artifact records a non-empty visible-text summary.

`scripts/wiki_visual_extractor.py` can add a visual evidence artifact:

```text
tmp/wiki-runs/<run-id>/evidence.json
```

The stub extractor records whether visual evidence is required for the source and whether extraction was performed. It does not OCR, inspect pixels, call a model, or authorize writes. Writer and judge provider metadata copy this artifact's evidence fields when it exists.

If a same-stem deterministic OCR sidecar already exists next to the source path, the stub extractor may use it as supporting evidence:

```text
<source-stem>.ocr.txt
```

The extractor normalizes and clips the sidecar text into `visible_text_summary`, records `evidence_extraction_performed: true`, and sets `evidence_source: "ocr"`. Missing or empty sidecars do not count as extracted evidence. The sidecar is not a provider output artifact and does not authorize writes; `evidence.json` remains the canonical handoff to writer and judge providers. For visual sources, `source_fidelity` still cannot be scored unless extraction was performed and the visible-text summary is non-empty.

`scripts/wiki_classifier.py` can add a semantic stub artifact:

```text
tmp/wiki-runs/<run-id>/classifier.json
```

The stub classifier records the page-home route from `packet.json` without calling a model. It is an optional artifact in v1 and does not authorize writes.

`scripts/wiki_contradiction_detector.py` can add a semantic stub artifact:

```text
tmp/wiki-runs/<run-id>/contradictions.json
```

The stub contradiction detector records that no semantic contradiction detection was performed. It emits no contradiction candidates, requires human review, and does not authorize writes.

`scripts/wiki_link_scorer.py` can add a semantic stub artifact:

```text
tmp/wiki-runs/<run-id>/links.json
```

The stub link scorer scores only links already present in `packet.json`; it does not discover links, requires human review, and does not authorize writes.

`scripts/wiki_semantic.py` runs all current semantic stubs for a run:

```text
tmp/wiki-runs/<run-id>/evidence.json
tmp/wiki-runs/<run-id>/classifier.json
tmp/wiki-runs/<run-id>/contradictions.json
tmp/wiki-runs/<run-id>/links.json
```

It is a convenience wrapper over the same provider slots. It does not replace the fixed pipeline and does not authorize writes.

Semantic artifact schemas live under `schemas/`:

```text
schemas/wiki-visual-evidence-artifact.schema.json
schemas/wiki-classifier-artifact.schema.json
schemas/wiki-contradiction-artifact.schema.json
schemas/wiki-link-scorer-artifact.schema.json
```

Negative semantic validator fixtures live under:

```text
tests/fixtures/wiki-semantic/
```

These fixtures check that semantic stubs cannot overclaim judgment, invent links, change page-home decisions away from the dry-run packet, misstate visual evidence extraction, or declare durable writes.

`scripts/wiki_validate_run.py` checks an existing run directory without creating or mutating artifacts.

`scripts/wiki_validate_semantic.py` checks existing semantic artifacts without creating or mutating artifacts.

`scripts/wiki_apply.py` checks whether a validated run can cross the apply boundary. In v1 it is still no-write: it reports blockers and approval requirements, and it does not write under `wiki/`.

`scripts/wiki_apply_plan.py` emits a JSON apply plan for a validated run. It is also no-write: the plan records target files, manifest operations, blockers, review reasons, and `writes_wiki: false`.

`scripts/wiki_validate_apply_plan.py` validates an apply plan JSON artifact from a file or stdin.

Negative apply-plan validator fixtures live under:

```text
tests/fixtures/wiki-apply-plan/
```

These fixtures check that apply plans require approval, remain no-write, include blockers when blocked, avoid duplicate operation targets, and keep `target_files` aligned with manifest operations.

Positive apply-plan fixtures live under:

```text
tests/fixtures/wiki-apply-plan-valid/
```

These fixtures lock in stable valid plan shapes for existing-source no-op plans, new-source create plans, and blocked policy-reject plans.

`scripts/wiki_pipeline.py` also writes a top-level run summary:

```text
tmp/wiki-runs/<run-id>/pipeline.json
```

This records the run directory, source path, task type, stub providers used, expected artifact paths, and `writes_wiki: false`.

`scripts/wiki_validate_pipeline.py` validates `pipeline.json` and checks that every listed artifact exists under the run directory.

Negative pipeline validator fixtures live under:

```text
tests/fixtures/wiki-pipeline/
```

The apply plan schema lives at:

```text
schemas/wiki-apply-plan.schema.json
schemas/wiki-pipeline-artifact.schema.json
```

All run artifacts live under ignored `tmp/`. Harness scripts must not write under `wiki/` unless a later apply workflow explicitly exists and is approved.

`draft/manifest.json` is the proposed-diff contract for future writer providers. It maps every proposed operation to a target path from `packet.json` `expected_touched_files`. If the packet has no expected touched files, the manifest must contain a `no_op` operation. The manifest itself is not an apply instruction and cannot authorize durable writes.

Manifest validation blocks unsafe proposed-diff shapes before the apply boundary:

- `delete` operations are not allowed yet.
- Non-`no_op` targets must be under `wiki/`.
- Draft paths must stay under `tmp/wiki-runs/<run-id>/draft/`.
- Draft files referenced by write operations must exist.
- A target path can appear only once.
- Operation targets must exactly match `packet.json` `expected_touched_files`.

## Commands

Run the current no-model harness:

```bash
python3 scripts/wiki_pipeline.py <raw-source> --run-id <id> --overwrite
```

Equivalent expanded command sequence:

```bash
python3 scripts/wiki_run.py <raw-source> --run-id <id> --overwrite
python3 scripts/wiki_semantic.py tmp/wiki-runs/<id> --provider stub --overwrite
python3 scripts/wiki_writer.py tmp/wiki-runs/<id>/packet.json --provider stub --overwrite
python3 scripts/wiki_judge.py tmp/wiki-runs/<id> --provider stub --overwrite
python3 scripts/wiki_validate_run.py tmp/wiki-runs/<id>
python3 scripts/wiki_validate_semantic.py tmp/wiki-runs/<id>
python3 scripts/wiki_apply_plan.py tmp/wiki-runs/<id> > tmp/wiki-runs/<id>/apply-plan.json
python3 scripts/wiki_validate_apply_plan.py tmp/wiki-runs/<id>/apply-plan.json
python3 scripts/wiki_validate_pipeline.py tmp/wiki-runs/<id>/pipeline.json
```

Validate an existing run artifact directly:

```bash
python3 scripts/wiki_validate_run.py tmp/wiki-runs/<id>
python3 scripts/wiki_validate_semantic.py tmp/wiki-runs/<id>
```

Validate a run with expected statuses and drafts:

```bash
python3 scripts/wiki_validate_run.py tmp/wiki-runs/<id> \
  --expected-policy-status pass \
  --expected-judge-decision approve_for_review \
  --expected-draft draft/README.md
```

Check the apply boundary:

```bash
python3 scripts/wiki_apply_plan.py tmp/wiki-runs/<id>
python3 scripts/wiki_apply_plan.py tmp/wiki-runs/<id> | python3 scripts/wiki_validate_apply_plan.py -
python3 scripts/wiki_apply.py tmp/wiki-runs/<id>
python3 scripts/wiki_apply.py tmp/wiki-runs/<id> --approved
```

The plan command emits JSON for inspection. The first boundary command reports the approval block. The second confirms boundary eligibility after approval, but v1 still writes no durable files.

Run all deterministic harness evals:

```bash
python3 scripts/wiki_eval.py
```

Golden dry-run ingest examples live under:

```text
tests/fixtures/wiki-ingest/
```

These fixtures cover successful historical sources and assert deterministic packet fields such as source type, primary home, touched files, review requirement, no-write status, and expected risk flags.

Fixtures may also declare `expected_absent_risk_flags` when the point of the example is to prevent a false-positive risk, `expected_exact_risk_flags` when no extra risk flags should appear, and `expected_policy_status` when the generated dry-run packet must produce a specific policy result. Visual/social screenshots are allowed as source artifacts, but the dry-run should mark them for review with `visual_source_requires_review` and `social_source_requires_review` rather than rejecting them as `unsupported_source_extension`.

Screenshot/social source fidelity depends on visible-text extraction or human verification notes. A provider must not claim source fidelity for a visual artifact unless the run artifact records what visible text or image evidence it relied on.

Run a targeted suite:

```bash
python3 scripts/wiki_eval.py --suite ingest
python3 scripts/wiki_eval.py --suite policy
python3 scripts/wiki_eval.py --suite run
python3 scripts/wiki_eval.py --suite apply
python3 scripts/wiki_eval.py --suite semantic
python3 scripts/wiki_eval.py --suite pipeline
python3 scripts/wiki_eval.py --suite provider
python3 scripts/wiki_eval.py --suite route
python3 scripts/wiki_eval.py --suite tier1
```

## Extension rules

1. Keep the pipeline fixed. Change providers, not architecture.
2. Keep writes inside `tmp/wiki-runs/<run-id>/` until a separate apply workflow exists.
3. Record provider metadata in `writer.json` or `judge.json`.
4. Run `python3 scripts/wiki_validate_run.py tmp/wiki-runs/<run-id>` before trusting a provider-generated artifact.
5. Run `python3 scripts/wiki_apply.py tmp/wiki-runs/<run-id>` before considering any durable apply.
6. Add or update fixtures before trusting new behavior.
7. Run `python3 scripts/wiki_eval.py` before committing harness changes.
8. Preserve `scripts/capture_gate.py`, `scripts/rebuild_referenced_by.py`, and `scripts/lint.py`; the harness composes around them.

## Source of truth

The implementation spec is `wiki/analyses/wiki-autonomous-maintenance-prd.md`. If behavior diverges from that PRD, update the PRD through the appropriate wiki workflow rather than letting script behavior become the only documentation.
