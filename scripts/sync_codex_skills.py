#!/usr/bin/env python3
"""Manage duplicate global Codex installs for the wiki skills.

Codex now discovers the repo copy under .codex/skills/wiki-* directly. Keeping
identical global copies under ~/.codex/skills/wiki-* creates duplicate slash
commands, so this helper detects and removes those old global installs.

--check reports every existing global wiki-* install and how it differs from the
repo source. --remove-global deletes only the installs confirmed byte-identical
to the repo source; a divergent global copy (one that --check reports as
differs/extra/missing) is left in place and reported, so a customized global
wrapper is never destroyed silently. Pair --remove-global with --dry-run to see
exactly what would be deleted first.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / ".codex" / "skills"
EXPECTED_SKILLS = (
    "wiki-capture",
    "wiki-eval",
    "wiki-export",
    "wiki-ingest",
    "wiki-lint",
    "wiki-promote",
    "wiki-synthesize",
)

# The two live tracked wrapper surfaces. Each must cover the same
# EXPECTED_SKILLS names. .claude/commands holds one .md per skill; .codex/skills
# holds one <skill>/SKILL.md per skill.
WRAPPER_SURFACES = (
    ("claude-commands", REPO_ROOT / ".claude" / "commands", "{name}.md"),
    ("codex-skills", REPO_ROOT / ".codex" / "skills", "{name}/SKILL.md"),
)

# Thin-wrapper rule (AGENTS.md): a wrapper may carry at most one canonical
# command hint and no multi-step procedure. A second scripts/*.py reference or a
# numbered-step list means procedure has leaked into the wrapper.
SCRIPT_REF_RE = re.compile(r"scripts/[A-Za-z0-9_./-]*\.py")
NUMBERED_STEP_RE = re.compile(r"^\s*[0-9]+\.\s")


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
        help="Remove confirmed-identical global ~/.codex/skills/wiki-* directories.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --remove-global, print what would be removed without deleting.",
    )
    parser.add_argument(
        "--wrapper-parity",
        action="store_true",
        help="Verify the .claude/commands and .codex/skills wrapper surfaces "
        "cover the same wiki-* names and stay thin.",
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


def duplicate_status(source: Path, target: Path) -> list[str]:
    if not target.exists():
        return []

    source_files = files_under(source)
    target_files = files_under(target)
    messages = [f"duplicate global wiki skill: {target}"]

    for rel in sorted(source_files - target_files):
        messages.append(f"  missing global file compared with repo source: {target / rel}")
    for rel in sorted(target_files - source_files):
        messages.append(f"  extra global file compared with repo source: {target / rel}")
    for rel in sorted(source_files & target_files):
        if not filecmp.cmp(source / rel, target / rel, shallow=False):
            messages.append(f"  differs from repo source: {target / rel}")
    return messages


def is_identical_duplicate(source: Path, target: Path) -> bool:
    """True only when target exists and matches source byte-for-byte.

    duplicate_status emits the bare header line for any existing target and one
    extra line per missing/extra/differing file. An identical install is the
    one case that produces exactly the header and nothing more.
    """
    status = duplicate_status(source, target)
    return len(status) == 1


def remove_tree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file() or child.is_symlink():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()
    print(f"Removed duplicate global wiki skill: {path}")


def wrapper_parity_problems(repo_root: Path = REPO_ROOT) -> list[str]:
    """Check the live tracked wrapper surfaces stay thin and mutually consistent.

    Returns a list of human-readable problems (empty when all surfaces are in
    sync). Catches:
      - a surface that does not cover all EXPECTED_SKILLS names (drop/add drift),
      - a surface that carries an extra wiki-* wrapper not in EXPECTED_SKILLS,
      - a wrapper body with more than one scripts/*.py reference or a
        numbered-step list (procedure leaking into a thin pointer).
    """
    problems: list[str] = []
    expected = set(EXPECTED_SKILLS)

    for label, root, pattern in WRAPPER_SURFACES:
        if not root.exists():
            problems.append(f"{label}: wrapper surface missing: {root}")
            continue

        if pattern.endswith("/SKILL.md"):
            present = {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("wiki-")}
        else:
            present = {p.stem for p in root.glob("wiki-*.md")}

        for missing in sorted(expected - present):
            problems.append(f"{label}: missing wrapper for {missing}")
        for extra in sorted(present - expected):
            problems.append(f"{label}: unexpected wiki-* wrapper {extra}")

        for name in sorted(expected & present):
            wrapper = root / pattern.format(name=name)
            if not wrapper.exists():
                problems.append(f"{label}: missing wrapper file {wrapper}")
                continue
            text = wrapper.read_text(encoding="utf-8")
            script_refs = SCRIPT_REF_RE.findall(text)
            if len(script_refs) > 1:
                problems.append(
                    f"{label}/{name}: {len(script_refs)} scripts/*.py references "
                    f"(thin wrappers allow at most one canonical command hint): "
                    f"{', '.join(sorted(set(script_refs)))}"
                )
            step_lines = [
                line for line in text.splitlines() if NUMBERED_STEP_RE.match(line)
            ]
            if step_lines:
                problems.append(
                    f"{label}/{name}: wrapper contains a numbered-step list "
                    f"(procedure belongs only in workflows/): {step_lines[0].strip()!r}"
                )

    return problems


def main() -> int:
    args = parse_args()

    if args.wrapper_parity:
        problems = wrapper_parity_problems()
        if problems:
            print("Wrapper-parity problems found:")
            for problem in problems:
                print(f"  - {problem}")
            return 1
        print("Wrapper surfaces are in parity and thin.")
        return 0

    sources = ensure_sources()
    target_root = codex_home() / "skills"

    if not args.check and not args.remove_global:
        print("Choose --check, --remove-global, or --wrapper-parity.", file=sys.stderr)
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

    skipped = []
    to_remove = []
    for source in sources:
        target = target_root / source.name
        if not target.exists():
            continue
        if is_identical_duplicate(source, target):
            to_remove.append(target)
        else:
            skipped.append(target)

    for target in skipped:
        print(
            f"Skipping divergent global wiki skill (not identical to repo source): {target}",
            file=sys.stderr,
        )
        print("  Reconcile or remove it by hand; --remove-global only deletes confirmed duplicates.", file=sys.stderr)

    if not to_remove:
        print("No confirmed-identical global wiki Codex skills to remove.")
        return 1 if skipped else 0

    if args.dry_run:
        print("Dry run: would remove confirmed-identical global wiki Codex skills:")
        for target in to_remove:
            print(f"  - {target}")
        return 1 if skipped else 0

    for target in to_remove:
        remove_tree(target)
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
