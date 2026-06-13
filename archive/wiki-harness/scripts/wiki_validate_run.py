#!/usr/bin/env python3
"""Validate an existing no-write wiki run artifact directory.

This command checks a completed tmp/wiki-runs/<run-id>/ directory without
creating or mutating artifacts. It is intended for provider outputs that should
be inspected directly without running the full fixture suite.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wiki_eval_run import validate_run_artifacts


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate an existing wiki run artifact directory.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument(
        "--expected-policy-status",
        choices=["pass", "review", "reject", "unknown"],
        default=None,
        help="Optional expected policy status.",
    )
    p.add_argument(
        "--expected-judge-decision",
        choices=["approve_for_review", "needs_revision", "reject"],
        default=None,
        help="Optional expected judge decision.",
    )
    p.add_argument(
        "--expected-draft",
        action="append",
        default=[],
        help="Expected draft path relative to the run directory. Repeat as needed.",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    errors = validate_run_artifacts(
        Path(args.run_dir),
        expected_policy_status=args.expected_policy_status,
        expected_judge_decision=args.expected_judge_decision,
        expected_drafts=args.expected_draft,
    )

    if errors:
        print("FAIL wiki-run-contract")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-run-contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
