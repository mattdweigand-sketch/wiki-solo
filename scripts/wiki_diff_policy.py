#!/usr/bin/env python3
"""Evaluate a wiki dry-run packet against deterministic diff policy.

The policy reads JSON from a file or stdin and writes a JSON report. It does
not inspect model output and does not write files.

Examples:
    python3 scripts/wiki_dry_run.py raw/videos/example.md | python3 scripts/wiki_diff_policy.py -
    python3 scripts/wiki_diff_policy.py packet.json --max-wiki-pages 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CORE_PREFIXES = ("workflows/", "scripts/", "schemas/")
ROOT_PROTECTED = {"AGENTS.md", "CLAUDE.md", "CONTEXT.md", "REFERENCES.md", "README.md"}
REVIEW_RISK_FLAGS = {
    "source_page_exists",
    "social_source_requires_review",
    "unknown_source_type",
    "visual_source_requires_review",
}
INFO_RISK_FLAGS = {
    "raw_path_gitignored",
    "raw_path_untracked",
}
REJECT_RISK_FLAGS = {
    "source_path_missing",
    "source_path_outside_raw",
    "unsupported_source_extension",
    "target_slug_not_kebab_case",
    "primary_home_conflict",
    "manual_referenced_by_edit",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Evaluate a dry-run packet against deterministic wiki diff policy.",
    )
    p.add_argument(
        "packet",
        help="JSON dry-run packet path, or '-' for stdin.",
    )
    p.add_argument(
        "--max-wiki-pages",
        type=int,
        default=8,
        help="Maximum expected wiki/*.md page touches before review is required.",
    )
    p.add_argument(
        "--allow-core-edits",
        action="store_true",
        help="Allow protected root, workflow, script, and schema paths.",
    )
    return p


def load_packet(path_text: str) -> dict[str, Any]:
    if path_text == "-":
        return json.load(sys.stdin)
    with Path(path_text).open(encoding="utf-8") as f:
        return json.load(f)


def touched_files(packet: dict[str, Any]) -> list[str]:
    value = packet.get("expected_touched_files", [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def is_wiki_page(path: str) -> bool:
    return path.startswith("wiki/") and path.endswith(".md")


def touches_core(path: str) -> bool:
    return path in ROOT_PROTECTED or path.startswith(CORE_PREFIXES)


def evaluate(packet: dict[str, Any], max_wiki_pages: int, allow_core_edits: bool) -> dict[str, Any]:
    files = touched_files(packet)
    risk_flags = packet.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        risk_flags = []
    risk_flags = [str(flag) for flag in risk_flags]

    rejects: list[str] = []
    reviews: list[str] = []
    passes: list[str] = []

    if packet.get("writes_files") is not False:
        rejects.append("packet must be a no-write dry run")
    else:
        passes.append("packet declares writes_files=false")

    for flag in risk_flags:
        if flag in REJECT_RISK_FLAGS:
            rejects.append(f"risk flag requires rejection: {flag}")
        elif flag in REVIEW_RISK_FLAGS:
            reviews.append(f"risk flag requires review: {flag}")
        elif flag in INFO_RISK_FLAGS:
            passes.append(f"informational risk flag observed: {flag}")

    raw_touches = [path for path in files if path.startswith("raw/")]
    if raw_touches:
        rejects.append("expected touched files include raw/ paths")
    else:
        passes.append("no raw/ files are proposed for mutation")

    core_touches = [path for path in files if touches_core(path)]
    if core_touches and not allow_core_edits:
        rejects.append("protected root/workflow/script/schema paths require explicit allowance")
    elif core_touches:
        reviews.append("protected paths were explicitly allowed")
    else:
        passes.append("no protected root/workflow/script/schema paths are proposed")

    wiki_pages = [path for path in files if is_wiki_page(path)]
    if len(wiki_pages) > max_wiki_pages:
        reviews.append(f"broad touch set: {len(wiki_pages)} wiki pages exceeds {max_wiki_pages}")
    else:
        passes.append(f"wiki page touch count within limit: {len(wiki_pages)}/{max_wiki_pages}")

    referenced_by_touches = [
        path for path in files if path.endswith(".md") and "referenced-by" in path.lower()
    ]
    if referenced_by_touches:
        rejects.append("expected touched files suggest manual Referenced by edits")

    if rejects:
        status = "reject"
    elif reviews:
        status = "review"
    else:
        status = "pass"

    return {
        "policy_version": "wiki-diff-policy.v1",
        "status": status,
        "rejects": rejects,
        "reviews": reviews,
        "passes": passes,
        "evaluated_touched_files": files,
    }


def main() -> int:
    args = parser().parse_args()
    packet = load_packet(args.packet)
    report = evaluate(
        packet,
        max_wiki_pages=args.max_wiki_pages,
        allow_core_edits=args.allow_core_edits,
    )
    print(json.dumps(report, indent=2))
    return 2 if report["status"] == "reject" else 0


if __name__ == "__main__":
    sys.exit(main())
