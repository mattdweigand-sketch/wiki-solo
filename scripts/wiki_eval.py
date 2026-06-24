#!/usr/bin/env python3
"""Run the live wiki evaluation suites.

Entrypoint for the deterministic checks that guard live tooling: shared parser
coverage, backlink rebuild guards, lint seeded-violation cases, capture_gate.py's
approval contract across capture and synthesis kinds, the single approval
ledger, export include/exclude boundaries, review_due surfacing, duplicate global
Codex skill detection/removal safety, wrapper parity, and Tier-1 lint over the
live corpus.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


SUITES = {
    "parse": [sys.executable, "scripts/wiki_eval_parse.py"],
    "rebuild": [sys.executable, "scripts/wiki_eval_rebuild.py"],
    "lint": [sys.executable, "scripts/wiki_eval_lint.py"],
    "gate": [sys.executable, "scripts/wiki_eval_gate.py"],
    "capture-runs": [sys.executable, "scripts/validate_capture_runs.py"],
    "ledger-validators": [sys.executable, "scripts/wiki_eval_ledgers.py"],
    "export": [sys.executable, "scripts/wiki_eval_export.py"],
    "review-due": [sys.executable, "scripts/wiki_eval_review.py"],
    "codex-global-dupes": [sys.executable, "scripts/sync_codex_skills.py", "--check"],
    "codex-remove-safety": [sys.executable, "scripts/wiki_eval_codex_remove.py"],
    "wrapper-parity": [sys.executable, "scripts/sync_codex_skills.py", "--wrapper-parity"],
    "tier1": [sys.executable, "scripts/lint.py", "--tier1"],
}


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
    suite_names = args.suite or list(SUITES)

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
