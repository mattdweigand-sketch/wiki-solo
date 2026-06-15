#!/usr/bin/env python3
"""Deterministic approval gate for synthesis promotion.

The synthesize workflow is draft-first. This gate forces agents to show the
exact synthesis draft and edit scope before updating wiki/synthesis.md,
flipping draft confidence/status, or logging a promotion.

Exit codes:
  0: approved synthesis scope is allowed to proceed
  2: approval required before proceeding
  3: invalid or blocked synthesis approval request
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_APPROVAL_LEDGER = "scripts/synthesis-runs.jsonl"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Require user approval before promoting synthesis output.",
    )
    p.add_argument("--artifact", required=True, help="Short description of the synthesis run.")
    p.add_argument("--drafts", required=True, help="Draft pages or sections being reviewed.")
    p.add_argument(
        "--primary-home",
        default="wiki/synthesis.md",
        help="Ledger or primary durable home for the approved synthesis.",
    )
    p.add_argument(
        "--pages-touched",
        required=True,
        help="Comma-separated file scope the agent may edit after approval.",
    )
    p.add_argument(
        "--approval-ledger",
        default=DEFAULT_APPROVAL_LEDGER,
        help="JSONL file for approved synthesis approval records.",
    )
    p.add_argument(
        "--approved",
        action="store_true",
        help="Set only after the user explicitly approves this exact synthesis draft and file scope.",
    )
    return p


def blocked(message: str, args: argparse.Namespace) -> int:
    print("SYNTHESIS GATE: BLOCKED")
    print(f"Artifact: {args.artifact}")
    print(f"Reason: {message}")
    return 3


def validate(args: argparse.Namespace) -> str | None:
    if not args.drafts.strip():
        return "Synthesis approval requires --drafts so the user can review what changed."
    if not args.pages_touched.strip():
        return "Synthesis approval requires --pages-touched so the editable scope is explicit."
    touched = {path.strip() for path in args.pages_touched.split(",")}
    if "wiki/synthesis.md" not in touched and args.primary_home == "wiki/synthesis.md":
        return "Ledger approval scope must include wiki/synthesis.md in --pages-touched."
    return None


def split_scope(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def stable_run_id(args: argparse.Namespace) -> str:
    payload = {
        "artifact": args.artifact.strip(),
        "drafts": args.drafts.strip(),
        "primary_home": args.primary_home.strip(),
        "pages_touched": split_scope(args.pages_touched),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def existing_approved_run_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    run_ids: set[str] = set()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("record_type") == "synthesis_approval" and record.get("approval_status") == "approved":
            run_id = record.get("run_id")
            if isinstance(run_id, str):
                run_ids.add(run_id)
    return run_ids


def approval_record(args: argparse.Namespace) -> dict[str, object]:
    approved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    pages_touched = split_scope(args.pages_touched)
    return {
        "record_type": "synthesis_approval",
        "schema_version": 1,
        "run_id": stable_run_id(args),
        "approval_status": "approved",
        "approved_at": approved_at,
        "artifact": args.artifact.strip(),
        "drafts": args.drafts.strip(),
        "primary_home": args.primary_home.strip(),
        "pages_touched": pages_touched,
        "ledger_update_required": args.primary_home.strip() == "wiki/synthesis.md" and "wiki/synthesis.md" in pages_touched,
    }


def write_approval_record(args: argparse.Namespace) -> tuple[bool, Path, str]:
    ledger_path = Path(args.approval_ledger)
    record = approval_record(args)
    run_id = str(record["run_id"])
    approved_ids = existing_approved_run_ids(ledger_path)
    if run_id in approved_ids:
        return False, ledger_path, run_id

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return True, ledger_path, run_id


def print_summary(args: argparse.Namespace) -> None:
    print("SYNTHESIS GATE")
    print(f"Artifact: {args.artifact}")
    print("Proposed action: Approve synthesis draft and update the synthesis ledger.")
    print(f"Primary home: {args.primary_home}")
    print(f"Drafts for review: {args.drafts}")
    print(f"Files the agent may edit after approval: {args.pages_touched}")


def print_approval_request() -> None:
    print()
    print("APPROVAL REQUIRED")
    print("Do not update wiki/synthesis.md, flip draft confidence/status, or log a synthesis promotion yet.")
    print()
    print("Approve only if these are correct:")
    print("- The draft synthesis change is right.")
    print("- The primary ledger/durable home is right.")
    print("- The file list is the full intended approval edit scope.")
    print()
    print('Reply with plain-language approval, such as "approve" or "yes", or say what should change.')
    print()
    print("Agents: re-run with --approved only after the user clearly approves the displayed draft and file scope.")


def print_approval_confirmed(args: argparse.Namespace) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved synthesis: {args.artifact}")
    print(f"Approved primary home: {args.primary_home}")
    print(f"Approved file scope: {args.pages_touched}")
    print(f"Approval record: {args.approval_ledger}")
    print("Proceed only within this approved scope.")


def main() -> int:
    args = parser().parse_args()
    reason = validate(args)
    if reason:
        return blocked(reason, args)

    print_summary(args)
    if args.approved:
        print("Approval: confirmed for this exact synthesis draft and file scope.")
        wrote, ledger_path, run_id = write_approval_record(args)
        if wrote:
            print(f"Structured approval record: appended run_id {run_id} to {ledger_path}")
        else:
            print(f"Structured approval record: already present for run_id {run_id} in {ledger_path}")
        print_approval_confirmed(args)
        return 0

    print_approval_request()
    return 2


if __name__ == "__main__":
    sys.exit(main())
