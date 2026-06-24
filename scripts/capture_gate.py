#!/usr/bin/env python3
"""Deterministic approval gate for capture, promotion, and synthesis.

Unapproved runs are display-only. Approved reruns append or confirm a structured
approval record before the workflow applies analysis, promotion, or synthesis
changes.

Determinism: the gate anchors on checkable facts, not only declared flags.
- A free route (chat-only, ingest, capture-decision, capture-experience,
  workflow-update) may not target wiki/analyses/; that destination always goes
  through analysis-capture or promotion-audit.
- analysis-capture requires --path to the drafted artifact, and the gate counts
  its words itself instead of trusting --word-count.
- Approval-required routes reject placeholder ("<...>") destinations and any path
  outside the allowed durable roots, so an approval names a real, in-scope home.
- synthesis approval displays the reviewed --drafts content and full edit scope
  before durable synthesis changes proceed.

Measurement scope: only word_count is measured (from --path at analysis-capture).
synthesized_pages is a declared value, never measured; validate_capture_runs.py
re-checks that declared number for the 3-page analysis qualification.

Exit codes:
  0: approved route is allowed to proceed
  2: approval required before proceeding
  3: invalid or blocked route
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

from ledger_common import (
    ALLOWED_ROOTS,
    approved_at_now,
    split_scope,
    under_allowed_root,
    write_approval_record as _write_approval_record,
)


DEFAULT_APPROVAL_LEDGER = "scripts/capture-runs.jsonl"
SYNTHESIS_DEFAULT_HOME = "wiki/synthesis.md"

LEDGER_SCHEMA_DESCRIPTION = (
    "Append-only operational records written by scripts/capture_gate.py after "
    "the user approves exact analysis-capture, artifact-promotion, or synthesis "
    "approval scopes. Free routes such as ingest, decision capture, experience "
    "capture, and workflow updates remain unrecorded here."
)

ANALYSES_PREFIX = "wiki/analyses/"
APPROVAL_ROUTES = {"analysis-capture", "promotion-audit"}
# ALLOWED_ROOTS / ALLOWED_ROOT_FILES / under_allowed_root are single-sourced in
# ledger_common so the gate and its validator agree on the durable-root scope
# (and the raw/ exclusion) byte-for-byte.


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
        description="Require approval for wiki analysis capture, promotion, or synthesis.",
    )
    p.add_argument("--artifact", required=True, help="Short description of the artifact.")
    p.add_argument(
        "--kind",
        choices=["capture", "synthesis"],
        default="capture",
        help="Approval branch. Default capture preserves existing phase-derived behavior.",
    )
    p.add_argument(
        "--phase",
        choices=["drafting", "accepted", "source", "decision", "experience", "workflow"],
        help="Current state of the user request. Required for --kind=capture.",
    )
    p.add_argument("--primary-home", default="", help="Exact intended path, if known.")
    p.add_argument("--pages-touched", default="", help="Comma-separated intended paths.")
    p.add_argument("--source-path", default="", help="Source path or URL if a source is involved.")
    p.add_argument(
        "--path",
        default="",
        help="Path to the drafted artifact on disk. Required for analysis-capture; "
             "the gate counts its words instead of trusting --word-count.",
    )
    p.add_argument("--drafts", default="", help="Reviewed synthesis content for --kind=synthesis.")
    p.add_argument("--synthesized-pages", type=int, default=0)
    p.add_argument("--word-count", type=int, default=0,
                   help="Declared word count; overridden by the measured count when --path is given.")
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
    p.add_argument(
        "--approval-ledger",
        default=DEFAULT_APPROVAL_LEDGER,
        help="JSONL file for approved capture, promotion, and synthesis records.",
    )
    return p


def is_placeholder(path: str) -> bool:
    return "<" in path or ">" in path


def normalize_path(path: str) -> str:
    """Resolve ./, //, and .. so destinations cannot be spelled around guards."""
    return posixpath.normpath(path.strip())


def real_destinations(home: str, pages_touched: str) -> list[str]:
    """Concrete declared destination paths, normalized."""
    out: list[str] = []
    for path in [home, *split_scope(pages_touched)]:
        path = path.strip()
        if not path or path == "none" or is_placeholder(path):
            continue
        out.append(normalize_path(path))
    return out


