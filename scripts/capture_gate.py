#!/usr/bin/env python3
"""Deterministic approval gate for analysis capture and promotion.

The script does not edit files. It classifies a proposed durable write and
prints the exact approval block an agent should show before applying analysis
or promotion changes.

Exit codes:
  0: approved route is allowed to proceed
  2: approval required before proceeding
  3: invalid or blocked route
"""

from __future__ import annotations

import argparse
import sys


PROMOTION_TRIGGERS = (
    "reusable_distinction",
    "ranking_or_framework",
    "open_question_resolution",
    "future_agent_behavior",
    "existing_page_update",
)


def yn(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"yes", "true", "1", "y"}:
        return True
    if lowered in {"no", "false", "0", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected yes/no")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Classify a wiki capture route and require approval only for analysis or promotion.",
    )
    p.add_argument("--artifact", required=True, help="Short description of the artifact.")
    p.add_argument(
        "--phase",
        required=True,
        choices=["drafting", "accepted", "source", "decision", "experience", "workflow"],
        help="Current state of the user request.",
    )
    p.add_argument("--primary-home", default="", help="Exact intended path, if known.")
    p.add_argument("--pages-touched", default="", help="Comma-separated intended paths.")
    p.add_argument("--source-path", default="", help="Source path or URL if a source is involved.")
    p.add_argument("--synthesized-pages", type=int, default=0)
    p.add_argument("--word-count", type=int, default=0)
    p.add_argument(
        "--domain-context",
        dest="domain_context",
        type=yn,
        default=False,
        help="Whether the answer is about this wiki's configured domain.",
    )
    p.add_argument(
        "--life-context",
        dest="domain_context",
        type=yn,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--trigger",
        action="append",
        choices=PROMOTION_TRIGGERS,
        default=[],
        help="Reusable-artifact trigger. Repeat for multiple triggers.",
    )
    p.add_argument(
        "--approved",
        action="store_true",
        help="Set only after the user explicitly approves this exact route.",
    )
    return p


def classify(args: argparse.Namespace) -> tuple[str, str, str]:
    if args.phase == "drafting":
        return (
            "chat-only",
            "none",
            "The artifact is still being shaped conversationally.",
        )

    if args.phase == "source":
        if not args.source_path:
            return ("blocked", "none", "Source phase requires --source-path.")
        return (
            "ingest",
            args.primary_home or "wiki/sources/<slug>.md",
            "A concrete source must be represented before downstream synthesis cites it.",
        )

    if args.phase == "decision":
        return (
            "capture-decision",
            args.primary_home or "wiki/decisions/<slug>.md",
            "The artifact records a choice and rationale.",
        )

    if args.phase == "experience":
        return (
            "capture-experience",
            args.primary_home or "wiki/<entity>/<slug>.md",
            "The artifact records an observation, field note, or contextual experience.",
        )

    if args.phase == "workflow":
        return (
            "workflow-update",
            args.primary_home or "workflows/<workspace>/<file>.md",
            "The artifact changes how future agents should behave.",
        )

    qualifies_analysis = (
        args.synthesized_pages >= 3 and args.word_count > 300 and args.domain_context
    )
    if qualifies_analysis:
        return (
            "analysis-capture",
            args.primary_home or "wiki/analyses/<slug>.md",
            "Matches the research analysis criteria: 3+ pages, >300 words, domain-context question.",
        )

    if args.trigger:
        return (
            "promotion-audit",
            args.primary_home or "existing page or new page from audit",
            "Promotion trigger present: " + ", ".join(args.trigger) + ".",
        )

    return (
        "chat-only",
        "none",
        "Does not meet analysis-capture criteria and has no promotion trigger.",
    )


def main() -> int:
    args = parser().parse_args()
    route, home, reason = classify(args)

    if route == "blocked":
        print("CAPTURE GATE: BLOCKED")
        print(f"Artifact: {args.artifact}")
        print(f"Reason: {reason}")
        return 3

    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print(f"Mode: {route}")
    print(f"Primary home: {home}")
    print(f"Reason: {reason}")
    print(f"Pages touched: {args.pages_touched or home}")

    if route == "chat-only":
        print("Approval: not required; do not edit files.")
        return 0

    approval_required = route in {"analysis-capture", "promotion-audit"}

    if not approval_required:
        print("Approval: not required for this route.")
        return 0

    if args.approved:
        print("Approval: confirmed for this exact route.")
        return 0

    print()
    print("APPROVAL REQUIRED")
    print("Ask the user to approve this exact mode, primary home, and touched files.")
    print("Re-run with --approved only after approval.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
