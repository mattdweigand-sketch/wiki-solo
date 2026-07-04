#!/usr/bin/env python3
"""Run the live wiki evaluation suites.

Entrypoint for the deterministic checks that guard live tooling. The SUITES
registry below is the single enumeration of what runs; each suite's own
docstring describes what it guards. The autonomy harness suites are archived
under archive/wiki-harness/ per decisions/archive-wiki-autonomy-harness;
restore them from there if the harness is reopened.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SUITES = {
    "parse": [sys.executable, "scripts/wiki_eval_parse.py"],
    "rebuild": [sys.executable, "scripts/wiki_eval_rebuild.py"],
    "lint": [sys.executable, "scripts/wiki_eval_lint.py"],
    "gate": [sys.executable, "scripts/wiki_eval_gate.py"],
    "capture-runs": [sys.executable, "scripts/validate_capture_runs.py"],
    "export": [sys.executable, "scripts/wiki_eval_export.py"],
    "rotate-log": [sys.executable, "scripts/wiki_eval_rotate_log.py"],
    "review-due": [sys.executable, "scripts/wiki_eval_review.py"],
    "stale-text-sweep": [sys.executable, "scripts/wiki_eval_stale_text_sweep.py"],
    "ledger-validators": [sys.executable, "scripts/wiki_eval_ledgers.py"],
    "wrapper-parity": [sys.executable, "scripts/wiki_eval_wrappers.py"],
    "tier1": [sys.executable, "scripts/lint.py", "--tier1"],
}


def unregistered_suites() -> list[str]:
    """wiki_eval_*.py files that appear in no registered suite command. A new
    suite file that is never added to SUITES would otherwise silently never
    run; this makes the default run fail loudly instead."""
    registered = {part for command in SUITES.values() for part in command}
    scripts_dir = Path(__file__).resolve().parent
    return sorted(
        p.name for p in scripts_dir.glob("wiki_eval_*.py")
        if f"scripts/{p.name}" not in registered
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run live wiki tooling evals.")
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
    # Default to every suite, derived from SUITES so a newly registered suite can
    # never be silently dropped from the default run by a forgotten list entry.
    suite_names = args.suite or list(SUITES)

    failures: list[str] = []
    orphans = unregistered_suites()
    if orphans:
        failures.append(
            "unregistered suite file(s) not in SUITES: " + ", ".join(orphans)
        )
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
