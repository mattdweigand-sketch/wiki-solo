#!/usr/bin/env python3
"""Run fixture tests for no-write wiki run artifact creation."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from wiki_eval_sources import ensure_eval_sources, remove_existing_source_page, write_existing_source_page


DEFAULT_FIXTURE_DIR = Path("tests/fixtures/wiki-run")
RUNS_ROOT = Path("tmp/wiki-runs")
EXPECTED_ARTIFACTS = ["packet.json", "review.md", "policy.json", "writer.json", "judge.json"]
EXPECTED_DRAFT_ARTIFACTS = ["draft/manifest.json"]
WRITER_KEYS = {
    "writer_version",
    "provider",
    "source_path",
    "primary_home",
    "draft_path",
    "writes_wiki",
    "provider_metadata",
}
JUDGE_KEYS = {
    "judge_version",
    "provider",
    "decision",
    "policy_status",
    "writer_provider",
    "scores",
    "findings",
    "human_review_required",
    "writes_wiki",
    "provider_metadata",
}
JUDGE_SCORE_KEYS = {
    "route_correctness",
    "source_fidelity",
    "citation_adequacy",
    "link_quality",
    "scope_discipline",
}
DRAFT_MANIFEST_KEYS = {
    "manifest_version",
    "source_path",
    "primary_home",
    "operations",
    "writes_wiki",
}
DRAFT_OPERATION_KEYS = {"op", "target_path", "draft_path", "status"}
DRAFT_OPS = {"create", "update", "delete", "no_op"}
DRAFT_WRITE_OPS = {"create", "update"}
DRAFT_STATUSES = {"stub", "drafted", "ready", "blocked"}
VISUAL_SOURCE_FLAG = "visual_source_requires_review"
VISUAL_EVIDENCE_KEYS = {
    "required",
    "evidence_extraction_performed",
    "evidence_source",
    "visible_text_summary",
}
VISUAL_EVIDENCE_SOURCES = {"visual", "ocr", "human_verified", "none"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate no-write wiki run fixtures.")
    p.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory containing run fixture JSON files.",
    )
    return p


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_status_wiki() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no", "wiki"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def delete_nested(value: dict[str, Any], key_path: list[str]) -> None:
    current: Any = value
    for key in key_path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(key)
    if isinstance(current, dict):
        current.pop(key_path[-1], None)


def set_nested(value: dict[str, Any], key_path: list[str], replacement: Any) -> None:
    current: Any = value
    for key in key_path[:-1]:
        if isinstance(current, dict):
            current = current.setdefault(key, {})
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            return
    if isinstance(current, dict):
        current[key_path[-1]] = replacement
    elif isinstance(current, list) and key_path[-1].isdigit() and int(key_path[-1]) < len(current):
        current[int(key_path[-1])] = replacement


def visual_source_required(packet: dict[str, Any]) -> bool:
    risk_flags = packet.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        return False
    return VISUAL_SOURCE_FLAG in risk_flags


def validate_visual_source_evidence(
    metadata: dict[str, Any],
    artifact_name: str,
    visual_required: bool,
    source_fidelity_claimed: bool = False,
) -> list[str]:
    errors: list[str] = []
    evidence = metadata.get("visual_source_evidence")
    if evidence is None:
        errors.append(f"{artifact_name} visual_source_evidence is required in provider_metadata")
        return errors
    if not isinstance(evidence, dict):
        errors.append(f"{artifact_name} visual_source_evidence must be an object")
        return errors

    missing = sorted(VISUAL_EVIDENCE_KEYS - evidence.keys())
    extra = sorted(evidence.keys() - VISUAL_EVIDENCE_KEYS)
    if missing:
        errors.append(f"{artifact_name} visual_source_evidence missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{artifact_name} visual_source_evidence has unsupported fields: {', '.join(extra)}")

    required = evidence.get("required")
    performed = evidence.get("evidence_extraction_performed")
    evidence_source = evidence.get("evidence_source")
    summary = evidence.get("visible_text_summary")

    if not isinstance(required, bool):
        errors.append(f"{artifact_name} visual_source_evidence.required must be a boolean")
    elif visual_required and required is not True:
        errors.append(f"{artifact_name} visual_source_evidence.required must be true for visual sources")
    elif not visual_required and required is not False:
        errors.append(f"{artifact_name} visual_source_evidence.required must be false for non-visual sources")

    if not isinstance(performed, bool):
        errors.append(f"{artifact_name} visual_source_evidence.evidence_extraction_performed must be a boolean")
    if evidence_source not in VISUAL_EVIDENCE_SOURCES:
        errors.append(f"{artifact_name} visual_source_evidence.evidence_source is invalid")
    if not isinstance(summary, str):
        errors.append(f"{artifact_name} visual_source_evidence.visible_text_summary must be a string")

    has_evidence = (
        performed is True
        and evidence_source in (VISUAL_EVIDENCE_SOURCES - {"none"})
        and isinstance(summary, str)
        and bool(summary.strip())
    )
    if performed is True and evidence_source == "none":
        errors.append(
            f"{artifact_name} visual_source_evidence.evidence_source cannot be none when extraction was performed",
        )
    if performed is False and evidence_source != "none":
        errors.append(
            f"{artifact_name} visual_source_evidence.evidence_source must be none when extraction was not performed",
        )
    if performed is True and isinstance(summary, str) and not summary.strip():
        errors.append(
            f"{artifact_name} visual_source_evidence.visible_text_summary is required when extraction was performed",
        )
    if performed is False and isinstance(summary, str) and summary.strip():
        errors.append(
            f"{artifact_name} visual_source_evidence.visible_text_summary must be empty when extraction was not performed",
        )
    if source_fidelity_claimed and visual_required and not has_evidence:
        errors.append(f"{artifact_name} source_fidelity cannot be scored without visual evidence extraction")

    return errors


def apply_mutations(run_dir: Path, mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, mutation in enumerate(mutations):
        artifact = mutation.get("artifact")
        if artifact not in {"writer.json", "judge.json", "draft/manifest.json"}:
            errors.append(
                f"mutation[{index}] artifact must be writer.json, judge.json, or draft/manifest.json"
            )
            continue

        path = run_dir / str(artifact)
        if not path.exists():
            errors.append(f"mutation[{index}] target does not exist: {path}")
            continue

        value = load_json(path)
        for key_path in mutation.get("delete", []):
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"mutation[{index}] delete path must be a list of strings")
                continue
            delete_nested(value, key_path)

        for change in mutation.get("set", []):
            key_path = change.get("path") if isinstance(change, dict) else None
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"mutation[{index}] set path must be a list of strings")
                continue
            set_nested(value, key_path, change.get("value"))

        write_json(path, value)
    return errors


def validate_writer_contract(
    writer: dict[str, Any],
    packet: dict[str, Any],
    run_dir: Path,
) -> list[str]:
    errors: list[str] = []
    missing = sorted(WRITER_KEYS - writer.keys())
    extra = sorted(writer.keys() - WRITER_KEYS)
    if missing:
        errors.append(f"writer metadata missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"writer metadata has unsupported fields: {', '.join(extra)}")

    if writer.get("writer_version") != "wiki-writer.v1":
        errors.append("writer_version must be wiki-writer.v1")
    if not isinstance(writer.get("provider"), str) or not writer.get("provider"):
        errors.append("writer provider must be a non-empty string")
    if writer.get("source_path") != packet.get("source_path"):
        errors.append("writer source_path must match packet source_path")
    if writer.get("primary_home") != packet.get("primary_home"):
        errors.append("writer primary_home must match packet primary_home")
    if writer.get("writes_wiki") is not False:
        errors.append("writer must declare writes_wiki=false")
    if not isinstance(writer.get("provider_metadata"), dict):
        errors.append("writer provider_metadata must be an object")
    else:
        errors.extend(
            validate_visual_source_evidence(
                writer["provider_metadata"],
                "writer",
                visual_source_required(packet),
            )
        )

    draft_path = writer.get("draft_path")
    if not isinstance(draft_path, str) or not draft_path:
        errors.append("writer draft_path must be a non-empty string")
    elif not is_under(Path(draft_path), run_dir):
        errors.append(f"writer draft_path escaped run directory: {draft_path}")

    return errors


def validate_judge_contract(
    judge: dict[str, Any],
    writer: dict[str, Any],
    packet: dict[str, Any],
    expected_policy_status: str | None,
    expected_judge_decision: str | None,
) -> list[str]:
    errors: list[str] = []
    missing = sorted(JUDGE_KEYS - judge.keys())
    extra = sorted(judge.keys() - JUDGE_KEYS)
    if missing:
        errors.append(f"judge metadata missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"judge metadata has unsupported fields: {', '.join(extra)}")

    if judge.get("judge_version") != "wiki-judge.v1":
        errors.append("judge_version must be wiki-judge.v1")
    if not isinstance(judge.get("provider"), str) or not judge.get("provider"):
        errors.append("judge provider must be a non-empty string")
    if judge.get("decision") not in {"approve_for_review", "needs_revision", "reject"}:
        errors.append("judge decision is invalid")
    if expected_judge_decision is not None and judge.get("decision") != expected_judge_decision:
        errors.append(
            f"judge decision: expected {expected_judge_decision!r}, got {judge.get('decision')!r}",
        )
    if judge.get("policy_status") not in {"pass", "review", "reject", "unknown"}:
        errors.append("judge policy_status is invalid")
    if expected_policy_status is not None and judge.get("policy_status") != expected_policy_status:
        errors.append(
            f"judge policy_status: expected {expected_policy_status!r}, got {judge.get('policy_status')!r}",
        )
    if judge.get("writer_provider") != writer.get("provider"):
        errors.append("judge writer_provider must match writer provider")
    if judge.get("human_review_required") is not True:
        errors.append("judge must require human review")
    if judge.get("writes_wiki") is not False:
        errors.append("judge must declare writes_wiki=false")
    if not isinstance(judge.get("provider_metadata"), dict):
        errors.append("judge provider_metadata must be an object")
    else:
        scores = judge.get("scores")
        source_fidelity_claimed = (
            isinstance(scores, dict)
            and scores.get("source_fidelity") is not None
        )
        errors.extend(
            validate_visual_source_evidence(
                judge["provider_metadata"],
                "judge",
                visual_source_required(packet),
                source_fidelity_claimed=source_fidelity_claimed,
            )
        )

    scores = judge.get("scores")
    if not isinstance(scores, dict):
        errors.append("judge scores must be an object")
    else:
        missing_scores = sorted(JUDGE_SCORE_KEYS - scores.keys())
        extra_scores = sorted(scores.keys() - JUDGE_SCORE_KEYS)
        if missing_scores:
            errors.append(f"judge scores missing fields: {', '.join(missing_scores)}")
        if extra_scores:
            errors.append(f"judge scores has unsupported fields: {', '.join(extra_scores)}")
        for key, value in scores.items():
            if value is not None and not isinstance(value, (int, float)):
                errors.append(f"judge scores.{key} must be a number or null")

    findings = judge.get("findings")
    if not isinstance(findings, list):
        errors.append("judge findings must be a list")
    else:
        for index, finding in enumerate(findings):
            if not isinstance(finding, str):
                errors.append(f"judge findings[{index}] must be a string")

    return errors


def validate_draft_manifest(
    manifest: dict[str, Any],
    packet: dict[str, Any],
    run_dir: Path,
) -> list[str]:
    errors: list[str] = []
    missing = sorted(DRAFT_MANIFEST_KEYS - manifest.keys())
    extra = sorted(manifest.keys() - DRAFT_MANIFEST_KEYS)
    if missing:
        errors.append(f"draft manifest missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"draft manifest has unsupported fields: {', '.join(extra)}")

    if manifest.get("manifest_version") != "wiki-draft-manifest.v1":
        errors.append("draft manifest_version must be wiki-draft-manifest.v1")
    if manifest.get("source_path") != packet.get("source_path"):
        errors.append("draft manifest source_path must match packet source_path")
    if manifest.get("primary_home") != packet.get("primary_home"):
        errors.append("draft manifest primary_home must match packet primary_home")
    if manifest.get("writes_wiki") is not False:
        errors.append("draft manifest must declare writes_wiki=false")

    operations = manifest.get("operations")
    if not isinstance(operations, list):
        errors.append("draft manifest operations must be a list")
        return errors
    if not operations:
        errors.append("draft manifest operations must not be empty")
        return errors

    packet_targets = set(str(path) for path in packet.get("expected_touched_files", []))
    operation_targets: set[str] = set()
    draft_dir = run_dir / "draft"
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            errors.append(f"draft manifest operations[{index}] must be an object")
            continue
        missing_op = sorted(DRAFT_OPERATION_KEYS - operation.keys())
        extra_op = sorted(operation.keys() - DRAFT_OPERATION_KEYS)
        if missing_op:
            errors.append(f"draft manifest operations[{index}] missing fields: {', '.join(missing_op)}")
        if extra_op:
            errors.append(
                f"draft manifest operations[{index}] has unsupported fields: {', '.join(extra_op)}"
            )
        operation_op = operation.get("op")
        if operation_op not in DRAFT_OPS:
            errors.append(f"draft manifest operations[{index}].op is invalid")
        elif operation_op == "delete":
            errors.append("draft manifest delete operations are not allowed")
        if operation.get("status") not in DRAFT_STATUSES:
            errors.append(f"draft manifest operations[{index}].status is invalid")

        target_path = operation.get("target_path")
        if not isinstance(target_path, str):
            errors.append(f"draft manifest operations[{index}].target_path must be a string")
        elif target_path:
            if not target_path.startswith("wiki/"):
                errors.append(f"draft manifest operations[{index}].target_path must be under wiki/")
            if target_path in operation_targets:
                errors.append(f"draft manifest duplicate operation target: {target_path}")
            operation_targets.add(target_path)
        elif operation_op in DRAFT_WRITE_OPS:
            errors.append(f"draft manifest operations[{index}].target_path must be set for {operation_op}")

        draft_path = operation.get("draft_path")
        if draft_path is not None:
            if not isinstance(draft_path, str) or not draft_path:
                errors.append(f"draft manifest operations[{index}].draft_path must be a string or null")
            else:
                draft_file = Path(draft_path)
                if not is_under(draft_file, draft_dir):
                    errors.append(f"draft manifest operation draft_path must be under draft directory: {draft_path}")
                elif not draft_file.exists():
                    errors.append(f"draft manifest operation draft_path does not exist: {draft_path}")
        elif operation_op in DRAFT_WRITE_OPS:
            errors.append(f"draft manifest operations[{index}].draft_path must be set for {operation_op}")

    if packet_targets and operation_targets != packet_targets:
        errors.append("draft manifest operation targets must match packet expected_touched_files")
    if not packet_targets:
        has_no_op = any(operation.get("op") == "no_op" for operation in operations if isinstance(operation, dict))
        if not has_no_op:
            errors.append("draft manifest must include no_op when packet has no expected touched files")

    return errors


def validate_run_artifacts(
    run_dir: Path,
    expected_policy_status: str | None = None,
    expected_judge_decision: str | None = None,
    expected_drafts: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    expected_drafts = expected_drafts or []

    if not run_dir.exists():
        return [f"run directory does not exist: {run_dir}"]
    if not run_dir.is_dir():
        return [f"run path is not a directory: {run_dir}"]
    if not is_under(run_dir, RUNS_ROOT):
        errors.append(f"run directory must be under {RUNS_ROOT}: {run_dir}")

    for name in EXPECTED_ARTIFACTS:
        path = run_dir / name
        if not path.exists():
            errors.append(f"missing run artifact: {path}")
        elif not is_under(path, run_dir):
            errors.append(f"run artifact escaped run directory: {path}")
    for name in EXPECTED_DRAFT_ARTIFACTS:
        path = run_dir / name
        if not path.exists():
            errors.append(f"missing draft artifact: {path}")
        elif not is_under(path, run_dir):
            errors.append(f"draft artifact escaped run directory: {path}")

    draft_dir = run_dir / "draft"
    if not draft_dir.is_dir():
        errors.append(f"missing draft directory: {draft_dir}")
    elif not is_under(draft_dir, run_dir):
        errors.append(f"draft directory escaped run directory: {draft_dir}")

    for name in expected_drafts:
        path = run_dir / name
        if not path.exists():
            errors.append(f"missing draft artifact: {path}")
        elif not is_under(path, run_dir):
            errors.append(f"draft artifact escaped run directory: {path}")

    if errors:
        return errors

    packet = load_json(run_dir / "packet.json")
    policy = load_json(run_dir / "policy.json")
    writer = load_json(run_dir / "writer.json")
    judge = load_json(run_dir / "judge.json")
    manifest = load_json(run_dir / "draft" / "manifest.json")

    if packet.get("writes_files") is not False:
        errors.append("packet must declare writes_files=false")
    if expected_policy_status is not None and policy.get("status") != expected_policy_status:
        errors.append(
            f"policy status: expected {expected_policy_status!r}, got {policy.get('status')!r}",
        )
    if judge.get("policy_status") != policy.get("status"):
        errors.append("judge policy_status must match policy status")

    errors.extend(validate_writer_contract(writer, packet, run_dir))
    errors.extend(validate_draft_manifest(manifest, packet, run_dir))
    errors.extend(
        validate_judge_contract(
            judge,
            writer,
            packet,
            expected_policy_status,
            expected_judge_decision,
        ),
    )

    return errors


def run_fixture(fixture: dict[str, Any]) -> list[str]:
    fixture_id = str(fixture["id"])
    run_id = str(fixture.get("run_id") or f"eval-{fixture_id}")
    run_dir = RUNS_ROOT / run_id
    source_path = str(fixture["source_path"])
    target_slug = str(fixture.get("target_slug") or "")
    expected_policy_status = str(fixture["expected_policy_status"])
    expected_judge_decision = str(fixture["expected_judge_decision"])
    expected_drafts = [str(path) for path in fixture.get("expected_drafts", [])]
    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]

    before = git_status_wiki()
    shutil.rmtree(run_dir, ignore_errors=True)

    run_cmd = [
        sys.executable,
        "scripts/wiki_run.py",
        source_path,
        "--run-id",
        run_id,
    ]
    if target_slug:
        run_cmd.extend(["--target-slug", target_slug])

    commands = [
        run_cmd,
        [
            sys.executable,
            "scripts/wiki_writer.py",
            str(run_dir / "packet.json"),
            "--provider",
            "stub",
            "--overwrite",
        ],
        [
            sys.executable,
            "scripts/wiki_judge.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ],
    ]

    errors: list[str] = []
    for command in commands:
        result = run_command(command)
        if result.returncode != 0:
            errors.append(result.stderr.strip() or result.stdout.strip())
            return errors

    after = git_status_wiki()
    if before != after:
        errors.append("wiki/ git status changed during no-write run")

    errors.extend(apply_mutations(run_dir, mutations))

    if errors:
        return errors

    errors.extend(
        validate_run_artifacts(
            run_dir,
            expected_policy_status=expected_policy_status,
            expected_judge_decision=expected_judge_decision,
            expected_drafts=expected_drafts,
        )
    )

    return errors


def main() -> int:
    ensure_eval_sources()
    write_existing_source_page()
    args = parser().parse_args()
    fixture_dir = Path(args.fixture_dir)
    fixture_paths = sorted(fixture_dir.glob("*.json"))
    if not fixture_paths:
        print(f"No fixtures found in {fixture_dir}", file=sys.stderr)
        return 2

    failures = 0
    for path in fixture_paths:
        fixture = load_fixture(path)
        fixture_id = fixture.get("id", path.stem)
        errors = run_fixture(fixture)
        expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
        if expected_errors:
            missing_errors = [
                expected
                for expected in expected_errors
                if not any(expected in error for error in errors)
            ]
            if missing_errors:
                failures += 1
                print(f"FAIL {fixture_id}")
                for error in missing_errors:
                    print(f"  - missing expected error: {error}")
                if errors:
                    print("  observed errors:")
                    for error in errors:
                        print(f"    - {error}")
            else:
                print(f"PASS {fixture_id}")
        elif errors:
            failures += 1
            print(f"FAIL {fixture_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {fixture_id}")

    print(f"\nSummary: {len(fixture_paths) - failures} passed, {failures} failed")
    remove_existing_source_page()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
