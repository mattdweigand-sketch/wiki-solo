#!/usr/bin/env python3
"""Judge interface for no-write wiki runs.

The stub judge validates that run, policy, and writer artifacts exist and writes
tmp/wiki-runs/<run-id>/judge.json. The pipeline is fixed; provider selects the
replaceable judge adapter. It does not call a model.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


JUDGE_PROVIDERS = ("stub",)
VISUAL_SOURCE_FLAG = "visual_source_requires_review"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Judge a no-write wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument("--provider", choices=JUDGE_PROVIDERS, default=None)
    p.add_argument("--mode", choices=JUDGE_PROVIDERS, dest="provider", help=argparse.SUPPRESS)
    p.add_argument("--overwrite", action="store_true")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def draft_exists(run_dir: Path, packet: dict[str, Any], writer: dict[str, Any]) -> bool:
    draft_path = writer.get("draft_path")
    if draft_path and Path(str(draft_path)).exists():
        return True
    stub_path = run_dir / "draft" / f"{packet['target_slug']}.md.stub"
    return stub_path.exists()


def visual_source_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    risk_flags = packet.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        risk_flags = []
    required = VISUAL_SOURCE_FLAG in risk_flags
    return {
        "required": required,
        "evidence_extraction_performed": False,
        "evidence_source": "none",
        "visible_text_summary": "",
    }


def read_visual_source_evidence(run_dir: Path, packet: dict[str, Any]) -> dict[str, Any]:
    evidence_path = run_dir / "evidence.json"
    if not evidence_path.exists():
        return visual_source_evidence(packet)
    evidence = load_json(evidence_path)
    return {
        "required": evidence.get("required"),
        "evidence_extraction_performed": evidence.get("evidence_extraction_performed"),
        "evidence_source": evidence.get("evidence_source"),
        "visible_text_summary": evidence.get("visible_text_summary"),
    }


def stub_judgment(run_dir: Path) -> dict[str, Any]:
    findings: list[str] = []
    packet_path = run_dir / "packet.json"
    policy_path = run_dir / "policy.json"
    writer_path = run_dir / "writer.json"

    packet = load_json(packet_path) if packet_path.exists() else {}
    policy = load_json(policy_path) if policy_path.exists() else {}
    writer = load_json(writer_path) if writer_path.exists() else {}

    for path in (packet_path, policy_path, writer_path):
        if not path.exists():
            findings.append(f"missing artifact: {path.name}")

    if packet and writer and not draft_exists(run_dir, packet, writer):
        findings.append("missing draft artifact")

    policy_status = policy.get("status", "unknown")
    if policy_status == "reject":
        decision = "reject"
        findings.append("policy rejected the dry-run packet")
    elif findings:
        decision = "needs_revision"
    else:
        decision = "approve_for_review"

    return {
        "judge_version": "wiki-judge.v1",
        "provider": "stub",
        "decision": decision,
        "policy_status": policy_status,
        "writer_provider": writer.get("provider") or writer.get("mode"),
        "scores": {
            "route_correctness": None,
            "source_fidelity": None,
            "citation_adequacy": None,
            "link_quality": None,
            "scope_discipline": 1.0 if not findings else 0.0,
        },
        "findings": findings,
        "human_review_required": True,
        "writes_wiki": False,
        "provider_metadata": {
            "visual_source_evidence": read_visual_source_evidence(run_dir, packet),
        },
    }


def main() -> int:
    args = parser().parse_args()
    run_dir = Path(args.run_dir)
    output_path = run_dir / "judge.json"
    provider = args.provider or "stub"

    if output_path.exists() and not args.overwrite:
        print(f"Judge artifact already exists: {output_path}", file=sys.stderr)
        return 2

    if provider != "stub":
        print(f"Unsupported judge provider: {provider}", file=sys.stderr)
        return 2

    judgment = stub_judgment(run_dir)
    output_path.write_text(json.dumps(judgment, indent=2) + "\n", encoding="utf-8")

    print(f"Judge artifact: {output_path}")
    print(f"Judge decision: {judgment['decision']}")
    return 0 if judgment["decision"] != "reject" else 2


if __name__ == "__main__":
    sys.exit(main())
