#!/usr/bin/env python3
"""Emit a no-write apply plan for a completed wiki run.

The apply plan is an inspection artifact. It validates an existing run,
summarizes the boundary status, and maps draft manifest operations into a
machine-readable plan. It never writes under wiki/.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from wiki_apply import check_boundary


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Emit a no-write wiki apply plan as JSON.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def manifest_operations(run_dir: Path) -> list[dict[str, Any]]:
    manifest_path = run_dir / "draft" / "manifest.json"
    if not manifest_path.exists():
        return []

    manifest = load_json(manifest_path)
    operations = manifest.get("operations", [])
    if not isinstance(operations, list):
        return []

    plan_operations: list[dict[str, Any]] = []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        plan_operations.append(
            {
                "op": operation.get("op"),
                "target_path": operation.get("target_path"),
                "draft_path": operation.get("draft_path"),
                "status": operation.get("status"),
            }
        )
    return plan_operations


def build_apply_plan(run_dir: Path) -> dict[str, Any]:
    blockers, review_reasons, summary = check_boundary(run_dir)
    operations = manifest_operations(run_dir)
    target_files = [str(operation["target_path"]) for operation in operations if operation.get("target_path")]

    return {
        "apply_plan_version": "wiki-apply-plan.v1",
        "run_dir": str(run_dir),
        "status": "blocked" if blockers else "ready_for_approval",
        "required_approval": True,
        "target_files": target_files,
        "operations": operations,
        "blockers": blockers,
        "review_reasons": review_reasons,
        "writes_wiki": False,
    }


def main() -> int:
    args = parser().parse_args()
    run_dir = Path(args.run_dir)
    plan = build_apply_plan(run_dir)
    print(json.dumps(plan, indent=2))
    return 2 if plan["blockers"] else 0


if __name__ == "__main__":
    sys.exit(main())
