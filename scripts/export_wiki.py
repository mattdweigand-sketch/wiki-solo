#!/usr/bin/env python3
"""Build and verify a wiki export zip.

The export includes gitignored raw sources, but excludes local scratch,
deliverables, git internals, and private local settings. Upload and delivery are
handled by the workflow because they depend on local tool availability.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import date
from pathlib import Path


DEFAULT_EXCLUDES = (
    ".git/",
    ".agents/",
    "tmp/",
    "deliverables/",
    ".claude/worktrees/",
)
DEFAULT_EXCLUDE_FILES = {
    ".claude/settings.local.json",
    ".env",
}
REQUIRED_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTEXT.md",
    "LICENSE",
    "README.md",
    "REFERENCES.md",
    "SETUP.md",
}
REQUIRED_PREFIXES = (
    ".claude/commands/",
    ".codex/skills/",
    ".github/workflows/",
    "raw/",
    "scripts/",
    "wiki/",
    "workflows/",
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build and verify a complete wiki export zip.")
    p.add_argument("--date", default=date.today().isoformat(), help="Date stamp for the export filename.")
    p.add_argument("--output-dir", default="tmp", help="Directory for the export zip.")
    p.add_argument("--repo-root", default=".", help="Repository root to export.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List how many files would be exported without writing the zip.",
    )
    return p


def should_exclude(rel: str) -> bool:
    if rel in DEFAULT_EXCLUDE_FILES:
        return True
    if rel.endswith(".zip") or rel.endswith(".DS_Store"):
        return True
    return any(rel.startswith(prefix) for prefix in DEFAULT_EXCLUDES)


def export_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if should_exclude(rel):
            continue
        files.append(path)
    return files


def zip_path(repo_root: Path, output_dir: str, stamp: str) -> Path:
    out_dir = repo_root / output_dir
    return out_dir / f"wiki-export-{stamp}.zip"


def build_zip(repo_root: Path, output: Path, files: list[Path]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(repo_root).as_posix())


def validate_names(names: list[str]) -> list[str]:
    errors: list[str] = []
    name_set = set(names)
    for required in sorted(REQUIRED_FILES):
        if required not in name_set:
            errors.append(f"archive does not contain {required}")
    for prefix in REQUIRED_PREFIXES:
        if not any(name.startswith(prefix) for name in names):
            errors.append(f"archive does not contain {prefix}")
    for name in names:
        if should_exclude(name):
            errors.append(f"archive contains excluded path {name}")
    return errors


def verify_zip(output: Path, expected_count: int) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not output.exists():
        return False, [f"{output} was not created"]
    with zipfile.ZipFile(output) as zf:
        names = zf.namelist()
        corrupt = zf.testzip()
    if corrupt:
        errors.append(f"corrupt zip member: {corrupt}")
    errors.extend(validate_names(names))
    if len(names) != expected_count:
        errors.append(f"archive file count {len(names)} did not match expected {expected_count}")
    return not errors, errors


def main() -> int:
    args = parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    files = export_files(repo_root)
    output = zip_path(repo_root, args.output_dir, args.date)

    if args.dry_run:
        names = [path.relative_to(repo_root).as_posix() for path in files]
        errors = validate_names(names)
        print(f"Export dry run: {len(files)} file(s) would be written to {output}")
        print("Required export coverage: " + ("yes" if not errors else "no"))
        for error in errors:
            print(f"- {error}")
        return 0 if not errors else 1

    build_zip(repo_root, output, files)
    ok, errors = verify_zip(output, len(files))
    if not ok:
        print("Wiki export verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Wiki export created: {output}")
    print(f"Files included: {len(files)}")
    print(f"Size bytes: {output.stat().st_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
