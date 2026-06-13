#!/usr/bin/env python3
"""Check the apply boundary for a completed wiki run.

This v1 command is an apply gate, not a durable writer. It validates a
tmp/wiki-runs/<run-id>/ directory, reports blockers and review requirements,
and confirms whether the run is eligible for a future manual apply step. It
does not write to wiki/.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from wiki_diff_policy import REJECT_RISK_FLAGS, REVIEW_RISK_FLAGS, touches_core
from wiki_eval_run import validate_run_artifacts


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Check whether a wiki run can cross the apply boundary.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument(
        "--approved",
        action="store_true",
        help="Acknowledge human approval for review-only apply eligibility. Does not write files.",
    )
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def git_status(paths: list[str]) -> str:
    if not paths:
        return ""
    result = subprocess.run(
        ["git", "status", "--short", "--", *paths],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def touched_files(packet: dict[str, Any]) -> list[str]:
    value = packet.get("expected_touched_files", [])
    if not isinstance(value, list):
        return []
    return [str(path) for path in value]


def check_boundary(run_dir: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    errors = validate_run_artifacts(run_dir)
    if errors:
        return errors, [], {}

    packet = load_json(run_dir / "packet.json")
    policy = load_json(run_dir / "policy.json")
    writer = load_json(run_dir / "writer.json")
    judge = load_json(run_dir / "judge.json")

    blockers: list[str] = []
    review_reasons: list[str] = []
    files = touched_files(packet)
    risk_flags = [str(flag) for flag in packet.get("risk_flags", []) if isinstance(flag, str)]

    if policy.get("status") == "reject":
        blockers.append("policy status is reject")
    if policy.get("status") == "review":
        review_reasons.append("policy status is review")
    if judge.get("decision") == "reject":
        blockers.append("judge decision is reject")
    if judge.get("decision") == "needs_revision":
        review_reasons.append("judge decision is needs_revision")
    if packet.get("writes_files") is not False:
        blockers.append("packet does not declare writes_files=false")
    if writer.get("writes_wiki") is not False:
        blockers.append("writer does not declare writes_wiki=false")
    if judge.get("writes_wiki") is not False:
        blockers.append("judge does not declare writes_wiki=false")

    raw_touches = [path for path in files if path.startswith("raw/")]
    if raw_touches:
        blockers.append("expected touched files include raw/ paths")

    core_touches = [path for path in files if touches_core(path)]
    if core_touches:
        review_reasons.append("expected touched files include protected root/workflow/script/schema paths")

    for flag in risk_flags:
        if flag in REJECT_RISK_FLAGS:
            blockers.append(f"risk flag blocks apply: {flag}")
        elif flag in REVIEW_RISK_FLAGS:
            review_reasons.append(f"risk flag requires review: {flag}")

    if git_status(files):
        blockers.append("working tree is dirty in expected touched files")

    # V1 deliberately requires explicit human approval for every apply crossing.
    review_reasons.append("v1 apply boundary requires explicit human approval")

    summary = {
        "run_dir": str(run_dir),
        "task_type": packet.get("task_type"),
        "primary_home": packet.get("primary_home"),
        "expected_touched_files": files,
        "policy_status": policy.get("status"),
        "judge_decision": judge.get("decision"),
        "human_review_required": True,
        "writes_wiki": False,
    }
    return blockers, review_reasons, summary


def print_report(blockers: list[str], review_reasons: list[str], summary: dict[str, Any]) -> None:
    print("Wiki apply boundary")
    if summary:
        print(f"- Run directory: `{summary['run_dir']}`")
        print(f"- Task type: `{summary.get('task_type')}`")
        print(f"- Primary home: `{summary.get('primary_home')}`")
        print(f"- Policy status: `{summary.get('policy_status')}`")
        print(f"- Judge decision: `{summary.get('judge_decision')}`")
        print("- Expected touched files:")
        files = summary.get("expected_touched_files") or []
        if files:
            for path in files:
                print(f"  - `{path}`")
        else:
            print("  - none")

    if blockers:
        print("\nBLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
    if review_reasons:
        print("\nAPPROVAL REQUIRED")
        for reason in review_reasons:
            print(f"- {reason}")

    print("\nNo durable files were written.")


def main() -> int:
    args = parser().parse_args()
    blockers, review_reasons, summary = check_boundary(Path(args.run_dir))
    print_report(blockers, review_reasons, summary)

    if blockers:
        return 2
    if review_reasons and not args.approved:
        return 3

    print("\nPASS wiki-apply-boundary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
