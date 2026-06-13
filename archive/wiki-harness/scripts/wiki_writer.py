#!/usr/bin/env python3
"""Writer interface for no-write wiki runs.

The writer consumes tmp/wiki-runs/<run-id>/packet.json and writes only into the
run's draft/ directory. The pipeline is fixed; provider selects the replaceable
writer adapter. The only implemented provider is the deterministic stub.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WRITER_PROVIDERS = ("stub",)
VISUAL_SOURCE_FLAG = "visual_source_requires_review"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Write draft artifacts for a wiki run.")
    p.add_argument("packet_path", help="Path to tmp/wiki-runs/<run-id>/packet.json.")
    p.add_argument(
        "--provider",
        choices=WRITER_PROVIDERS,
        default=None,
        help="Writer provider adapter.",
    )
    p.add_argument(
        "--mode",
        choices=WRITER_PROVIDERS,
        dest="provider",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing draft files.",
    )
    return p


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_file(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite to replace it")
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: dict[str, Any], overwrite: bool) -> None:
    write_file(path, json.dumps(value, indent=2) + "\n", overwrite)


def read_policy_status(run_dir: Path) -> str:
    policy_path = run_dir / "policy.json"
    if not policy_path.exists():
        return "unknown"
    policy = load_json(policy_path)
    return str(policy.get("status", "unknown"))


def stub_readme_text(packet: dict[str, Any], policy_status: str) -> str:
    return "\n".join(
        [
            "# Draft Stub",
            "",
            "This directory is the writer output slot for a no-write wiki run.",
            "",
            f"- Writer provider: `stub`",
            f"- Source path: `{packet['source_path']}`",
            f"- Primary home: `{packet['primary_home']}`",
            f"- Page-home mode: `{packet['page_home_decision']['mode']}`",
            f"- Policy status: `{policy_status}`",
            "",
            "No model-generated content has been produced yet.",
            "",
        ]
    )


def stub_page_text(packet: dict[str, Any]) -> str:
    expected_files = packet.get("expected_touched_files", [])
    touched = "\n".join(f"- `{path}`" for path in expected_files) or "- none"
    return "\n".join(
        [
            "# Source Draft Stub",
            "",
            f"Writer provider: `stub`",
            f"Source path: `{packet['source_path']}`",
            f"Primary home: `{packet['primary_home']}`",
            f"Page-home mode: `{packet['page_home_decision']['mode']}`",
            "",
            "## Expected Touched Files",
            "",
            touched,
            "",
            "## Writer Status",
            "",
            "No writer model has been run. This file reserves the draft output slot only.",
            "",
        ]
    )


def draft_manifest(packet: dict[str, Any], stub_path: Path) -> dict[str, Any]:
    expected_files = packet.get("expected_touched_files", [])
    operations: list[dict[str, Any]] = []
    for target_path in expected_files:
        operations.append(
            {
                "op": "create",
                "target_path": str(target_path),
                "draft_path": str(stub_path),
                "status": "stub",
            }
        )
    if not operations:
        operations.append(
            {
                "op": "no_op",
                "target_path": "",
                "draft_path": None,
                "status": "stub",
            }
        )

    return {
        "manifest_version": "wiki-draft-manifest.v1",
        "source_path": packet["source_path"],
        "primary_home": packet["primary_home"],
        "operations": operations,
        "writes_wiki": False,
    }


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


def writer_metadata(provider: str, packet: dict[str, Any], draft_path: Path, run_dir: Path) -> dict[str, Any]:
    return {
        "writer_version": "wiki-writer.v1",
        "provider": provider,
        "source_path": packet["source_path"],
        "primary_home": packet["primary_home"],
        "draft_path": str(draft_path),
        "writes_wiki": False,
        "provider_metadata": {
            "visual_source_evidence": read_visual_source_evidence(run_dir, packet),
        },
    }


def write_stub(packet_path: Path, overwrite: bool) -> tuple[Path, Path]:
    packet = load_json(packet_path)
    run_dir = packet_path.parent
    draft_dir = run_dir / "draft"
    draft_dir.mkdir(exist_ok=True)

    target_slug = packet["target_slug"]
    readme_path = draft_dir / "README.md"
    stub_path = draft_dir / f"{target_slug}.md.stub"

    policy_status = read_policy_status(run_dir)
    write_file(readme_path, stub_readme_text(packet, policy_status), overwrite)
    write_file(stub_path, stub_page_text(packet), overwrite)
    write_json(draft_dir / "manifest.json", draft_manifest(packet, stub_path), overwrite)
    write_json(run_dir / "writer.json", writer_metadata("stub", packet, stub_path, run_dir), overwrite)
    return draft_dir, stub_path


def main() -> int:
    args = parser().parse_args()
    packet_path = Path(args.packet_path)
    provider = args.provider or "stub"

    if provider == "stub":
        draft_dir, stub_path = write_stub(packet_path, args.overwrite)
    else:
        raise ValueError(f"unsupported writer provider: {provider}")

    print(f"Writer provider: {provider}")
    print(f"Draft directory: {draft_dir}")
    print(f"Draft stub: {stub_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"wiki_writer error: {exc}", file=sys.stderr)
        sys.exit(1)
