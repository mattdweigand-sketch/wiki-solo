#!/usr/bin/env python3
"""Validate existing no-write semantic artifacts for a wiki run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wiki_eval_semantic import (
    validate_classifier,
    validate_contradictions,
    validate_evidence,
    validate_links,
    load_json,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Validate semantic artifacts in a wiki run directory.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    return p


def expected_page_home_mode(run_dir: Path) -> str | None:
    packet = load_json(run_dir / "packet.json")
    decision = packet.get("page_home_decision", {})
    if isinstance(decision, dict):
        mode = decision.get("mode")
        if isinstance(mode, str):
            return mode
    return None


def validate_semantic_artifacts(run_dir: Path) -> list[str]:
    errors: list[str] = []
    required = ["packet.json", "evidence.json", "classifier.json", "contradictions.json", "links.json"]
    for name in required:
        if not (run_dir / name).exists():
            errors.append(f"missing semantic validation artifact: {run_dir / name}")
    if errors:
        return errors

    expected_mode = expected_page_home_mode(run_dir)
    if expected_mode is None:
        errors.append("packet page_home_decision.mode must be a string")
        return errors

    errors.extend(validate_evidence(run_dir))
    errors.extend(validate_classifier(run_dir, expected_mode))
    errors.extend(validate_contradictions(run_dir))
    errors.extend(validate_links(run_dir))
    return errors


def main() -> int:
    args = parser().parse_args()
    errors = validate_semantic_artifacts(Path(args.run_dir))
    if errors:
        print("FAIL wiki-semantic-contract")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-semantic-contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
