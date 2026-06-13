#!/usr/bin/env python3
"""Link quality scorer interface for no-write wiki runs.

The scorer consumes tmp/wiki-runs/<run-id>/packet.json and writes
tmp/wiki-runs/<run-id>/links.json. The only implemented provider is the
deterministic stub. It scores only links already present in the packet and
does not propose new links.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


LINK_SCORER_PROVIDERS = ("stub",)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Score proposed links for a no-write wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument("--provider", choices=LINK_SCORER_PROVIDERS, default=None)
    p.add_argument("--mode", choices=LINK_SCORER_PROVIDERS, dest="provider", help=argparse.SUPPRESS)
    p.add_argument("--overwrite", action="store_true")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def score_stub_link(link: dict[str, Any]) -> dict[str, Any]:
    target = link.get("target")
    label = link.get("label", "Related")
    evidence = link.get("evidence", "")
    has_evidence = isinstance(evidence, str) and bool(evidence.strip())
    typed_label = label in {"Supports", "Contradicts", "Depends on", "Derived from", "Part of"}
    score = 3 if typed_label and has_evidence else 2 if has_evidence else 1

    return {
        "target": target,
        "label": label,
        "score": score,
        "rationale": "stub score based on typed label and evidence presence only",
    }


def stub_link_scores(packet: dict[str, Any]) -> dict[str, Any]:
    proposed_links = packet.get("proposed_links", [])
    scored_links = [
        score_stub_link(link)
        for link in proposed_links
        if isinstance(link, dict)
    ]
    findings = ["stub provider did not discover or verify links"]
    if not scored_links:
        findings.append("packet contains no proposed links")

    return {
        "link_scorer_version": "wiki-link-scorer.v1",
        "provider": "stub",
        "source_path": packet.get("source_path"),
        "primary_home": packet.get("primary_home"),
        "scored_links": scored_links,
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
        print(f"Unsupported link scorer provider: {provider}", file=sys.stderr)
        return 2

    packet = load_json(run_dir / "packet.json")
    output_path = run_dir / "links.json"
    artifact = stub_link_scores(packet)
    write_json(output_path, artifact, args.overwrite)

    print(f"Link scorer artifact: {output_path}")
    print(f"Scored links: {len(artifact['scored_links'])}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_link_scorer error: {exc}", file=sys.stderr)
        sys.exit(1)
