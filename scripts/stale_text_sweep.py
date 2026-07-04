#!/usr/bin/env python3
"""Read-only helper for ingest stale-text sweeps.

Runs the same search an agent would otherwise run by hand:
    rg -n -i -- <phrase> <root>

The helper only collects evidence. It does not classify hits as stale, current,
or historical, and it never edits wiki or raw files.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


def command_string(phrase: str, root: Path) -> str:
    parts = ["rg", "-n", "-i", "--", phrase, str(root)]
    return " ".join(shlex.quote(part) for part in parts)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run read-only rg stale-text sweeps and emit log-ready proof."
    )
    p.add_argument(
        "--phrase",
        action="append",
        required=True,
        help="Text to search for. Repeat for multiple phrasings.",
    )
    p.add_argument(
        "--root",
        default="wiki",
        help="Root to search. Defaults to wiki.",
    )
    p.add_argument(
        "--pages-fixed",
        action="append",
        default=[],
        help="Page fixed after agent review. Repeatable; copied into proof JSON.",
    )
    p.add_argument(
        "--historical-no-change-hit",
        action="append",
        default=[],
        help="Reviewed hit preserved as historical/no-change. Repeatable.",
    )
    return p


def count_hits(rg_stdout: str) -> tuple[int, dict[str, int]]:
    per_file: dict[str, int] = {}
    total = 0
    for line in rg_stdout.splitlines():
        if not line:
            continue
        path, sep, _rest = line.partition(":")
        if not sep:
            continue
        total += 1
        per_file[path] = per_file.get(path, 0) + 1
    return total, per_file


def run_search(phrase: str, root: Path) -> tuple[str, int, dict[str, int], int]:
    cmd = ["rg", "-n", "-i", "--", phrase, str(root)]
    shown = command_string(phrase, root)
    print(f"Command: {shown}")
    proc = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    elif proc.returncode == 1:
        print("Matches: none")
    if proc.stderr:
        print(
            proc.stderr,
            end="" if proc.stderr.endswith("\n") else "\n",
            file=sys.stderr,
        )

    if proc.returncode not in (0, 1):
        return shown, 0, {}, proc.returncode
    hits, per_file = count_hits(proc.stdout)
    return shown, hits, per_file, 0


def main() -> int:
    args = parser().parse_args()
    root = Path(args.root)
    if not root.exists():
        print(f"error: root does not exist: {root}", file=sys.stderr)
        return 2
    for phrase in args.phrase:
        if not phrase.strip():
            print("error: --phrase must not be empty", file=sys.stderr)
            return 2

    commands: list[str] = []
    total_hits = 0
    per_file: dict[str, int] = {}

    for phrase in args.phrase:
        shown, hits, file_hits, code = run_search(phrase, root)
        commands.append(shown)
        if code:
            return code
        total_hits += hits
        for path, count in file_hits.items():
            per_file[path] = per_file.get(path, 0) + count

    print(f"Total hits: {total_hits}")
    print("Per-file hits:")
    if per_file:
        for path in sorted(per_file):
            print(f"  {path}: {per_file[path]}")
    else:
        print("  none")

    print(
        "Stale-text sweep: status=completed; "
        f"commands={json.dumps(commands)}; "
        f"hit_count={total_hits}; "
        f"pages_fixed={json.dumps(args.pages_fixed)}; "
        "historical_no_change_hits="
        f"{json.dumps(args.historical_no_change_hit)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
