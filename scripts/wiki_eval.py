#!/usr/bin/env python3
"""Run the wiki autonomy harness evaluation suite.

This is the single entrypoint for deterministic checks around the dry-run
harness. It composes focused scripts rather than duplicating their logic.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


SUITES = {
    "apply": [sys.executable, "scripts/wiki_eval_apply.py"],
    "ingest": [sys.executable, "scripts/wiki_eval_fixtures.py"],
    "pipeline": [sys.executable, "scripts/wiki_eval_pipeline.py"],
    "policy": [sys.executable, "scripts/wiki_eval_policy.py"],
    "provider": [sys.executable, "scripts/wiki_eval_provider.py"],
    "route": [sys.executable, "scripts/wiki_eval_route.py"],
    "run": [sys.executable, "scripts/wiki_eval_run.py"],
    "semantic": [sys.executable, "scripts/wiki_eval_semantic.py"],
    "tier1": [sys.executable, "scripts/lint.py", "--tier1"],
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run wiki dry-run harness evals.")
    p.add_argument(
        "--suite",
        action="append",
        choices=sorted(SUITES),
        help="Suite to run. Repeat for multiple suites. Defaults to all.",
    )
    return p


def run_suite(name: str, command: list[str]) -> int:
    print(f"== {name} ==", flush=True)
    result = subprocess.run(command, check=False)
    print()
    return result.returncode


def main() -> int:
    args = parser().parse_args()
    suite_names = args.suite or [
        "ingest",
        "policy",
        "route",
        "run",
        "apply",
        "semantic",
        "pipeline",
        "provider",
        "tier1",
    ]

    failures: list[str] = []
    for name in suite_names:
        code = run_suite(name, SUITES[name])
        if code != 0:
            failures.append(f"{name} exited {code}")

    if failures:
        print("Wiki eval failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Wiki eval passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
