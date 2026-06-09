#!/usr/bin/env python3
"""Agent-neutral shortcut for artifact promotion.

This script is a convenience entrypoint over workflows/maintenance/artifact-promotion.md.
It does not edit wiki files. By default it prints the audit route. With --apply,
it runs capture_gate.py so agents get the same approval boundary as the workflow.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


CAPTURE_GATE = Path("scripts/capture_gate.py")
PROMOTION_WORKFLOW = Path("workflows/maintenance/artifact-promotion.md")
TRIGGERS = (
    "reusable_distinction",
    "ranking_or_framework",
    "open_question_resolution",
    "future_agent_behavior",
    "existing_page_update",
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Route a reusable artifact through the promotion workflow.")
    p.add_argument("artifact", help="Short description of the artifact to promote.")
    p.add_argument(
        "--trigger",
        action="append",
        choices=TRIGGERS,
        default=[],
        help="Why this artifact may be reusable. Repeat for multiple triggers.",
    )
    p.add_argument("--primary-home", default="", help="Proposed primary home, if known.")
    p.add_argument("--pages-touched", default="", help="Comma-separated proposed touched files.")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Run the capture gate for an apply attempt. Without this, audit only.",
    )
    p.add_argument(
        "--approved",
        action="store_true",
        help="Pass through only after the user approves the exact apply route.",
    )
    return p


def print_audit_route(args: argparse.Namespace) -> int:
    triggers = args.trigger or ["not specified"]
    print("PROMOTION AUDIT")
    print(f"Artifact: {args.artifact}")
    print(f"Workflow: {PROMOTION_WORKFLOW}")
    print("Mode: audit-only")
    print(f"Triggers: {', '.join(triggers)}")
    print(f"Primary home: {args.primary_home or 'decide during audit'}")
    print(f"Pages touched: {args.pages_touched or 'decide during audit'}")
    print("Writes files: false")
    print()
    print("Next step: read the promotion workflow and choose one primary home.")
    print("Use --apply only after the user asks to promote, apply, save, file, or update the wiki.")
    return 0


def run_apply_gate(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        str(CAPTURE_GATE),
        "--artifact",
        args.artifact,
        "--phase",
        "accepted",
        "--primary-home",
        args.primary_home,
        "--pages-touched",
        args.pages_touched,
    ]
    triggers = args.trigger or ["reusable_distinction"]
    for trigger in triggers:
        command.extend(["--trigger", trigger])
    if args.approved:
        command.append("--approved")

    result = subprocess.run(command, check=False)
    return result.returncode


def main() -> int:
    args = parser().parse_args()
    if args.apply:
        return run_apply_gate(args)
    return print_audit_route(args)


if __name__ == "__main__":
    sys.exit(main())
