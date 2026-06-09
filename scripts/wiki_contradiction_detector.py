#!/usr/bin/env python3
"""Contradiction detector interface for no-write wiki runs.

The detector consumes tmp/wiki-runs/<run-id>/packet.json and writes
tmp/wiki-runs/<run-id>/contradictions.json. The only implemented provider is
the deterministic stub. It does not inspect wiki semantics and cannot clear
human review.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTRADICTION_PROVIDERS = ("stub",)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Detect contradiction risks for a no-write wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument("--provider", choices=CONTRADICTION_PROVIDERS, default=None)
    p.add_argument("--mode", choices=CONTRADICTION_PROVIDERS, dest="provider", help=argparse.SUPPRESS)
    p.add_argument("--overwrite", action="store_true")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def stub_contradictions(packet: dict[str, Any]) -> dict[str, Any]:
    risk_flags = [str(flag) for flag in packet.get("risk_flags", []) if isinstance(flag, str)]
    findings: list[str] = [
        "stub provider did not perform semantic contradiction detection",
    ]
    if "low_source_confidence" in risk_flags:
        findings.append("low source confidence requires human review")
    if "unknown_source_type" in risk_flags:
        findings.append("unknown source type requires human review")

    return {
        "contradiction_detector_version": "wiki-contradiction-detector.v1",
        "provider": "stub",
        "source_path": packet.get("source_path"),
        "primary_home": packet.get("primary_home"),
        "status": "no_conflict_found",
        "potential_contradictions": [],
        "findings": findings,
        "human_review_required": True,
        "writes_wiki": False,
        "provider_metadata": {},
    }


def main() -> int:
    args = parser().parse_args()
    run_dir = Path(args.run_dir)
    provider = args.provider or "stub"
    if provider != "stub":
        print(f"Unsupported contradiction detector provider: {provider}", file=sys.stderr)
        return 2

    packet = load_json(run_dir / "packet.json")
    output_path = run_dir / "contradictions.json"
    artifact = stub_contradictions(packet)
    write_json(output_path, artifact, args.overwrite)

    print(f"Contradiction artifact: {output_path}")
    print(f"Contradiction status: {artifact['status']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_contradiction_detector error: {exc}", file=sys.stderr)
        sys.exit(1)
