#!/usr/bin/env python3
"""Manage duplicate global Codex installs for the wiki skills.

Codex discovers the repo copy under .codex/skills/wiki-* directly while working
in the repo. Keeping identical global copies under ~/.codex/skills/wiki-* can
create duplicate slash commands, so this helper detects and removes those old
global installs. Divergent same-name global skills are reported but not removed
by --remove-global.
"""

from __future__ import annotations

import argparse
import filecmp
import os
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
        description="Detect or remove duplicate global wiki Codex skill wrappers.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether duplicate global wiki skills exist.",
    )
    parser.add_argument(
        "--remove-global",
        action="store_true",
        help="Remove duplicate global ~/.codex/skills/wiki-* directories.",
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


def tree_diff(source: Path, target: Path) -> list[str]:
    messages: list[str] = []
    source_files = files_under(source)
    target_files = files_under(target)

    for rel in sorted(source_files - target_files):
        messages.append(f"  missing global file compared with repo source: {target / rel}")
    for rel in sorted(target_files - source_files):
        messages.append(f"  extra global file compared with repo source: {target / rel}")
    for rel in sorted(source_files & target_files):
        if not filecmp.cmp(source / rel, target / rel, shallow=False):
            messages.append(f"  differs from repo source: {target / rel}")
    return messages


def duplicate_status(source: Path, target: Path) -> list[str]:
    if not target.exists():
        return []

    diff = tree_diff(source, target)
    if not diff:
        return [f"duplicate global wiki skill: {target}"]

    messages = [f"same-name global wiki skill differs from repo source: {target}"]
    messages.extend(diff)
    return messages


def is_identical_duplicate(source: Path, target: Path) -> bool:
    return target.exists() and not tree_diff(source, target)


def remove_tree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()
    print(f"Removed duplicate global wiki skill: {path}")


def main() -> int:
    args = parse_args()
    sources = ensure_sources()
    target_root = codex_home() / "skills"

    if not args.check and not args.remove_global:
        print("Choose --check or --remove-global.", file=sys.stderr)
        return 2

    statuses = []
    for source in sources:
        target = target_root / source.name
        statuses.extend(duplicate_status(source, target))

    if args.check:
        if statuses:
            print("Duplicate global wiki Codex skills found:")
            for status in statuses:
                print(f"  - {status}")
            print("Run: python3 scripts/sync_codex_skills.py --remove-global")
            return 1
        print("No duplicate global wiki Codex skills found.")
        return 0

    blocked = []
    for source in sources:
        target = target_root / source.name
        if not target.exists():
            continue
        if is_identical_duplicate(source, target):
            remove_tree(target)
            continue
        blocked.append((source, target, tree_diff(source, target)))

    if blocked:
        print("Refusing to remove non-identical global wiki skill(s):", file=sys.stderr)
        for _source, target, diff in blocked:
            print(f"  - {target}", file=sys.stderr)
            for message in diff:
                print(message, file=sys.stderr)
        print("Remove or reconcile those directories manually if they are intentional.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
