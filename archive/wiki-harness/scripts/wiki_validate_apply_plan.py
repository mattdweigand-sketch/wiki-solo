#!/usr/bin/env python3
"""Validate a no-write wiki apply plan JSON artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


APPLY_PLAN_KEYS = {
    "apply_plan_version",
    "run_dir",
    "status",
    "required_approval",
    "target_files",
    "operations",
    "blockers",
    "review_reasons",
    "writes_wiki",
}
OPERATION_KEYS = {"op", "target_path", "draft_path", "status"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate a wiki apply plan JSON artifact.")
    p.add_argument("plan_path", help="Path to an apply plan JSON file, or '-' for stdin.")
    return p


def load_plan(path_text: str) -> dict[str, Any]:
    if path_text == "-":
        return json.loads(sys.stdin.read())
    path = Path(path_text)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_apply_plan(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(APPLY_PLAN_KEYS - plan.keys())
    extra = sorted(plan.keys() - APPLY_PLAN_KEYS)
    if missing:
        errors.append(f"apply plan missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"apply plan has unsupported fields: {', '.join(extra)}")

    if plan.get("apply_plan_version") != "wiki-apply-plan.v1":
        errors.append("apply_plan_version must be wiki-apply-plan.v1")
    if not isinstance(plan.get("run_dir"), str) or not plan.get("run_dir"):
        errors.append("apply plan run_dir must be a non-empty string")
    if plan.get("status") not in {"blocked", "ready_for_approval"}:
        errors.append("apply plan status is invalid")
    if plan.get("required_approval") is not True:
        errors.append("apply plan must require approval")
    if plan.get("writes_wiki") is not False:
        errors.append("apply plan must declare writes_wiki=false")

    for key in ("target_files", "blockers", "review_reasons"):
        value = plan.get(key)
        if not isinstance(value, list):
            errors.append(f"apply plan {key} must be a list")
            continue
        for index, item in enumerate(value):
            if not isinstance(item, str):
                errors.append(f"apply plan {key}[{index}] must be a string")
        if key == "target_files" and len(value) != len(set(value)):
            errors.append("apply plan target_files must not contain duplicates")

    operations = plan.get("operations")
    operation_targets: list[str] = []
    if not isinstance(operations, list):
        errors.append("apply plan operations must be a list")
    else:
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                errors.append(f"apply plan operations[{index}] must be an object")
                continue
            missing_op = sorted(OPERATION_KEYS - operation.keys())
            extra_op = sorted(operation.keys() - OPERATION_KEYS)
            if missing_op:
                errors.append(f"apply plan operations[{index}] missing fields: {', '.join(missing_op)}")
            if extra_op:
                errors.append(f"apply plan operations[{index}] has unsupported fields: {', '.join(extra_op)}")
            if operation.get("op") not in {"create", "update", "delete", "no_op", None}:
                errors.append(f"apply plan operations[{index}].op is invalid")
            if operation.get("status") not in {"stub", "drafted", "ready", "blocked", None}:
                errors.append(f"apply plan operations[{index}].status is invalid")
            for key in ("target_path", "draft_path"):
                if operation.get(key) is not None and not isinstance(operation.get(key), str):
                    errors.append(f"apply plan operations[{index}].{key} must be a string or null")
            target_path = operation.get("target_path")
            if isinstance(target_path, str) and target_path:
                if target_path in operation_targets:
                    errors.append(f"apply plan duplicate operation target: {target_path}")
                operation_targets.append(target_path)

    if plan.get("status") == "blocked" and not plan.get("blockers"):
        errors.append("blocked apply plan must include at least one blocker")
    target_files = plan.get("target_files")
    if isinstance(target_files, list) and all(isinstance(item, str) for item in target_files):
        if sorted(target_files) != sorted(operation_targets):
            errors.append("apply plan target_files must match operation target paths")
    return errors


def main() -> int:
    args = parser().parse_args()
    try:
        plan = load_plan(args.plan_path)
    except Exception as exc:
        print(f"wiki_validate_apply_plan error: {exc}", file=sys.stderr)
        return 1

    errors = validate_apply_plan(plan)
    if errors:
        print("FAIL wiki-apply-plan-contract")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-apply-plan-contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
