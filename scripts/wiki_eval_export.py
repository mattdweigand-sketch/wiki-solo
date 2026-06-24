#!/usr/bin/env python3
"""Regression eval for export_wiki.py template include/exclude boundaries."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from eval_lib import Results


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT = REPO_ROOT / "scripts" / "export_wiki.py"

results = Results()


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


with tempfile.TemporaryDirectory(prefix="wiki-export-eval-") as td:
    root = Path(td)
    required_files = [
        ".gitignore",
        "AGENTS.md",
        "CLAUDE.md",
        "CONTEXT.md",
        "LICENSE",
        "README.md",
        "REFERENCES.md",
        "SETUP.md",
    ]
    for rel in required_files:
        write(root / rel)
    for rel in [
        ".claude/commands/wiki-ingest.md",
        ".codex/skills/wiki-ingest/SKILL.md",
        ".github/workflows/wiki-ci.yml",
        "raw/README.md",
        "raw/.gitkeep",
        "raw/customer-research/source.txt",
        "scripts/lint.py",
        "wiki/index.md",
        "workflows/maintenance/export.md",
    ]:
        write(root / rel)
    for rel in [
        ".env",
        ".claude/settings.local.json",
        ".claude/worktrees/private.txt",
        ".git/config",
        "deliverables/output/file.txt",
        "tmp/scratch.txt",
        "tmp/wiki-export-2026-06-24.zip",
        "wiki/.DS_Store",
    ]:
        write(root / rel)

    dry = subprocess.run(
        [sys.executable, str(EXPORT), "--repo-root", str(root), "--dry-run", "--date", "2026-06-24"],
        text=True,
        capture_output=True,
        check=False,
    )
    results.record(
        "dry-run-verifies-template-coverage",
        dry.returncode == 0 and "Required export coverage: yes" in dry.stdout,
        dry.stdout.replace("\n", " | ") + dry.stderr.replace("\n", " | "),
    )

    build = subprocess.run(
        [sys.executable, str(EXPORT), "--repo-root", str(root), "--date", "2026-06-24"],
        text=True,
        capture_output=True,
        check=False,
    )
    zip_path = root / "tmp" / "wiki-export-2026-06-24.zip"
    names: set[str] = set()
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
    required_present = all(rel in names for rel in required_files)
    prefixes_present = all(
        any(name.startswith(prefix) for name in names)
        for prefix in (
            ".claude/commands/",
            ".codex/skills/",
            ".github/workflows/",
            "raw/",
            "scripts/",
            "wiki/",
            "workflows/",
        )
    )
    excluded_absent = all(
        rel not in names
        for rel in (
            ".env",
            ".claude/settings.local.json",
            ".claude/worktrees/private.txt",
            ".git/config",
            "deliverables/output/file.txt",
            "tmp/scratch.txt",
            "tmp/wiki-export-2026-06-24.zip",
            "wiki/.DS_Store",
        )
    )
    results.record(
        "build-includes-required-and-excludes-local",
        build.returncode == 0 and required_present and prefixes_present and excluded_absent,
        "stdout: " + build.stdout.replace("\n", " | ") + " names: " + repr(sorted(names)),
    )

sys.exit(results.finish())
