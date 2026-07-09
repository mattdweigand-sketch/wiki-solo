#!/usr/bin/env python3
"""Validate the structured approval ledger."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
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
DRAFT_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DRAFT_SHA256_REQUIRED_FROM = "2026-07-08T00:00:00Z"


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not is_nonempty_string(value):
        return None
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


DRAFT_SHA256_REQUIRED_FROM_DT = parse_utc_timestamp(DRAFT_SHA256_REQUIRED_FROM)
assert DRAFT_SHA256_REQUIRED_FROM_DT is not None


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
    approved_at = parse_utc_timestamp(record.get("approved_at"))
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
    # Measurement provenance; optional because historical records predate it.
    if "word_count_path" in record and not isinstance(record.get("word_count_path"), str):
        errors.append("word_count_path must be a string when present")
    if "draft_sha256" in record:
        draft_sha256 = record.get("draft_sha256")
        if not isinstance(draft_sha256, str) or not DRAFT_SHA256_RE.fullmatch(draft_sha256):
            errors.append("draft_sha256 must be 64 lowercase hex characters when present")
    if (
        approved_at is not None
        and approved_at >= DRAFT_SHA256_REQUIRED_FROM_DT
        and record.get("word_count_source") == "measured"
        and is_nonempty_string(record.get("word_count_path"))
        and "draft_sha256" not in record
    ):
        errors.append(
            "draft_sha256 is required for measured capture approvals "
            f"commissioned from {DRAFT_SHA256_REQUIRED_FROM}"
        )
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


def validate_synthesis_approval(record: dict[str, Any]) -> list[str]:
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
    if record.get("primary_home") != "wiki/synthesis.md" and record.get("ledger_update_required") is True:
        errors.append("ledger_update_required must be false unless primary_home is wiki/synthesis.md")

    if "ledger_update_required" not in record or not isinstance(record.get("ledger_update_required"), bool):
        errors.append("ledger_update_required must be a boolean")

    errors.extend(validate_backfill_fields(record))
    return errors


def validate_approval(record: dict[str, Any]) -> list[str]:
    if record.get("record_type") == "capture_approval":
        return validate_capture_approval(record)
    if record.get("record_type") == "synthesis_approval":
        return validate_synthesis_approval(record)
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