def measure_word_count(path: str) -> int | None:
    """Count word tokens in the drafted artifact, or None if it can't be read."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return len(re.findall(r"\w+", text))


def classify_capture(args: argparse.Namespace) -> tuple[str, str, str]:
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
            "The artifact records observed, field, or first-person context.",
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
            args.primary_home or "wiki/<page>.md",
            "Promotion trigger present: " + ", ".join(trigger_labels) + ".",
        )

    return (
        "chat-only",
        "none",
        "Does not meet analysis-capture criteria and has no promotion trigger.",
    )


def scope_with_home(home: str, pages_touched: str) -> list[str]:
    """pages_touched as a list, guaranteeing primary_home is included."""
    scope = [normalize_path(p) for p in split_scope(pages_touched)]
    home = home.strip()
    if home and home != "none" and not is_placeholder(home) and home not in scope:
        scope.insert(0, home)
    return scope or ([home] if home and home != "none" and not is_placeholder(home) else [])


def approval_guard(args: argparse.Namespace, route: str, home: str) -> str | None:
    """Block reasons for approval-required capture routes."""
    if not args.artifact.strip():
        return ("--artifact must be a non-empty description; the gate will not "
                "write an approval record its own validator would reject.")
    if is_placeholder(home) or not home or home == "none":
        return (f"{route} requires a concrete --primary-home path "
                "(no placeholder); name the real durable destination.")
    if route == "analysis-capture":
        if not args.path:
            return ("analysis-capture requires --path to the drafted artifact so "
                    "its word count can be verified, not declared.")
        if measure_word_count(args.path) is None:
            return f"--path {args.path!r} is not a readable file."
    return None


def free_route_targets_analyses(args: argparse.Namespace, route: str, home: str) -> bool:
    if route in APPROVAL_ROUTES:
        return False
    return any(d.startswith(ANALYSES_PREFIX) for d in real_destinations(home, args.pages_touched))


def out_of_root_destinations(args: argparse.Namespace, home: str) -> list[str]:
    """Concrete declared destinations outside allowed durable roots or under raw/."""
    return [d for d in real_destinations(home, args.pages_touched) if not under_allowed_root(d)]


def capture_approval_record(args: argparse.Namespace, route: str, home: str, scope: list[str],
                            word_count_source: str) -> dict[str, object]:
    return {
        "record_type": "capture_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "approved_at": approved_at_now(),
        "artifact": args.artifact.strip(),
        "route": route,
        "phase": args.phase,
        "primary_home": home.strip(),
        "pages_touched": scope,
        "source_path": args.source_path.strip(),
        "synthesized_pages": args.synthesized_pages,
        "word_count": args.word_count,
        "word_count_source": word_count_source,
        "domain_context": args.domain_context,
        "triggers": sorted(args.trigger),
    }


def synthesis_approval_record(args: argparse.Namespace, home: str, scope: list[str]) -> dict[str, object]:
    return {
        "record_type": "synthesis_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "approved_at": approved_at_now(),
        "artifact": args.artifact.strip(),
        "drafts": args.drafts.strip(),
        "primary_home": home.strip(),
        "pages_touched": scope,
        "ledger_update_required": home.strip() == SYNTHESIS_DEFAULT_HOME and SYNTHESIS_DEFAULT_HOME in scope,
    }


def write_approval_record(record: dict[str, object], ledger: str,
                          record_type: str) -> tuple[bool, Path, str]:
    return _write_approval_record(
        Path(ledger),
        record,
        record_type=record_type,
        schema_description=LEDGER_SCHEMA_DESCRIPTION,
    )


def print_capture_summary(args: argparse.Namespace, route: str, home: str, reason: str,
                          scope: list[str]) -> None:
    files = ", ".join(scope) if scope else (home if home else "none")
    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print(f"Machine mode: {route}")
    if route in ACTION_LABELS:
        print(f"Proposed action: {ACTION_LABELS[route]}")
    print(f"Primary home: {home}")
    print(f"Reason: {reason}")
    print(f"Pages touched: {files}")


def print_synthesis_summary(args: argparse.Namespace, home: str, scope: list[str]) -> None:
    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print("Machine mode: synthesis")
    print("Proposed action: Approve synthesis content and update the synthesis ledger.")
    print(f"Primary home: {home}")
    print(f"Drafts for review: {args.drafts}")
    print(f"Files the agent may edit after approval: {', '.join(scope)}")


def print_capture_approval_request(args: argparse.Namespace, route: str, home: str,
                                   scope: list[str]) -> None:
    action = ACTION_LABELS[route]
    files = ", ".join(scope)
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
    print('Reply with plain-language approval, such as "approve" or "yes", or say what should change.')
    print()
    print("Agents: re-run with --approved only after the user clearly approves the displayed action, destination, and file scope.")


def print_synthesis_approval_request() -> None:
    print()
    print("APPROVAL REQUIRED")
    print("Do not update wiki/synthesis.md, flip draft confidence/status, or log a synthesis promotion yet.")
    print()
    print("Approve only if these are correct:")
    print("- The reviewed synthesis content is right.")
    print("- The primary ledger/durable home is right.")
    print("- The file list is the full intended approval edit scope.")
    print()
    print('Reply with plain-language approval, such as "approve" or "yes", or say what should change.')
    print()
    print("Agents: re-run with --approved only after the user clearly approves the displayed draft and file scope.")


def print_capture_approval_confirmed(args: argparse.Namespace, route: str, home: str,
                                     scope: list[str]) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved action: {ACTION_LABELS[route]}")
    print(f"Approved primary destination: {home}")
    print(f"Approved file scope: {', '.join(scope)}")
    print(f"Approval record: {args.approval_ledger}")
    print("Proceed only within this approved scope.")


def print_synthesis_approval_confirmed(args: argparse.Namespace, home: str, scope: list[str]) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved synthesis: {args.artifact}")
    print(f"Approved primary home: {home}")
    print(f"Approved file scope: {', '.join(scope)}")
    print(f"Approval record: {args.approval_ledger}")
    print("Proceed only within this approved scope.")


def blocked(reason: str, args: argparse.Namespace) -> int:
    """Print the BLOCKED banner with the reason and return exit code 3."""
    print("CAPTURE GATE: BLOCKED")
    print(f"Artifact: {args.artifact}")
    print(f"Reason: {reason}")
    return 3


def synthesis_guard(args: argparse.Namespace, home: str, scope: list[str]) -> str | None:
    if not args.artifact.strip():
        return ("--artifact must be a non-empty description; the gate will not "
                "write an approval record its own validator would reject.")
    if not args.drafts.strip():
        return "Synthesis approval requires --drafts so the user can review what changed."
    if not args.pages_touched.strip():
        return "Synthesis approval requires --pages-touched so the editable scope is explicit."

    checked_scope = scope + [home]
    placeholders = [p for p in checked_scope if p and ("<" in p or ">" in p)]
    if placeholders:
        return f"approval scope must name concrete paths, not placeholders: {placeholders}"
    if home not in scope:
        return f"primary home {home} must be included in --pages-touched."
    outside = [p for p in checked_scope if p and not under_allowed_root(posixpath.normpath(p))]
    if outside:
        return f"approval scope paths must be under an allowed root: {outside}"
    return None


def run_synthesis(args: argparse.Namespace) -> int:
    home = args.primary_home.strip() or SYNTHESIS_DEFAULT_HOME
    if home and not is_placeholder(home):
        home = normalize_path(home)
    scope = [normalize_path(p) for p in split_scope(args.pages_touched)]

    reason = synthesis_guard(args, home, scope)
    if reason:
        return blocked(reason, args)

    print_synthesis_summary(args, home, scope)
    if args.approved:
        print("Approval: confirmed for this exact synthesis content and file scope.")
        record = synthesis_approval_record(args, home, scope)
        wrote, ledger_path, label = write_approval_record(
            record, args.approval_ledger, "synthesis_approval"
        )
        if wrote:
            print(f"Structured approval record: appended approval for {label} to {ledger_path}")
        else:
            print(f"Structured approval record: already present for {label} in {ledger_path}")
        print_synthesis_approval_confirmed(args, home, scope)
        return 0

    print_synthesis_approval_request()
    return 2


def run_capture(args: argparse.Namespace) -> int:
    if not args.phase:
        return blocked("--phase is required when --kind=capture.", args)

    # Measure the word count from the real draft when a path is given, so the
    # decision rests on a fact rather than a declared number.
    word_count_source = "declared"
    if args.path:
        measured = measure_word_count(args.path)
        if measured is not None:
            args.word_count = measured
            word_count_source = "measured"

    route, home, reason = classify_capture(args)
    # Normalize a concrete home once so every downstream check and stored record
    # see the same resolved path.
    if home and home != "none" and not is_placeholder(home):
        home = normalize_path(home)

    if route == "blocked":
        return blocked(reason, args)

    if free_route_targets_analyses(args, route, home):
        return blocked(f"route '{route}' may not write to {ANALYSES_PREFIX}; "
                       "an analysis must go through analysis-capture or promotion-audit.",
                       args)

    outside = out_of_root_destinations(args, home)
    if outside:
        return blocked("destinations must be under an allowed root "
                       f"({', '.join(ALLOWED_ROOTS)}) and never raw/: offending {outside}",
                       args)

    approval_required = route in APPROVAL_ROUTES

    if approval_required:
        block = approval_guard(args, route, home)
        if block:
            return blocked(block, args)

    scope = scope_with_home(home, args.pages_touched)
    print_capture_summary(args, route, home, reason, scope)

    if route == "chat-only":
        print("Approval: not required; do not edit files.")
        return 0

    if not approval_required:
        print("Approval: not required for this route.")
        return 0

    if args.approved:
        print("Approval: confirmed for this exact route.")
        record = capture_approval_record(args, route, home, scope, word_count_source)
        wrote, ledger_path, label = write_approval_record(
            record, args.approval_ledger, "capture_approval"
        )
        if wrote:
            print(f"Structured approval record: appended approval for {label} to {ledger_path}")
        else:
            print(f"Structured approval record: already present for {label} in {ledger_path}")
        print_capture_approval_confirmed(args, route, home, scope)
        return 0

    print_capture_approval_request(args, route, home, scope)
    return 2


def main() -> int:
    args = parser().parse_args()
    if args.kind == "synthesis":
        return run_synthesis(args)
    return run_capture(args)


if __name__ == "__main__":
    sys.exit(main())
