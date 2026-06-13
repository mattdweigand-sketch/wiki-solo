#!/usr/bin/env python3
"""Page-home classifier interface for no-write wiki runs.

The classifier consumes tmp/wiki-runs/<run-id>/packet.json and writes
tmp/wiki-runs/<run-id>/classifier.json. The only implemented provider is the
deterministic stub, which mirrors the dry-run page-home decision without
calling a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CLASSIFIER_PROVIDERS = ("stub",)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Classify the page-home route for a no-write wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument("--provider", choices=CLASSIFIER_PROVIDERS, default=None)
    p.add_argument("--mode", choices=CLASSIFIER_PROVIDERS, dest="provider", help=argparse.SUPPRESS)
    p.add_argument("--overwrite", action="store_true")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def stub_classification(packet: dict[str, Any]) -> dict[str, Any]:
    decision = packet.get("page_home_decision", {})
    mode = decision.get("mode") if isinstance(decision, dict) else None
    rationale = decision.get("rationale") if isinstance(decision, dict) else ""
    risk_flags = packet.get("risk_flags", [])

    findings: list[str] = []
    if packet.get("primary_home_exists"):
        findings.append("primary home already exists; classifier preserves no-op route")
    if "unknown_source_type" in risk_flags:
        findings.append("source type is unknown")
    if "source_path_missing" in risk_flags:
        findings.append("source path is missing")

    return {
        "classifier_version": "wiki-classifier.v1",
        "provider": "stub",
        "source_path": packet.get("source_path"),
        "primary_home": packet.get("primary_home"),
        "page_home_mode": mode,
        "confidence": 1.0 if mode in {"source_only", "no_op"} else None,
        "rationale": rationale,
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
        print(f"Unsupported classifier provider: {provider}", file=sys.stderr)
        return 2

    packet_path = run_dir / "packet.json"
    output_path = run_dir / "classifier.json"
    packet = load_json(packet_path)
    artifact = stub_classification(packet)
    write_json(output_path, artifact, args.overwrite)

    print(f"Classifier artifact: {output_path}")
    print(f"Page-home mode: {artifact['page_home_mode']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_classifier error: {exc}", file=sys.stderr)
        sys.exit(1)
