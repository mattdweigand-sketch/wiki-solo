#!/usr/bin/env python3
"""Run wiki dry-run fixtures against known-good historical examples.

Fixtures live under tests/fixtures/wiki-ingest by default. The runner invokes
scripts/wiki_dry_run.py and compares deterministic packet fields only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from wiki_eval_sources import ensure_eval_sources, remove_existing_source_page, write_existing_source_page


DEFAULT_FIXTURE_DIR = Path("tests/fixtures/wiki-ingest")
DRY_RUN = Path("scripts/wiki_dry_run.py")
POLICY = Path("scripts/wiki_diff_policy.py")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate wiki dry-run fixture outputs.")
    p.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory containing fixture JSON files.",
    )
    return p


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def run_dry_run(source_path: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            sys.executable,
            str(DRY_RUN),
            source_path,
            "--validate-schema",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def run_policy(packet: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(POLICY), "-"],
        input=json.dumps(packet),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in {0, 2}:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def compare_fixture(fixture: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    expected_pairs = {
        "source_path": fixture["input_source"],
        "primary_home": fixture["expected_primary_home"],
    }
    optional_pairs = {
        "inferred_source_type": "expected_source_type",
        "source_path_exists": "expected_source_path_exists",
        "source_gitignored": "expected_source_gitignored",
        "source_tracked": "expected_source_tracked",
        "primary_home_exists": "expected_primary_home_exists",
        "human_review_required": "expected_human_review_required",
        "writes_files": "expected_writes_files",
    }
    for key, expected in expected_pairs.items():
        actual = packet.get(key)
        if actual != expected:
            errors.append(f"{key}: expected {expected!r}, got {actual!r}")
    for packet_key, fixture_key in optional_pairs.items():
        if fixture_key not in fixture:
            continue
        expected = fixture[fixture_key]
        actual = packet.get(packet_key)
        if actual != expected:
            errors.append(f"{packet_key}: expected {expected!r}, got {actual!r}")

    expected_mode = fixture["expected_page_home_mode"]
    actual_mode = packet.get("page_home_decision", {}).get("mode")
    if actual_mode != expected_mode:
        errors.append(f"page_home_decision.mode: expected {expected_mode!r}, got {actual_mode!r}")

    expected_touched = fixture.get("expected_touched_files", [])
    actual_touched = packet.get("expected_touched_files", [])
    if actual_touched != expected_touched:
        errors.append(f"expected_touched_files: expected {expected_touched!r}, got {actual_touched!r}")

    actual_risks = set(packet.get("risk_flags", []))
    for flag in fixture.get("expected_risk_flags", []):
        if flag not in actual_risks:
            errors.append(f"risk_flags missing expected flag {flag!r}")
    for flag in fixture.get("expected_absent_risk_flags", []):
        if flag in actual_risks:
            errors.append(f"risk_flags contained forbidden flag {flag!r}")
    if "expected_exact_risk_flags" in fixture:
        expected_exact_risks = set(fixture["expected_exact_risk_flags"])
        missing = sorted(expected_exact_risks - actual_risks)
        unexpected = sorted(actual_risks - expected_exact_risks)
        if missing:
            errors.append(f"risk_flags missing exact expected flags {missing!r}")
        if unexpected:
            errors.append(f"risk_flags contained unexpected flags {unexpected!r}")

    for pattern in fixture.get("forbidden_touched_patterns", []):
        matches = [path for path in actual_touched if fnmatch.fnmatch(path, pattern)]
        if matches:
            errors.append(f"forbidden touched pattern {pattern!r} matched {matches!r}")

    if packet.get("writes_files") is not False:
        errors.append("packet must declare writes_files=false")
    if packet.get("human_review_required") is not True:
        errors.append("packet must require human review")

    if "expected_policy_status" in fixture:
        report = run_policy(packet)
        expected_status = fixture["expected_policy_status"]
        actual_status = report.get("status")
        if actual_status != expected_status:
            errors.append(f"policy status: expected {expected_status!r}, got {actual_status!r}")

    return errors


def main() -> int:
    ensure_eval_sources()
    write_existing_source_page()
    args = parser().parse_args()
    fixture_dir = Path(args.fixture_dir)
    fixture_paths = sorted(fixture_dir.glob("*.json"))
    if not fixture_paths:
        print(f"No fixtures found in {fixture_dir}", file=sys.stderr)
        return 2

    failures = 0
    for path in fixture_paths:
        fixture = load_fixture(path)
        fixture_id = fixture.get("id", path.stem)
        try:
            packet = run_dry_run(fixture["input_source"])
            errors = compare_fixture(fixture, packet)
        except Exception as exc:
            errors = [str(exc)]

        if errors:
            failures += 1
            print(f"FAIL {fixture_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {fixture_id}")

    print(f"\nSummary: {len(fixture_paths) - failures} passed, {failures} failed")
    remove_existing_source_page()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
