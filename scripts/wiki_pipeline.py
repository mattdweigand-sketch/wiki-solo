#!/usr/bin/env python3
"""Run the full no-write wiki harness pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


RUNS_ROOT = Path("tmp/wiki-runs")
PIPELINE_ARTIFACTS = [
    "packet.json",
    "review.md",
    "policy.json",
    "evidence.json",
    "classifier.json",
    "contradictions.json",
    "links.json",
    "writer.json",
    "judge.json",
    "pipeline.json",
    "apply-plan.json",
    "draft/README.md",
    "draft/manifest.json",
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the full no-write wiki harness pipeline.")
    p.add_argument("source_path", help="Path to a raw source artifact.")
    p.add_argument(
        "--task-type",
        choices=["ingest", "promotion_audit", "lint_followup", "research_capture"],
        default="ingest",
    )
    p.add_argument("--target-slug", default="")
    p.add_argument("--run-id", default="")
    p.add_argument("--runs-root", default=str(RUNS_ROOT))
    p.add_argument("--max-wiki-pages", type=int, default=8)
    p.add_argument("--allow-core-edits", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    return p


def slug(text: str) -> str:
    value = text.lower()
    value = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "run"


def default_run_id(source_path: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{slug(Path(source_path).stem)}"


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


def read_policy_status(run_dir: Path) -> str:
    with (run_dir / "policy.json").open(encoding="utf-8") as f:
        policy = json.load(f)
    return str(policy.get("status", "unknown"))


def write_apply_plan(run_dir: Path) -> str:
    result = run_command(
        [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
        allowed={0, 2},
    )
    plan_path = run_dir / "apply-plan.json"
    plan_path.write_text(result.stdout, encoding="utf-8")
    run_command([sys.executable, "scripts/wiki_validate_apply_plan.py", str(plan_path)])
    return str(plan_path)


def write_pipeline_artifact(
    run_dir: Path,
    source_path: str,
    task_type: str,
) -> str:
    packet_path = run_dir / "packet.json"
    target_slug = ""
    if packet_path.exists():
        with packet_path.open(encoding="utf-8") as f:
            packet = json.load(f)
        target_slug = str(packet.get("target_slug", ""))

    artifacts = list(PIPELINE_ARTIFACTS)
    if target_slug:
        artifacts.append(f"draft/{target_slug}.md.stub")

    artifact = {
        "pipeline_version": "wiki-pipeline.v1",
        "run_dir": str(run_dir),
        "source_path": source_path,
        "task_type": task_type,
        "providers": {
            "semantic": "stub",
            "writer": "stub",
            "judge": "stub",
        },
        "artifacts": artifacts,
        "writes_wiki": False,
    }
    output_path = run_dir / "pipeline.json"
    output_path.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return str(output_path)


def main() -> int:
    args = parser().parse_args()
    run_id = args.run_id or default_run_id(args.source_path)
    run_dir = Path(args.runs_root) / run_id

    run_cmd = [
        sys.executable,
        "scripts/wiki_run.py",
        args.source_path,
        "--task-type",
        args.task_type,
        "--run-id",
        run_id,
        "--runs-root",
        args.runs_root,
        "--max-wiki-pages",
        str(args.max_wiki_pages),
    ]
    if args.target_slug:
        run_cmd.extend(["--target-slug", args.target_slug])
    if args.allow_core_edits:
        run_cmd.append("--allow-core-edits")
    if args.overwrite:
        run_cmd.append("--overwrite")

    commands = [
        run_cmd,
        [
            sys.executable,
            "scripts/wiki_semantic.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ],
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
        [sys.executable, "scripts/wiki_validate_run.py", str(run_dir)],
        [sys.executable, "scripts/wiki_validate_semantic.py", str(run_dir)],
    ]

    try:
        for command in commands:
            run_command(command)
        plan_path = write_apply_plan(run_dir)
        pipeline_path = write_pipeline_artifact(run_dir, args.source_path, args.task_type)
        run_command([sys.executable, "scripts/wiki_validate_pipeline.py", pipeline_path])
    except Exception as exc:
        print(f"wiki_pipeline error: {exc}", file=sys.stderr)
        return 1

    print(f"Run directory: {run_dir}")
    print(f"Policy status: {read_policy_status(run_dir)}")
    print(f"Apply plan: {plan_path}")
    print(f"Pipeline artifact: {pipeline_path}")
    print("No durable files were written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
