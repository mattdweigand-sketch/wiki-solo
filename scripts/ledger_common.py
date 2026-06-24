#!/usr/bin/env python3
"""Shared helpers for the approval ledger.

The approval gate writes capture_approval and synthesis_approval records to one
JSONL ledger. Idempotency is based on approval content identity, not hashes:
historical records may still carry inert legacy identifier fields, but new
records do not generate them and validators ignore them.

Every approval record's primary_home must be included in pages_touched, so the
main approved destination is always part of the explicit editable scope.
"""

from __future__ import annotations

import json
import posixpath
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


# Durable roots an approved capture/promotion/synthesis may edit. raw/ is
# excluded on purpose: source artifacts are never edited or committed.
ALLOWED_ROOTS = ("wiki/", "scripts/", "workflows/", ".claude/", ".codex/", ".github/")
ALLOWED_ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTEXT.md",
    "LICENSE",
    "README.md",
    "REFERENCES.md",
    "SETUP.md",
}
LEGACY_ID_FIELD = "run" + "_id"
IDENTITY_EXCLUDE_FIELDS = {"approved_at", LEGACY_ID_FIELD, "word_count_source"}


def under_allowed_root(path: str) -> bool:
    """True when a destination path is under an allowed durable root and not
    under raw/. The explicit raw/ exclusion is redundant defense (raw/ is not an
    allowed root) but makes the no-raw rule legible at the one place it matters."""
    if path.startswith("raw/") or path == "raw":
        return False
    return path in ALLOWED_ROOT_FILES or any(path.startswith(prefix) for prefix in ALLOWED_ROOTS)


def is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def split_scope(value: str) -> list[str]:
    """Comma-separated --pages-touched into a clean list, dropping blanks."""
    return [item.strip() for item in value.split(",") if item.strip()]


def approved_at_now() -> str:
    """Current UTC time in the ISO-8601 'Z' form the gate emits."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    """Validate pages_touched shape, allowed-root scope, and primary_home membership."""
    pages_touched = record.get("pages_touched")
    if not isinstance(pages_touched, list) or not pages_touched:
        return ["pages_touched must be a non-empty list"]
    if not all(is_nonempty_string(path) for path in pages_touched):
        return ["pages_touched entries must be non-empty strings"]
    errors: list[str] = []
    primary_home = record.get("primary_home")
    if is_nonempty_string(primary_home) and primary_home not in pages_touched:
        errors.append("primary_home must be included in pages_touched")
    # Historical backfills may reference paths that predate current roots.
    if record.get("backfilled") is not True:
        outside = [
            path for path in pages_touched
            if not under_allowed_root(posixpath.normpath(path))
        ]
        if outside:
            errors.append(f"pages_touched paths must be under an allowed root: {outside}")
    return errors


def has_schema_record(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("record_type") == "schema":
            return True
    return False


def approval_identity(record: dict[str, Any]) -> str:
    """Canonical content identity for idempotency and duplicate detection.

    approved_at is event metadata, the legacy identifier is inert historical residue, and
    word_count_source is measurement metadata. None should make the same approved
    boundary look different.
    """
    filtered = {
        key: value
        for key, value in record.items()
        if key not in IDENTITY_EXCLUDE_FIELDS
    }
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"))


def approval_label(record: dict[str, Any]) -> str:
    artifact = str(record.get("artifact") or "approval").strip() or "approval"
    return artifact if len(artifact) <= 80 else artifact[:77] + "..."


def existing_approval_identities(path: Path, record_type: str) -> set[str]:
    """Approved content identities already present for the given record_type."""
    if not path.exists():
        return set()

    identities: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("record_type") == record_type and record.get("approval_status") == "approved":
            identities.add(approval_identity(record))
    return identities


def write_approval_record(
    ledger_path: Path,
    record: dict[str, Any],
    record_type: str,
    schema_description: str,
) -> tuple[bool, Path, str]:
    """Idempotently append an approval record, seeding the schema line on first write.

    Returns (wrote, ledger_path, label); wrote is False when an approved record
    with the same content identity is already present.
    """
    identity = approval_identity(record)
    label = approval_label(record)
    approved_identities = existing_approval_identities(ledger_path, record_type)
    if identity in approved_identities:
        return False, ledger_path, label

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    seed_schema = not has_schema_record(ledger_path)
    with ledger_path.open("a", encoding="utf-8") as f:
        if seed_schema:
            schema = {"record_type": "schema", "schema_version": 1,
                      "description": schema_description}
            f.write(json.dumps(schema, sort_keys=True, separators=(",", ":")) + "\n")
        f.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return True, ledger_path, label


def validate_ledger(
    path: Path,
    record_types: set[str],
    validate_approval: Callable[[dict[str, Any]], list[str]],
) -> tuple[list[str], int]:
    """Iterate a JSONL approval ledger and apply shared structural checks."""
    errors: list[str] = []
    approval_count = 0
    seen_identities: set[str] = set()
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

        rtype = record.get("record_type")
        if rtype == "schema":
            schema_count += 1
            for error in validate_schema(record, line_no):
                errors.append(f"line {line_no}: {error}")
            continue
        if rtype not in record_types:
            errors.append(f"line {line_no}: unsupported record_type {rtype!r}")
            continue

        approval_count += 1
        for error in validate_approval(record):
            errors.append(f"line {line_no}: {error}")
        identity = approval_identity(record)
        if identity in seen_identities:
            errors.append(f"line {line_no}: duplicate approval record")
        seen_identities.add(identity)

    if schema_count != 1:
        errors.append(f"expected exactly one schema record, found {schema_count}")

    return errors, approval_count
