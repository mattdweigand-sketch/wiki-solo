#!/usr/bin/env python3
"""Smoke-test the full no-write wiki harness pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from wiki_eval_sources import ensure_eval_sources


RUN_ID = "eval-pipeline-stub"
RUN_DIR = Path("tmp/wiki-runs") / RUN_ID
SOURCE = "raw/ai-research/folder-organization-guide.md"
PIPELINE_FIXTURE_DIR = Path("tests/fixtures/wiki-pipeline")
APPLY_PLAN_SCHEMA = Path("schemas/wiki-apply-plan.schema.json")
PIPELINE_SCHEMA = Path("schemas/wiki-pipeline-artifact.schema.json")
EXPECTED_ARTIFACTS = [
    "packet.json",
    "review.md",
    "policy.json",
    "classifier.json",
    "contradictions.json",
    "links.json",
    "writer.json",
    "judge.json",
    "pipeline.json",
    "apply-plan.json",
    "draft/README.md",
    "draft/manifest.json",
    "draft/folder-organization-guide.md.stub",
]


def run_command(
    command: list[str],
    allowed: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    allowed_codes = allowed or {0}
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in allowed_codes:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or f"{command[0]} exited {result.returncode}")
    return result


def git_status_wiki() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no", "wiki"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def validate_artifacts() -> list[str]:
    errors: list[str] = []
    for artifact in EXPECTED_ARTIFACTS:
        path = RUN_DIR / artifact
        if not path.exists():
            errors.append(f"missing pipeline artifact: {path}")
    return errors


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def set_nested(value: dict, key_path: list[str], replacement) -> None:
    current = value
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


def apply_pipeline_mutations(run_dir: Path, mutations: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, mutation in enumerate(mutations):
        artifact = mutation.get("artifact")
        if artifact != "pipeline.json":
            errors.append(f"mutation[{index}] artifact must be pipeline.json")
            continue
        path = run_dir / artifact
        if not path.exists():
            errors.append(f"mutation[{index}] target does not exist: {path}")
            continue
        value = load_json(path)
        for change in mutation.get("set", []):
            key_path = change.get("path") if isinstance(change, dict) else None
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"mutation[{index}] set path must be a list of strings")
                continue
            set_nested(value, key_path, change.get("value"))
        write_json(path, value)
    return errors


def run_pipeline_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    fixture_id = str(fixture.get("id", path.stem))
    run_id = str(fixture.get("run_id") or f"eval-{fixture_id}")
    run_dir = Path("tmp/wiki-runs") / run_id
    source_path = str(fixture.get("source_path") or SOURCE)

    shutil.rmtree(run_dir, ignore_errors=True)
    run_command(
        [
            sys.executable,
            "scripts/wiki_pipeline.py",
            source_path,
            "--run-id",
            run_id,
            "--overwrite",
        ]
    )

    errors = apply_pipeline_mutations(run_dir, fixture.get("mutations", []))
    if errors:
        return errors

    pipeline_path = Path(str(fixture.get("pipeline_path") or run_dir / "pipeline.json"))
    if pipeline_path != run_dir / "pipeline.json":
        pipeline_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(run_dir / "pipeline.json", pipeline_path)

    result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_pipeline.py", str(pipeline_path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return ["pipeline validator unexpectedly passed"]

    output = result.stderr.strip() or result.stdout.strip()
    expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
    missing_errors = [
        expected for expected in expected_errors if expected not in output
    ]
    return [f"missing expected error: {error}" for error in missing_errors]


def validate_pipeline_fixtures() -> list[str]:
    if not PIPELINE_FIXTURE_DIR.exists():
        return [f"missing pipeline fixture dir: {PIPELINE_FIXTURE_DIR}"]
    fixture_paths = sorted(PIPELINE_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        return [f"no pipeline fixtures found in {PIPELINE_FIXTURE_DIR}"]

    errors: list[str] = []
    for path in fixture_paths:
        fixture_errors = run_pipeline_fixture(path)
        if fixture_errors:
            errors.extend(f"{path.stem}: {error}" for error in fixture_errors)
    return errors


def validate_apply_plan(output: str) -> list[str]:
    errors: list[str] = []
    if not APPLY_PLAN_SCHEMA.exists():
        errors.append(f"missing apply plan schema: {APPLY_PLAN_SCHEMA}")
    else:
        try:
            json.loads(APPLY_PLAN_SCHEMA.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"apply plan schema is invalid JSON: {exc}")

    try:
        plan = json.loads(output)
    except json.JSONDecodeError as exc:
        return [f"apply plan output must be JSON: {exc}"]

    if plan.get("apply_plan_version") != "wiki-apply-plan.v1":
        errors.append("apply plan version is invalid")
    if plan.get("writes_wiki") is not False:
        errors.append("apply plan must declare writes_wiki=false")
    if plan.get("status") not in {"blocked", "ready_for_approval"}:
        errors.append("apply plan status is invalid")
    if plan.get("required_approval") is not True:
        errors.append("apply plan must require approval")
    if not isinstance(plan.get("operations"), list):
        errors.append("apply plan operations must be a list")
    validator = subprocess.run(
        [sys.executable, "scripts/wiki_validate_apply_plan.py", "-"],
        input=output,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if validator.returncode != 0:
        errors.append(validator.stderr.strip() or validator.stdout.strip())
    return errors


def validate_pipeline_artifact() -> list[str]:
    errors: list[str] = []
    if not PIPELINE_SCHEMA.exists():
        errors.append(f"missing pipeline schema: {PIPELINE_SCHEMA}")
    else:
        try:
            json.loads(PIPELINE_SCHEMA.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"pipeline schema is invalid JSON: {exc}")

    try:
        artifact = json.loads((RUN_DIR / "pipeline.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return errors + [f"pipeline artifact must be JSON: {exc}"]

    if artifact.get("pipeline_version") != "wiki-pipeline.v1":
        errors.append("pipeline artifact version is invalid")
    if artifact.get("run_dir") != str(RUN_DIR):
        errors.append("pipeline artifact run_dir must match eval run")
    if artifact.get("source_path") != SOURCE:
        errors.append("pipeline artifact source_path must match eval source")
    if artifact.get("task_type") != "ingest":
        errors.append("pipeline artifact task_type must be ingest")
    if artifact.get("writes_wiki") is not False:
        errors.append("pipeline artifact must declare writes_wiki=false")
    providers = artifact.get("providers")
    if providers != {"semantic": "stub", "writer": "stub", "judge": "stub"}:
        errors.append("pipeline artifact providers must be stub")
    artifact_paths = artifact.get("artifacts")
    if not isinstance(artifact_paths, list):
        errors.append("pipeline artifact artifacts must be a list")
    else:
        for expected in EXPECTED_ARTIFACTS:
            if expected not in artifact_paths:
                errors.append(f"pipeline artifact must list {expected}")
    return errors


def main() -> int:
    ensure_eval_sources()
    before = git_status_wiki()
    shutil.rmtree(RUN_DIR, ignore_errors=True)
    errors: list[str] = []

    commands = [
        [
            sys.executable,
            "scripts/wiki_pipeline.py",
            SOURCE,
            "--run-id",
            RUN_ID,
            "--overwrite",
        ],
    ]

    try:
        for command in commands:
            run_command(command)
        plan_result = run_command([sys.executable, "scripts/wiki_validate_apply_plan.py", str(RUN_DIR / "apply-plan.json")])
        run_command([sys.executable, "scripts/wiki_validate_pipeline.py", str(RUN_DIR / "pipeline.json")])
    except Exception as exc:
        errors.append(str(exc))
        plan_result = None

    errors.extend(validate_artifacts())
    errors.extend(validate_pipeline_artifact())
    errors.extend(validate_pipeline_fixtures())
    if plan_result is not None:
        errors.extend(validate_apply_plan((RUN_DIR / "apply-plan.json").read_text(encoding="utf-8")))

    after = git_status_wiki()
    if before != after:
        errors.append("wiki/ git status changed during pipeline eval")

    if errors:
        print("FAIL wiki-pipeline")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
