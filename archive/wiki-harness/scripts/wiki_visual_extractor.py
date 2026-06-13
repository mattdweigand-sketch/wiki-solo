#!/usr/bin/env python3
"""Visual evidence extractor interface for no-write wiki runs.

The stub extractor consumes tmp/wiki-runs/<run-id>/packet.json and writes
tmp/wiki-runs/<run-id>/evidence.json. It can consume a deterministic same-stem
.ocr.txt sidecar when one already exists next to the visual source. It does not
OCR, inspect pixels, call a model, or write durable wiki files.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VISUAL_EXTRACTOR_PROVIDERS = ("stub",)
VISUAL_SOURCE_FLAG = "visual_source_requires_review"
SUMMARY_MAX_CHARS = 800


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Extract visual evidence for a no-write wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument("--provider", choices=VISUAL_EXTRACTOR_PROVIDERS, default=None)
    p.add_argument("--mode", choices=VISUAL_EXTRACTOR_PROVIDERS, dest="provider", help=argparse.SUPPRESS)
    p.add_argument("--overwrite", action="store_true")
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any], overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def visual_source_required(packet: dict[str, Any]) -> bool:
    risk_flags = packet.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        return False
    return VISUAL_SOURCE_FLAG in risk_flags


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def clipped_summary(text: str, max_chars: int = SUMMARY_MAX_CHARS) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def ocr_sidecar_path(packet: dict[str, Any]) -> Path | None:
    source_path = packet.get("source_path")
    if not isinstance(source_path, str) or not source_path:
        return None
    return Path(source_path).with_suffix(".ocr.txt")


def stub_evidence(packet: dict[str, Any]) -> dict[str, Any]:
    required = visual_source_required(packet)
    findings: list[str] = []
    performed = False
    evidence_source = "none"
    summary = ""
    provider_metadata: dict[str, Any] = {}

    if required:
        findings.append("visual source requires evidence extraction before source fidelity can be scored")
        sidecar_path = ocr_sidecar_path(packet)
        if sidecar_path is not None:
            provider_metadata["ocr_sidecar_path"] = str(sidecar_path)
            if sidecar_path.exists():
                sidecar_text = sidecar_path.read_text(encoding="utf-8").strip()
                if sidecar_text:
                    performed = True
                    evidence_source = "ocr"
                    summary = clipped_summary(sidecar_text)
                    provider_metadata["ocr_sidecar_char_count"] = len(sidecar_text)
                    findings.append("deterministic OCR sidecar was used for visible text evidence")
                else:
                    findings.append("OCR sidecar exists but is empty")
            else:
                findings.append("no deterministic OCR sidecar found")
    else:
        findings.append("source is not flagged as visual")

    return {
        "visual_evidence_version": "wiki-visual-evidence.v1",
        "provider": "stub",
        "source_path": packet.get("source_path"),
        "primary_home": packet.get("primary_home"),
        "required": required,
        "evidence_extraction_performed": performed,
        "evidence_source": evidence_source,
        "visible_text_summary": summary,
        "findings": findings,
        "human_review_required": True,
        "writes_wiki": False,
        "provider_metadata": provider_metadata,
    }


def main() -> int:
    args = parser().parse_args()
    run_dir = Path(args.run_dir)
    provider = args.provider or "stub"
    if provider != "stub":
        print(f"Unsupported visual extractor provider: {provider}", file=sys.stderr)
        return 2

    packet = load_json(run_dir / "packet.json")
    output_path = run_dir / "evidence.json"
    artifact = stub_evidence(packet)
    write_json(output_path, artifact, args.overwrite)

    print(f"Visual evidence artifact: {output_path}")
    print(f"Visual evidence required: {str(artifact['required']).lower()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_visual_extractor error: {exc}", file=sys.stderr)
        sys.exit(1)
