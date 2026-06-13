#!/usr/bin/env python3
"""Route a wiki work cluster after deterministic dry-run policy checks.

The route policy is the ingest front door:

    pass + ordinary ingest -> direct_edit
    review or non-ingest -> full_harness
    reject -> blocked

It does not write files. It either runs dry-run + diff policy from a source path,
or evaluates existing packet/policy artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DRY_RUN = Path("scripts/wiki_dry_run.py")
DIFF_POLICY = Path("scripts/wiki_diff_policy.py")
TASK_TYPES = {"ingest", "promotion_audit", "lint_followup", "research_capture"}
ROUTES = {"direct_edit", "full_harness", "blocked"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Route a wiki work cluster after dry-run policy checks.")
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("source_path", nargs="?", help="Path to a raw source artifact.")
    source.add_argument("--packet", help="Existing dry-run packet JSON path.")
    p.add_argument("--policy", help="Existing diff-policy JSON path. Required with --packet.")
    p.add_argument(
        "--task-type",
        choices=sorted(TASK_TYPES),
        default="ingest",
        help="Dry-run task route when source_path is used.",
    )
    p.add_argument("--target-slug", default="", help="Override inferred source page slug.")
    p.add_argument("--max-wiki-pages", type=int, default=8)
    p.add_argument("--allow-core-edits", action="store_true")
    return p


def run_command(command: list[str], allowed_codes: set[int] | None = None) -> subprocess.CompletedProcess[str]:
    allowed = allowed_codes or {0}
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in allowed:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or f"{command[0]} exited {result.returncode}")
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def run_dry_run(args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable,
        str(DRY_RUN),
        str(args.source_path),
        "--task-type",
        args.task_type,
        "--format",
        "json",
        "--validate-schema",
    ]
    if args.target_slug:
        command.extend(["--target-slug", args.target_slug])
    result = run_command(command)
    return json.loads(result.stdout)


def run_diff_policy(
    packet: dict[str, Any],
    max_wiki_pages: int,
    allow_core_edits: bool,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as f:
        json.dump(packet, f)
        f.flush()
        command = [
            sys.executable,
            str(DIFF_POLICY),
            f.name,
            "--max-wiki-pages",
            str(max_wiki_pages),
        ]
        if allow_core_edits:
            command.append("--allow-core-edits")
        result = run_command(command, allowed_codes={0, 2})
    return json.loads(result.stdout)


def route_packet(packet: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    status = str(policy.get("status", "unknown"))
    task_type = str(packet.get("task_type", ""))
    triggers: list[str] = []
    next_steps: list[str] = []
    human_review_required = True

    if status == "reject":
        route = "blocked"
        triggers.extend(str(item) for item in policy.get("rejects", []) if isinstance(item, str))
        next_steps.extend(
            [
                "Do not write durable wiki files.",
                "Fix the rejected packet condition or ask the user to choose a different route.",
            ]
        )
    elif status == "review":
        route = "full_harness"
        triggers.extend(str(item) for item in policy.get("reviews", []) if isinstance(item, str))
        next_steps.extend(
            [
                "Run the full no-write harness with scripts/wiki_pipeline.py.",
                "Inspect the run artifacts before any durable wiki edit.",
            ]
        )
    elif task_type != "ingest":
        route = "full_harness"
        triggers.append(f"non-ingest task type requires full harness: {task_type or 'unknown'}")
        next_steps.extend(
            [
                "Run the full no-write harness with scripts/wiki_pipeline.py.",
                "Use the task-specific workflow before durable writes.",
            ]
        )
    elif status == "pass":
        route = "direct_edit"
        human_review_required = False
        triggers.append("ordinary ingest passed deterministic diff policy")
        next_steps.extend(
            [
                "Proceed with the normal ingest workflow.",
                "Run rebuild_referenced_by.py, lint.py --tier1, and git diff --check before commit.",
            ]
        )
    else:
        route = "blocked"
        triggers.append(f"unknown diff-policy status: {status}")
        next_steps.append("Do not write durable wiki files until the policy status is understood.")

    return {
        "route_policy_version": "wiki-route-policy.v1",
        "route": route,
        "task_type": task_type,
        "source_path": packet.get("source_path"),
        "policy_status": status,
        "triggers": triggers,
        "next_steps": next_steps,
        "human_review_required": human_review_required,
        "writes_files": False,
    }


def load_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if args.packet:
        if not args.policy:
            raise ValueError("--policy is required when --packet is used")
        return load_json(Path(args.packet)), load_json(Path(args.policy))

    packet = run_dry_run(args)
    policy = run_diff_policy(
        packet,
        max_wiki_pages=args.max_wiki_pages,
        allow_core_edits=args.allow_core_edits,
    )
    return packet, policy


def main() -> int:
    args = parser().parse_args()
    packet, policy = load_inputs(args)
    report = route_packet(packet, policy)
    print(json.dumps(report, indent=2) + "\n")
    return 2 if report["route"] == "blocked" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_route_policy error: {exc}", file=sys.stderr)
        sys.exit(1)
