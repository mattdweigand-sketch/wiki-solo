#!/usr/bin/env python3
"""Run deterministic policy fixtures for the wiki dry-run diff policy."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_FIXTURE_DIR = Path("tests/fixtures/wiki-policy")
POLICY = Path("scripts/wiki_diff_policy.py")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate wiki diff-policy fixture outputs.")
    p.add_argument(
        "--fixture-dir",
        default=str(DEFAULT_FIXTURE_DIR),
        help="Directory containing policy fixture JSON files.",
    )
    return p


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def run_policy(packet: dict[str, Any]) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as f:
        json.dump(packet, f)
        f.flush()
        result = subprocess.run(
            [sys.executable, str(POLICY), f.name],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if result.returncode not in {0, 2}:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def main() -> int:
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
            report = run_policy(fixture["packet"])
            expected = fixture["expected_status"]
            actual = report.get("status")
            errors = [] if actual == expected else [f"status: expected {expected!r}, got {actual!r}"]
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
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
