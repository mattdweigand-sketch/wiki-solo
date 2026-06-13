#!/usr/bin/env python3
"""Sync tracked wiki Codex skills into the local Codex install directory.

The repo copy under .codex/skills/wiki-* is the source of truth. The installed
copy under ~/.codex/skills/wiki-* is local runtime state.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / ".codex" / "skills"
EXPECTED_SKILLS = (
    "wiki-capture",
    "wiki-export",
    "wiki-ingest",
    "wiki-lint",
    "wiki-promote",
    "wiki-synthesize",
)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync tracked wiki Codex skill wrappers into ~/.codex/skills.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without writing installed skill files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without writing installed skill files.",
    )
    return parser.parse_args()


def ensure_sources() -> list[Path]:
    missing = []
    sources = []
    for name in EXPECTED_SKILLS:
        path = SOURCE_ROOT / name
        skill = path / "SKILL.md"
        if not skill.exists():
            missing.append(str(skill.relative_to(REPO_ROOT)))
        sources.append(path)
    if missing:
        print("Missing tracked Codex skill source(s):", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        sys.exit(2)
    return sources


def files_under(path: Path) -> set[Path]:
    return {
        child.relative_to(path)
        for child in path.rglob("*")
        if child.is_file()
    }


def drift(source: Path, target: Path) -> list[str]:
    if not target.exists():
        return [f"missing target: {target}"]

    source_files = files_under(source)
    target_files = files_under(target)
    messages = []

    for rel in sorted(source_files - target_files):
        messages.append(f"missing installed file: {target / rel}")
    for rel in sorted(target_files - source_files):
        messages.append(f"extra installed file: {target / rel}")
    for rel in sorted(source_files & target_files):
        if not filecmp.cmp(source / rel, target / rel, shallow=False):
            messages.append(f"differs: {target / rel}")
    return messages


def sync_skill(source: Path, target: Path, dry_run: bool) -> None:
    if dry_run:
        action = "update" if target.exists() else "install"
        print(f"Would {action}: {target}")
        return
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"Synced: {target}")


def main() -> int:
    args = parse_args()
    sources = ensure_sources()
    target_root = codex_home() / "skills"

    if args.check:
        failures = []
        for source in sources:
            target = target_root / source.name
            failures.extend(drift(source, target))
        if failures:
            print("Codex skill drift found:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print("Codex skill install matches tracked repo sources.")
        return 0

    if args.dry_run:
        print(f"Tracked source: {SOURCE_ROOT}")
        print(f"Install target: {target_root}")

    target_root.mkdir(parents=True, exist_ok=True)
    for source in sources:
        sync_skill(source, target_root / source.name, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
