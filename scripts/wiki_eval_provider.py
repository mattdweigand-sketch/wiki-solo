#!/usr/bin/env python3
"""Evaluate provider readiness for the current no-write stub providers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from wiki_eval_sources import ensure_eval_sources
from typing import Any

from wiki_provider_readiness import (
    RUNS_ROOT,
    validate_provider_artifacts,
)
from wiki_validate_provider_manifest import (
    MANIFEST_PATH,
    validate_manifest,
)


SOURCE = "raw/ai-research/folder-organization-guide.md"
RUN_ID = "eval-provider-readiness"
PROVIDER_FIXTURE_DIR = Path("tests/fixtures/wiki-provider")
PROVIDER_MANIFEST_FIXTURE_DIR = Path("tests/fixtures/wiki-provider-manifest")


def run_command(command: list[str], allowed: set[int] | None = None) -> subprocess.CompletedProcess[str]:
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


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


def delete_nested(value: dict[str, Any], key_path: list[str]) -> None:
    current: Any = value
    for key in key_path[:-1]:
        if not isinstance(current, dict):
            return
        current = current.get(key)
    if isinstance(current, dict):
        current.pop(key_path[-1], None)


def create_ready_run(run_id: str, source_path: str) -> Path:
    run_command(
        [
            sys.executable,
            "scripts/wiki_provider_readiness.py",
            source_path,
            "--run-id",
            run_id,
            "--overwrite",
        ],
    )
    return RUNS_ROOT / run_id


def apply_mutations(run_dir: Path, mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    allowed_artifacts = {
        "evidence.json",
        "classifier.json",
        "contradictions.json",
        "links.json",
        "writer.json",
        "judge.json",
        "draft/manifest.json",
        "apply-plan.json",
    }
    for index, mutation in enumerate(mutations):
        artifact = mutation.get("artifact")
        if artifact not in allowed_artifacts:
            errors.append(f"mutation[{index}] artifact is not provider-owned: {artifact}")
            continue
        path = run_dir / str(artifact)
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


def semantic_errors(run_dir: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_semantic.py", str(run_dir)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = result.stderr.strip() or result.stdout.strip()
    return output.splitlines()


def run_errors(run_dir: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_run.py", str(run_dir)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = result.stderr.strip() or result.stdout.strip()
    return output.splitlines()


def apply_plan_errors(run_dir: Path) -> list[str]:
    result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_apply_plan.py", str(run_dir / "apply-plan.json")],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return []
    output = result.stderr.strip() or result.stdout.strip()
    return output.splitlines()


def run_negative_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    run_id = str(fixture.get("run_id") or f"eval-{fixture.get('id', path.stem)}")
    source_path = str(fixture.get("source_path") or SOURCE)
    run_dir = create_ready_run(run_id, source_path)

    for artifact in fixture.get("delete_artifacts", []):
        if not isinstance(artifact, str):
            return ["delete_artifacts entries must be strings"]
        path_to_delete = run_dir / artifact
        if path_to_delete.exists():
            path_to_delete.unlink()

    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]
    errors = apply_mutations(run_dir, mutations)
    if errors:
        return errors

    observed_errors = []
    observed_errors.extend(semantic_errors(run_dir))
    observed_errors.extend(run_errors(run_dir))
    observed_errors.extend(apply_plan_errors(run_dir))
    observed_errors.extend(
        validate_provider_artifacts(
            run_dir,
            semantic_provider="stub",
            writer_provider="stub",
            judge_provider="stub",
        )
    )

    output = "\n".join(observed_errors)
    expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
    if not expected_errors:
        return observed_errors
    if not observed_errors:
        return ["provider readiness fixture unexpectedly passed"]
    return [f"missing expected error: {error}" for error in expected_errors if error not in output]


def run_negative_fixtures() -> list[str]:
    if not PROVIDER_FIXTURE_DIR.exists():
        return [f"missing provider fixture dir: {PROVIDER_FIXTURE_DIR}"]
    fixture_paths = sorted(PROVIDER_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        return [f"no provider fixtures found in {PROVIDER_FIXTURE_DIR}"]

    errors: list[str] = []
    for path in fixture_paths:
        try:
            fixture_errors = run_negative_fixture(path)
        except Exception as exc:
            fixture_errors = [str(exc)]
        if fixture_errors:
            errors.extend(f"{path.stem}: {error}" for error in fixture_errors)
    return errors


def apply_manifest_mutations(manifest: dict[str, Any], mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, mutation in enumerate(mutations):
        for key_path in mutation.get("delete", []):
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"manifest mutation[{index}] delete path must be a list of strings")
                continue
            delete_nested(manifest, key_path)
        for change in mutation.get("set", []):
            key_path = change.get("path") if isinstance(change, dict) else None
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"manifest mutation[{index}] set path must be a list of strings")
                continue
            set_nested(manifest, key_path, change.get("value"))
    return errors


def run_manifest_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    manifest = load_json(MANIFEST_PATH)
    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]

    errors = apply_manifest_mutations(manifest, mutations)
    if errors:
        return errors

    observed_errors = validate_manifest(manifest)
    if not observed_errors:
        return ["provider manifest fixture unexpectedly passed"]

    output = "\n".join(observed_errors)
    expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
    return [f"missing expected error: {error}" for error in expected_errors if error not in output]


def run_manifest_fixtures() -> list[str]:
    if not PROVIDER_MANIFEST_FIXTURE_DIR.exists():
        return [f"missing provider manifest fixture dir: {PROVIDER_MANIFEST_FIXTURE_DIR}"]
    fixture_paths = sorted(PROVIDER_MANIFEST_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        return [f"no provider manifest fixtures found in {PROVIDER_MANIFEST_FIXTURE_DIR}"]

    errors: list[str] = []
    for path in fixture_paths:
        try:
            fixture_errors = run_manifest_fixture(path)
        except Exception as exc:
            fixture_errors = [str(exc)]
        if fixture_errors:
            errors.extend(f"{path.stem}: {error}" for error in fixture_errors)
    return errors


def main() -> int:
    ensure_eval_sources()
    manifest_result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_provider_manifest.py"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if manifest_result.returncode != 0:
        print("FAIL wiki-provider")
        output = manifest_result.stderr.strip() or manifest_result.stdout.strip()
        if output:
            for line in output.splitlines():
                print(f"  - {line}")
        return 1

    manifest_fixture_errors = run_manifest_fixtures()
    if manifest_fixture_errors:
        print("FAIL wiki-provider")
        for error in manifest_fixture_errors:
            print(f"  - {error}")
        return 1

    result = subprocess.run(
        [
            sys.executable,
            "scripts/wiki_provider_readiness.py",
            SOURCE,
            "--run-id",
            RUN_ID,
            "--overwrite",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        print("FAIL wiki-provider")
        output = result.stderr.strip() or result.stdout.strip()
        if output:
            for line in output.splitlines():
                print(f"  - {line}")
        return 1

    fixture_errors = run_negative_fixtures()
    if fixture_errors:
        print("FAIL wiki-provider")
        for error in fixture_errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-provider")
    return 0


if __name__ == "__main__":
    sys.exit(main())
