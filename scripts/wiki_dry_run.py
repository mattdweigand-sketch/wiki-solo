#!/usr/bin/env python3
"""Emit a no-write wiki maintenance dry-run packet.

This script performs deterministic repo inspection only. It does not call a
model and does not write files. Run from the repo root:

    python3 scripts/wiki_dry_run.py raw/customer-research/example.md
    python3 scripts/wiki_dry_run.py raw/product-specs/example.md --format yaml
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(".")
RAW_ROOT = Path("raw")
WIKI_ROOT = Path("wiki")
SOURCE_ROOT = WIKI_ROOT / "sources"

TASK_TYPES = {"ingest", "promotion_audit", "lint_followup", "research_capture"}
SOURCE_TYPE_BY_RAW_DIR = {
    "analyst-reports": "analyst-report",
    "ai-research": "analyst-report",
    "battlecards": "sales-battlecard",
    "board-docs": "board-doc",
    "call-transcripts": "call-transcript",
    "competitive-intel": "competitor-collateral",
    "competitor-collateral": "competitor-collateral",
    "crm-exports": "crm-export",
    "customer-research": "call-transcript",
    "decks": "deck",
    "exec-memos": "exec-memo",
    "help-docs": "help-doc",
    "internal-memos": "exec-memo",
    "press": "press",
    "product-specs": "product-spec",
    "release-notes": "release-note",
    "research": "other",
    "sales-battlecards": "sales-battlecard",
    "slack-threads": "slack-thread",
    "social": "press",
    "strategy-docs": "strategy-doc",
    "syntheses": "synthesis",
    "videos": "synthesis",
}
SUPPORTED_SOURCE_EXTENSIONS = {".md", ".txt", ".pdf", ".xlsx", ".csv", ".json"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Produce a structured no-write dry-run packet for wiki work.",
    )
    p.add_argument("source_path", help="Path to a raw source artifact.")
    p.add_argument(
        "--task-type",
        choices=sorted(TASK_TYPES),
        default="ingest",
        help="Dry-run task route.",
    )
    p.add_argument(
        "--target-slug",
        default="",
        help="Override the inferred source page slug.",
    )
    p.add_argument(
        "--format",
        choices=["json", "yaml", "markdown"],
        default="json",
        help="Output format. YAML and Markdown are emitted with stdlib helpers.",
    )
    p.add_argument(
        "--validate-schema",
        action="store_true",
        help="Validate the dry-run packet shape before printing.",
    )
    return p


def normalize_path(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        try:
            return path.relative_to(Path.cwd())
        except ValueError:
            return path
    return path


def slug_from_source(path: Path) -> str:
    stem = path.stem.lower()
    stem = DATE_PREFIX_RE.sub("", stem)
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    stem = re.sub(r"-+", "-", stem).strip("-")
    return stem or "source"


def infer_source_type(path: Path) -> str:
    try:
        parts = path.relative_to(RAW_ROOT).parts
    except ValueError:
        return "other"
    if len(parts) < 2:
        return "other"
    return SOURCE_TYPE_BY_RAW_DIR.get(parts[0], "other")


def git_check_ignore(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def git_tracked(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def expected_files(
    task_type: str,
    source_path: Path,
    primary_home: Path,
    source_exists: bool,
) -> list[str]:
    if task_type != "ingest":
        return []
    if source_exists or not source_path.exists() or not is_under(source_path, RAW_ROOT):
        return []

    files: list[Path] = []
    files.append(primary_home)
    files.extend([WIKI_ROOT / "index.md", WIKI_ROOT / "log.md"])
    return [str(p) for p in files]


def page_home_decision(
    task_type: str,
    source_path: Path,
    primary_home: Path,
    source_exists: bool,
) -> dict[str, str]:
    if task_type != "ingest":
        return {
            "mode": "no_op",
            "rationale": "This first dry-run version only infers ingest homes deterministically.",
        }

    if source_exists:
        return {
            "mode": "no_op",
            "rationale": f"{primary_home} already exists; a model-free dry run cannot justify edits.",
        }

    if source_path.exists() and is_under(source_path, RAW_ROOT):
        return {
            "mode": "source_only",
            "rationale": "The raw artifact exists under raw/ and can be represented by a source page before downstream synthesis.",
        }

    return {
        "mode": "no_op",
        "rationale": "The source path is missing or outside raw/, so no durable wiki target is safe to propose.",
    }


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def risk_flags(
    source_path: Path,
    source_type: str,
    primary_home: Path,
    source_exists: bool,
    ignored: bool,
    tracked: bool,
    target_slug: str,
) -> list[str]:
    flags: list[str] = []
    suffix = source_path.suffix.lower()

    if not source_path.exists():
        flags.append("source_path_missing")
    if not is_under(source_path, RAW_ROOT):
        flags.append("source_path_outside_raw")
    if suffix not in SUPPORTED_SOURCE_EXTENSIONS | SUPPORTED_IMAGE_EXTENSIONS:
        flags.append("unsupported_source_extension")
    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        flags.append("visual_source_requires_review")
    try:
        raw_parts = source_path.relative_to(RAW_ROOT).parts
    except ValueError:
        raw_parts = ()
    if raw_parts and raw_parts[0] == "social":
        flags.append("social_source_requires_review")
    if raw_parts and raw_parts[0] not in SOURCE_TYPE_BY_RAW_DIR:
        flags.append("unknown_source_type")
    if ignored:
        flags.append("raw_path_gitignored")
    if is_under(source_path, RAW_ROOT) and not tracked:
        flags.append("raw_path_untracked")
    if source_exists:
        flags.append("source_page_exists")
    if not KEBAB_RE.match(target_slug):
        flags.append("target_slug_not_kebab_case")
    if primary_home.exists() and not source_exists:
        flags.append("primary_home_conflict")

    return flags


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    source_path = normalize_path(args.source_path)
    target_slug = args.target_slug or slug_from_source(source_path)
    primary_home = SOURCE_ROOT / f"{target_slug}.md"
    source_exists = primary_home.exists()
    source_type = infer_source_type(source_path)
    ignored = git_check_ignore(source_path)
    tracked = git_tracked(source_path)

    flags = risk_flags(
        source_path=source_path,
        source_type=source_type,
        primary_home=primary_home,
        source_exists=source_exists,
        ignored=ignored,
        tracked=tracked,
        target_slug=target_slug,
    )

    return {
        "schema_version": "wiki-dry-run-packet.v1",
        "task_type": args.task_type,
        "source_path": str(source_path),
        "source_path_exists": source_path.exists(),
        "source_gitignored": ignored,
        "source_tracked": tracked,
        "inferred_source_type": source_type,
        "target_slug": target_slug,
        "primary_home": str(primary_home),
        "primary_home_exists": source_exists,
        "page_home_decision": page_home_decision(
            args.task_type,
            source_path,
            primary_home,
            source_exists,
        ),
        "expected_touched_files": expected_files(
            args.task_type,
            source_path,
            primary_home,
            source_exists,
        ),
        "risk_flags": flags,
        "proposed_links": [],
        "human_review_required": True,
        "writes_files": False,
    }


def validate_packet(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_types = {
        "schema_version": str,
        "task_type": str,
        "source_path": str,
        "source_path_exists": bool,
        "source_gitignored": bool,
        "source_tracked": bool,
        "inferred_source_type": str,
        "target_slug": str,
        "primary_home": str,
        "primary_home_exists": bool,
        "page_home_decision": dict,
        "expected_touched_files": list,
        "risk_flags": list,
        "proposed_links": list,
        "human_review_required": bool,
        "writes_files": bool,
    }
    for key, expected_type in required_types.items():
        if key not in packet:
            errors.append(f"missing required field: {key}")
        elif not isinstance(packet[key], expected_type):
            errors.append(f"{key} must be {expected_type.__name__}")

    if packet.get("schema_version") != "wiki-dry-run-packet.v1":
        errors.append("schema_version must be wiki-dry-run-packet.v1")
    if packet.get("task_type") not in TASK_TYPES:
        errors.append("task_type is not a supported route")
    if packet.get("writes_files") is not False:
        errors.append("dry-run packets must have writes_files=false")
    if packet.get("human_review_required") is not True:
        errors.append("dry-run packets must have human_review_required=true")

    target_slug = packet.get("target_slug")
    primary_home = packet.get("primary_home")
    if isinstance(target_slug, str):
        if not KEBAB_RE.match(target_slug):
            errors.append("target_slug must be kebab-case")
        if isinstance(primary_home, str) and primary_home != f"wiki/sources/{target_slug}.md":
            errors.append("primary_home must match target_slug under wiki/sources/")

    decision = packet.get("page_home_decision")
    if isinstance(decision, dict):
        mode = decision.get("mode")
        rationale = decision.get("rationale")
        if mode not in {
            "source_only",
            "source_plus_existing_updates",
            "source_plus_new_analysis",
            "no_op",
        }:
            errors.append("page_home_decision.mode is invalid")
        if not isinstance(rationale, str) or not rationale:
            errors.append("page_home_decision.rationale must be a non-empty string")

    for key in ("expected_touched_files", "risk_flags"):
        if isinstance(packet.get(key), list):
            for index, value in enumerate(packet[key]):
                if not isinstance(value, str):
                    errors.append(f"{key}[{index}] must be a string")
            if len(packet[key]) != len(set(packet[key])):
                errors.append(f"{key} must not contain duplicates")

    touched = packet.get("expected_touched_files")
    if isinstance(touched, list):
        for path in touched:
            if isinstance(path, str) and path.startswith("raw/"):
                errors.append("expected_touched_files must not include raw paths")

    if isinstance(packet.get("proposed_links"), list):
        for index, link in enumerate(packet["proposed_links"]):
            if not isinstance(link, dict):
                errors.append(f"proposed_links[{index}] must be an object")

    return errors


def yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or any(ch in text for ch in ":#[]{}\"\n"):
        return json.dumps(text)
    return text


def to_yaml(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {yaml_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return f"{pad}[]"
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(to_yaml(item, indent + 2))
            else:
                lines.append(f"{pad}- {yaml_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{yaml_scalar(value)}"


def to_markdown(packet: dict[str, Any]) -> str:
    decision = packet["page_home_decision"]
    lines = [
        "# Wiki Dry Run",
        "",
        f"- Task type: `{packet['task_type']}`",
        f"- Source path: `{packet['source_path']}`",
        f"- Primary home: `{packet['primary_home']}`",
        f"- Page-home mode: `{decision['mode']}`",
        f"- Human review required: `{str(packet['human_review_required']).lower()}`",
        f"- Writes files: `{str(packet['writes_files']).lower()}`",
        "",
        "## Rationale",
        "",
        decision["rationale"],
        "",
        "## Expected Touched Files",
        "",
    ]
    if packet["expected_touched_files"]:
        lines.extend(f"- `{path}`" for path in packet["expected_touched_files"])
    else:
        lines.append("- none")

    lines.extend(["", "## Risk Flags", ""])
    if packet["risk_flags"]:
        lines.extend(f"- `{flag}`" for flag in packet["risk_flags"])
    else:
        lines.append("- none")

    lines.extend(["", "## Proposed Links", ""])
    if packet["proposed_links"]:
        for link in packet["proposed_links"]:
            lines.append(f"- `{link.get('label', 'Related')}`: `{link.get('target', '')}`")
    else:
        lines.append("- none")

    return "\n".join(lines)


def main() -> int:
    args = parser().parse_args()
    packet = build_packet(args)
    errors = validate_packet(packet)
    if args.validate_schema and errors:
        for error in errors:
            print(f"schema error: {error}", file=sys.stderr)
        return 4

    if args.format == "json":
        print(json.dumps(packet, indent=2, sort_keys=False))
    elif args.format == "yaml":
        print(to_yaml(packet))
    else:
        print(to_markdown(packet))
    return 0


if __name__ == "__main__":
    sys.exit(main())
