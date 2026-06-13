#!/usr/bin/env python3
"""Create no-write wiki run artifacts under tmp/wiki-runs/.

The run wrapper composes the deterministic dry-run and policy scripts, then
writes reviewable artifacts outside wiki/:

    tmp/wiki-runs/<run-id>/packet.json
    tmp/wiki-runs/<run-id>/review.md
    tmp/wiki-runs/<run-id>/policy.json
    tmp/wiki-runs/<run-id>/draft/
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


RUNS_ROOT = Path("tmp/wiki-runs")
DRY_RUN = Path("scripts/wiki_dry_run.py")
POLICY = Path("scripts/wiki_diff_policy.py")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create no-write wiki run artifacts.")
    p.add_argument("source_path", help="Path to a raw source artifact.")
    p.add_argument(
        "--task-type",
        choices=["ingest", "promotion_audit", "lint_followup", "research_capture"],
        default="ingest",
        help="Dry-run task route.",
    )
    p.add_argument("--target-slug", default="", help="Override inferred source page slug.")
    p.add_argument("--run-id", default="", help="Run id. Defaults to timestamp plus source stem.")
    p.add_argument("--runs-root", default=str(RUNS_ROOT), help="Directory for run artifacts.")
    p.add_argument("--max-wiki-pages", type=int, default=8)
    p.add_argument("--allow-core-edits", action="store_true")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing run directory with the same run id.",
    )
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


def dry_run_command(args: argparse.Namespace, output_format: str) -> list[str]:
    command = [
        sys.executable,
        str(DRY_RUN),
        args.source_path,
        "--task-type",
        args.task_type,
        "--format",
        output_format,
        "--validate-schema",
    ]
    if args.target_slug:
        command.extend(["--target-slug", args.target_slug])
    return command


def policy_command(packet_path: Path, args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(POLICY),
        str(packet_path),
        "--max-wiki-pages",
        str(args.max_wiki_pages),
    ]
    if args.allow_core_edits:
        command.append("--allow-core-edits")
    return command


def main() -> int:
    args = parser().parse_args()
    run_id = args.run_id or default_run_id(args.source_path)
    run_dir = Path(args.runs_root) / run_id

    if run_dir.exists():
        if not args.overwrite:
            print(f"Run directory already exists: {run_dir}", file=sys.stderr)
            return 2
        shutil.rmtree(run_dir)

    run_dir.mkdir(parents=True)
    draft_dir = run_dir / "draft"
    draft_dir.mkdir()

    try:
        packet_result = run_command(dry_run_command(args, "json"))
        packet = json.loads(packet_result.stdout)
        packet_path = run_dir / "packet.json"
        packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

        review_result = run_command(dry_run_command(args, "markdown"))
        (run_dir / "review.md").write_text(review_result.stdout, encoding="utf-8")

        policy_result = run_command(policy_command(packet_path, args), allowed_codes={0, 2})
        policy = json.loads(policy_result.stdout)
        (run_dir / "policy.json").write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(run_dir, ignore_errors=True)
        raise

    print(f"Run directory: {run_dir}")
    print(f"Policy status: {policy['status']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_run error: {exc}", file=sys.stderr)
        sys.exit(1)
