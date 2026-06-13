#!/usr/bin/env python3
"""Validate a no-write wiki pipeline artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PIPELINE_KEYS = {
    "pipeline_version",
    "run_dir",
    "source_path",
    "task_type",
    "providers",
    "artifacts",
    "writes_wiki",
}
PROVIDER_KEYS = {"semantic", "writer", "judge"}
TASK_TYPES = {"ingest", "promotion_audit", "lint_followup", "research_capture"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate a wiki pipeline artifact JSON file.")
    p.add_argument("pipeline_path", help="Path to tmp/wiki-runs/<run-id>/pipeline.json.")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_pipeline_artifact(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(PIPELINE_KEYS - artifact.keys())
    extra = sorted(artifact.keys() - PIPELINE_KEYS)
    if missing:
        errors.append(f"pipeline artifact missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"pipeline artifact has unsupported fields: {', '.join(extra)}")

    if artifact.get("pipeline_version") != "wiki-pipeline.v1":
        errors.append("pipeline_version must be wiki-pipeline.v1")
    if not isinstance(artifact.get("run_dir"), str) or not artifact.get("run_dir"):
        errors.append("pipeline run_dir must be a non-empty string")
    if not isinstance(artifact.get("source_path"), str) or not artifact.get("source_path"):
        errors.append("pipeline source_path must be a non-empty string")
    if artifact.get("task_type") not in TASK_TYPES:
        errors.append("pipeline task_type is invalid")
    if artifact.get("writes_wiki") is not False:
        errors.append("pipeline artifact must declare writes_wiki=false")

    providers = artifact.get("providers")
    if not isinstance(providers, dict):
        errors.append("pipeline providers must be an object")
    else:
        missing_providers = sorted(PROVIDER_KEYS - providers.keys())
        extra_providers = sorted(providers.keys() - PROVIDER_KEYS)
        if missing_providers:
            errors.append(f"pipeline providers missing fields: {', '.join(missing_providers)}")
        if extra_providers:
            errors.append(f"pipeline providers has unsupported fields: {', '.join(extra_providers)}")
        for key in PROVIDER_KEYS:
            if providers.get(key) != "stub":
                errors.append(f"pipeline providers.{key} must be stub")

    artifacts = artifact.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("pipeline artifacts must be a list")
    else:
        for index, item in enumerate(artifacts):
            if not isinstance(item, str) or not item:
                errors.append(f"pipeline artifacts[{index}] must be a non-empty string")
        if len(artifacts) != len(set(artifacts)):
            errors.append("pipeline artifacts must not contain duplicates")

    return errors


def validate_pipeline_file(path: Path) -> list[str]:
    artifact = load_json(path)
    errors = validate_pipeline_artifact(artifact)
    run_dir = Path(str(artifact.get("run_dir", "")))
    if path.name != "pipeline.json":
        errors.append("pipeline artifact file must be named pipeline.json")
    if run_dir and path.parent != run_dir:
        errors.append("pipeline artifact must live directly under its run_dir")
    for artifact_path in artifact.get("artifacts", []):
        if isinstance(artifact_path, str) and artifact_path:
            target = run_dir / artifact_path
            if not target.exists():
                errors.append(f"pipeline listed artifact is missing: {target}")
    return errors


def main() -> int:
    args = parser().parse_args()
    try:
        errors = validate_pipeline_file(Path(args.pipeline_path))
    except Exception as exc:
        print(f"wiki_validate_pipeline error: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("FAIL wiki-pipeline-contract")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-pipeline-contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
