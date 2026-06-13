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

ACTION_LABELS = {
    "analysis-capture": "File a substantial research answer as an analysis page.",
    "promotion-audit": "Apply an artifact promotion to the wiki.",
}

TRIGGER_LABELS = {
    "reusable_distinction": "reusable distinction",
    "ranking_or_framework": "ranking or framework",
    "open_question_resolution": "open-question resolution",
    "future_agent_behavior": "future-agent behavior",
    "existing_page_update": "existing page update",
}


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
            "The artifact records observed or first-person context.",
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
        trigger_labels = [TRIGGER_LABELS[trigger] for trigger in args.trigger]
        return (
            "promotion-audit",
            args.primary_home or "existing page or new page from audit",
            "Promotion trigger present: " + ", ".join(trigger_labels) + ".",
        )

    return (
        "chat-only",
        "none",
        "Does not meet analysis-capture criteria and has no promotion trigger.",
    )


def touched_files(args: argparse.Namespace, home: str) -> str:
    return args.pages_touched or home


def approval_reply(route: str, home: str, files: str) -> str:
    return f"APPROVE {route} | {home} | {files}"


def print_summary(args: argparse.Namespace, route: str, home: str, reason: str) -> str:
    files = touched_files(args, home)
    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print(f"Machine mode: {route}")
    if route in ACTION_LABELS:
        print(f"Proposed action: {ACTION_LABELS[route]}")
    print(f"Primary home: {home}")
    print(f"Reason: {reason}")
    print(f"Pages touched: {files}")
    return files


def print_approval_request(args: argparse.Namespace, route: str, home: str, files: str) -> None:
    action = ACTION_LABELS[route]
    print()
    print("APPROVAL REQUIRED")
    print("No files have been changed yet.")
    print()
    print("What you are approving:")
    print(f"- Durable action: {action}")
    print(f"- Artifact: {args.artifact}")
    print(f"- Primary destination: {home}")
    print(f"- Files the agent may edit: {files}")
    print()
    print("Approve only if these are correct:")
    print("- This artifact should be saved to the wiki, not left in chat.")
    print("- The primary destination is the right durable home.")
    print("- The file list is the full intended edit scope.")
    print()
    print("To approve, reply exactly:")
    print(approval_reply(route, home, files))
    print()
    print('To deny or redirect, say what should change or reply "do not save."')
    print("Re-run with --approved only after approval.")


def print_approval_confirmed(route: str, home: str, files: str) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved action: {ACTION_LABELS[route]}")
    print(f"Approved primary destination: {home}")
    print(f"Approved file scope: {files}")
    print("Proceed only within this approved scope.")


def main() -> int:
    args = parser().parse_args()
    route, home, reason = classify(args)

    if route == "blocked":
        print("CAPTURE GATE: BLOCKED")
        print(f"Artifact: {args.artifact}")
        print(f"Reason: {reason}")
        return 3

    files = print_summary(args, route, home, reason)

    if route == "chat-only":
        print("Approval: not required; do not edit files.")
        return 0

    approval_required = route in {"analysis-capture", "promotion-audit"}

    if not approval_required:
        print("Approval: not required for this route.")
        return 0

    if args.approved:
        print("Approval: confirmed for this exact route.")
        print_approval_confirmed(route, home, files)
        return 0

    print_approval_request(args, route, home, files)
    return 2


if __name__ == "__main__":
    sys.exit(main())
