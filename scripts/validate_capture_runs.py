#!/usr/bin/env python3
"""Validate the structured approval ledger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from ledger_common import (
    is_nonempty_string,
    validate_ledger,
    validate_pages as _validate_pages,
    validate_timestamp,
)


DEFAULT_LEDGER = Path("scripts/capture-runs.jsonl")
VALID_RECORD_TYPES = {"capture_approval", "synthesis_approval"}
VALID_ROUTES = {"analysis-capture", "promotion-audit"}
VALID_PHASES = {"accepted"}
VALID_TRIGGERS = {
    "reusable_distinction",
    "ranking_or_framework",
    "open_question_resolution",
    "future_agent_behavior",
    "existing_page_update",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate scripts/capture-runs.jsonl.")
    p.add_argument(
        "path",
        nargs="?",
        default=str(DEFAULT_LEDGER),
        help="JSONL approval ledger to validate.",
    )
    return p


def validate_backfill_fields(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("backfilled") is True and not is_nonempty_string(record.get("backfill_source")):
        errors.append("backfilled records must include backfill_source")
    if "backfilled" in record and not isinstance(record.get("backfilled"), bool):
        errors.append("backfilled must be a boolean when present")
    return errors


def validate_capture_approval(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != 1:
        errors.append("approval record must have schema_version 1")
    if record.get("approval_status") != "approved":
        errors.append("approval_status must be approved")
    for key in ("artifact", "primary_home"):
        if not is_nonempty_string(record.get(key)):
            errors.append(f"{key} must be a non-empty string")

    route = record.get("route")
    if route not in VALID_ROUTES:
        errors.append(f"route must be one of {sorted(VALID_ROUTES)}")
    if record.get("phase") not in VALID_PHASES:
        errors.append("phase must be accepted for capture approvals")

    errors.extend(_validate_pages(record))

    timestamp_error = validate_timestamp(record.get("approved_at"))
    if timestamp_error:
        errors.append(timestamp_error)

    synthesized_pages = record.get("synthesized_pages")
    word_count = record.get("word_count")
    domain_context = record.get("domain_context")
    triggers = record.get("triggers")
    if not isinstance(synthesized_pages, int) or synthesized_pages < 0:
        errors.append("synthesized_pages must be a non-negative integer")
    if not isinstance(word_count, int) or word_count < 0:
        errors.append("word_count must be a non-negative integer")
    if not isinstance(domain_context, bool):
        errors.append("domain_context must be a boolean")
    if not isinstance(triggers, list) or not all(trigger in VALID_TRIGGERS for trigger in triggers):
        errors.append("triggers must be a list of valid promotion triggers")

    if route == "analysis-capture":
        if not (
            isinstance(synthesized_pages, int)
            and synthesized_pages >= 3
            and isinstance(word_count, int)
            and word_count > 300
            and domain_context is True
        ):
            errors.append("analysis-capture records must meet the 3+ pages, >300 words, domain-context criteria")
    if route == "promotion-audit" and triggers == []:
        errors.append("promotion-audit records must include at least one trigger")

    errors.extend(validate_backfill_fields(record))
    return errors


def check_synthesis_record(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != 1:
        errors.append("approval record must have schema_version 1")
    if record.get("approval_status") != "approved":
        errors.append("approval_status must be approved")
    for key in ("artifact", "drafts", "primary_home"):
        if not is_nonempty_string(record.get(key)):
            errors.append(f"{key} must be a non-empty string")

    pages_touched = record.get("pages_touched")
    errors.extend(_validate_pages(record))

    timestamp_error = validate_timestamp(record.get("approved_at"))
    if timestamp_error:
        errors.append(timestamp_error)

    if isinstance(pages_touched, list) and record.get("primary_home") == "wiki/synthesis.md":
        if record.get("ledger_update_required") is not True:
            errors.append("wiki/synthesis.md primary_home requires ledger_update_required true")

    if "ledger_update_required" not in record or not isinstance(record.get("ledger_update_required"), bool):
        errors.append("ledger_update_required must be a boolean")

    errors.extend(validate_backfill_fields(record))
    return errors


def validate_approval(record: dict[str, Any]) -> list[str]:
    if record.get("record_type") == "capture_approval":
        return validate_capture_approval(record)
    if record.get("record_type") == "synthesis_approval":
        return check_synthesis_record(record)
    return [f"unsupported record_type {record.get('record_type')!r}"]


def validate(path: Path) -> tuple[list[str], int]:
    return validate_ledger(path, VALID_RECORD_TYPES, validate_approval)


def main() -> int:
    args = parser().parse_args()
    errors, approval_count = validate(Path(args.path))
    if errors:
        print("Approval ledger validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Approval ledger validation passed: {approval_count} approved record(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
