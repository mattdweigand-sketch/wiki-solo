#!/usr/bin/env python3
"""Run no-write semantic artifact stubs for a wiki run.

This command is a convenience wrapper over the provider-shaped semantic slots:
visual evidence extractor, classifier, contradiction detector, and link scorer.
It writes only under the given tmp/wiki-runs/<run-id>/ directory.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SEMANTIC_COMMANDS = [
    ("visual_extractor", "scripts/wiki_visual_extractor.py"),
    ("classifier", "scripts/wiki_classifier.py"),
    ("contradiction_detector", "scripts/wiki_contradiction_detector.py"),
    ("link_scorer", "scripts/wiki_link_scorer.py"),
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run no-write semantic stubs for a wiki run.")
    p.add_argument("run_dir", help="Path to tmp/wiki-runs/<run-id>.")
    p.add_argument(
        "--provider",
        choices=["stub"],
        default="stub",
        help="Semantic provider adapter. Only stub is implemented.",
    )
    p.add_argument("--overwrite", action="store_true")
    return p


def run_semantic_command(
    name: str,
    script: str,
    run_dir: Path,
    provider: str,
    overwrite: bool,
) -> tuple[int, str]:
    command = [
        sys.executable,
        script,
        str(run_dir),
        "--provider",
        provider,
    ]
    if overwrite:
        command.append("--overwrite")

    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = result.stdout + result.stderr
    return result.returncode, f"{name}: {output.strip()}"


def main() -> int:
    args = parser().parse_args()
    run_dir = Path(args.run_dir)
    failures: list[str] = []

    for name, script in SEMANTIC_COMMANDS:
        code, output = run_semantic_command(name, script, run_dir, args.provider, args.overwrite)
        print(output)
        if code != 0:
            failures.append(f"{name} exited {code}")

    if failures:
        print("FAIL wiki-semantic")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("PASS wiki-semantic")
    return 0


if __name__ == "__main__":
    sys.exit(main())
