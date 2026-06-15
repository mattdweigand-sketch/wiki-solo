#!/usr/bin/env python3
"""Validate the structured capture approval ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_LEDGER = Path("scripts/capture-runs.jsonl")
RUN_ID_RE = re.compile(r"^[0-9a-f]{16}$")
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
        help="JSONL capture approval ledger to validate.",
    )
    return p


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def stable_run_id(record: dict[str, Any]) -> str:
    payload = {
        "artifact": record["artifact"].strip(),
        "route": record["route"],
        "phase": record["phase"],
        "primary_home": record["primary_home"].strip(),
        "pages_touched": record["pages_touched"],
        "source_path": record.get("source_path", "").strip(),
        "synthesized_pages": record.get("synthesized_pages", 0),
        "word_count": record.get("word_count", 0),
        "domain_context": record.get("domain_context", False),
        "triggers": sorted(record.get("triggers", [])),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def validate_timestamp(value: Any) -> str | None:
    if not is_nonempty_string(value):
        return "approved_at must be a non-empty string"
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return "approved_at must be ISO-8601 parseable"
    return None


def validate_schema(record: dict[str, Any], line_no: int) -> list[str]:
    errors: list[str] = []
    if line_no != 1:
        errors.append("schema record must be the first line")
    if record.get("schema_version") != 1:
        errors.append("schema record must have schema_version 1")
    if not is_nonempty_string(record.get("description")):
        errors.append("schema record must have a description")
    return errors


def validate_pages(record: dict[str, Any]) -> list[str]:
    pages_touched = record.get("pages_touched")
    if not isinstance(pages_touched, list) or not pages_touched:
        return ["pages_touched must be a non-empty list"]
    if not all(is_nonempty_string(path) for path in pages_touched):
        return ["pages_touched entries must be non-empty strings"]
    primary_home = record.get("primary_home")
    if is_nonempty_string(primary_home) and primary_home not in pages_touched:
        return ["primary_home must be included in pages_touched"]
    return []


def validate_approval(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != 1:
        errors.append("approval record must have schema_version 1")
    if record.get("approval_status") != "approved":
        errors.append("approval_status must be approved")
    if not isinstance(record.get("run_id"), str) or not RUN_ID_RE.match(record["run_id"]):
        errors.append("run_id must be 16 lowercase hex characters")
    for key in ("artifact", "primary_home"):
        if not is_nonempty_string(record.get(key)):
            errors.append(f"{key} must be a non-empty string")

    route = record.get("route")
    if route not in VALID_ROUTES:
        errors.append(f"route must be one of {sorted(VALID_ROUTES)}")
    if record.get("phase") not in VALID_PHASES:
        errors.append("phase must be accepted for capture approvals")

    errors.extend(validate_pages(record))

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

    if record.get("backfilled") is True and not is_nonempty_string(record.get("backfill_source")):
        errors.append("backfilled records must include backfill_source")
    if "backfilled" in record and not isinstance(record.get("backfilled"), bool):
        errors.append("backfilled must be a boolean when present")

    if not errors:
        expected = stable_run_id(record)
        if record["run_id"] != expected:
            errors.append(f"run_id mismatch: expected {expected}")

    return errors


def validate(path: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    approval_count = 0
    seen_run_ids: set[str] = set()
    schema_count = 0

    if not path.exists():
        return [f"{path} does not exist"], 0

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            errors.append(f"line {line_no}: blank lines are not allowed")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(record, dict):
            errors.append(f"line {line_no}: record must be a JSON object")
            continue

        record_type = record.get("record_type")
        if record_type == "schema":
            schema_count += 1
            for error in validate_schema(record, line_no):
                errors.append(f"line {line_no}: {error}")
            continue
        if record_type != "capture_approval":
            errors.append(f"line {line_no}: unsupported record_type {record_type!r}")
            continue

        approval_count += 1
        for error in validate_approval(record):
            errors.append(f"line {line_no}: {error}")
        run_id = record.get("run_id")
        if isinstance(run_id, str):
            if run_id in seen_run_ids:
                errors.append(f"line {line_no}: duplicate run_id {run_id}")
            seen_run_ids.add(run_id)

    if schema_count != 1:
        errors.append(f"expected exactly one schema record, found {schema_count}")

    return errors, approval_count


def main() -> int:
    args = parser().parse_args()
    errors, approval_count = validate(Path(args.path))
    if errors:
        print("Capture run ledger validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Capture run ledger validation passed: {approval_count} approved record(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
