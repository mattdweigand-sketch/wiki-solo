#!/usr/bin/env python3
"""Validate the wiki provider manifest contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MANIFEST_PATH = Path("config/wiki-provider-manifest.json")
SCHEMA_PATH = Path("schemas/wiki-provider-manifest.schema.json")
REQUIRED_KEYS = {
    "manifest_version",
    "architecture",
    "provider_rule",
    "slots",
    "readiness_command",
    "eval_command",
}
REQUIRED_SLOTS = {
    "visual_extractor",
    "classifier",
    "contradiction_detector",
    "link_scorer",
    "writer",
    "judge",
}
SLOT_KEYS = {
    "supported_providers",
    "input_artifacts",
    "output_artifacts",
    "validator_command",
    "writes_wiki",
    "human_review_required",
}
EXPECTED_OUTPUTS = {
    "visual_extractor": {"evidence.json"},
    "classifier": {"classifier.json"},
    "contradiction_detector": {"contradictions.json"},
    "link_scorer": {"links.json"},
    "writer": {"writer.json", "draft/README.md", "draft/manifest.json", "draft/<target-slug>.md.stub"},
    "judge": {"judge.json"},
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate config/wiki-provider-manifest.json.")
    p.add_argument("--manifest", default=str(MANIFEST_PATH))
    p.add_argument("--schema", default=str(SCHEMA_PATH))
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_string_list(value: Any, label: str, require_non_empty: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return [f"{label} must be a list"]
    if require_non_empty and not value:
        errors.append(f"{label} must not be empty")
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{label}[{index}] must be a non-empty string")
    if len(value) != len(set(value)):
        errors.append(f"{label} must not contain duplicates")
    return errors


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - manifest.keys())
    extra = sorted(manifest.keys() - REQUIRED_KEYS)
    if missing:
        errors.append(f"provider manifest missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"provider manifest has unsupported fields: {', '.join(extra)}")

    if manifest.get("manifest_version") != "wiki-provider-manifest.v1":
        errors.append("manifest_version must be wiki-provider-manifest.v1")
    errors.extend(validate_string_list(manifest.get("architecture"), "architecture", require_non_empty=True))
    if manifest.get("provider_rule") != "Local, cloud, and stub are providers, not workflows.":
        errors.append("provider_rule must preserve provider-not-workflow boundary")
    if not isinstance(manifest.get("readiness_command"), str) or "wiki_provider_readiness.py" not in manifest.get("readiness_command", ""):
        errors.append("readiness_command must reference scripts/wiki_provider_readiness.py")
    if manifest.get("eval_command") != "python3 scripts/wiki_eval.py --suite provider":
        errors.append("eval_command must be python3 scripts/wiki_eval.py --suite provider")

    slots = manifest.get("slots")
    if not isinstance(slots, dict):
        return errors + ["slots must be an object"]
    missing_slots = sorted(REQUIRED_SLOTS - slots.keys())
    extra_slots = sorted(slots.keys() - REQUIRED_SLOTS)
    if missing_slots:
        errors.append(f"provider manifest missing slots: {', '.join(missing_slots)}")
    if extra_slots:
        errors.append(f"provider manifest has unsupported slots: {', '.join(extra_slots)}")

    for slot_name in sorted(REQUIRED_SLOTS):
        slot = slots.get(slot_name)
        if not isinstance(slot, dict):
            errors.append(f"slot {slot_name} must be an object")
            continue
        missing_slot_keys = sorted(SLOT_KEYS - slot.keys())
        extra_slot_keys = sorted(slot.keys() - SLOT_KEYS)
        if missing_slot_keys:
            errors.append(f"slot {slot_name} missing fields: {', '.join(missing_slot_keys)}")
        if extra_slot_keys:
            errors.append(f"slot {slot_name} has unsupported fields: {', '.join(extra_slot_keys)}")
        if slot.get("supported_providers") != ["stub"]:
            errors.append(f"slot {slot_name} supported_providers must be ['stub']")
        errors.extend(validate_string_list(slot.get("input_artifacts"), f"slot {slot_name} input_artifacts"))
        errors.extend(validate_string_list(slot.get("output_artifacts"), f"slot {slot_name} output_artifacts", require_non_empty=True))
        if set(slot.get("output_artifacts", [])) != EXPECTED_OUTPUTS[slot_name]:
            errors.append(f"slot {slot_name} output_artifacts do not match contract")
        if not isinstance(slot.get("validator_command"), str) or "<run-dir>" not in slot.get("validator_command", ""):
            errors.append(f"slot {slot_name} validator_command must include <run-dir>")
        if slot.get("writes_wiki") is not False:
            errors.append(f"slot {slot_name} must declare writes_wiki=false")
        if slot.get("human_review_required") is not True:
            errors.append(f"slot {slot_name} must declare human_review_required=true")

    return errors


def main() -> int:
    args = parser().parse_args()
    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)
    try:
        manifest = load_json(manifest_path)
        load_json(schema_path)
    except Exception as exc:
        print(f"wiki_validate_provider_manifest error: {exc}", file=sys.stderr)
        return 1

    errors = validate_manifest(manifest)
    if errors:
        print("FAIL wiki-provider-manifest")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-provider-manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
