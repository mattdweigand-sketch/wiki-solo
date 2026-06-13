#!/usr/bin/env python3
"""Compatibility wrapper for the stub wiki writer provider."""

from __future__ import annotations

import argparse
import subprocess
import sys


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Create no-model draft placeholders for a wiki run.")
    p.add_argument("packet_path", help="Path to tmp/wiki-runs/<run-id>/packet.json.")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing stub draft files.",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    command = [
        sys.executable,
        "scripts/wiki_writer.py",
        args.packet_path,
        "--provider",
        "stub",
    ]
    if args.overwrite:
        command.append("--overwrite")
    result = subprocess.run(command, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
