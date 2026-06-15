#!/usr/bin/env python3
"""Run the live wiki evaluation suites.

Entrypoint for the deterministic checks that guard live tooling: the
rebuild_referenced_by.py link-graph guards, lint.py's checks and
adjudication suppression (seeded-violation cases so no check can go
vacuous), capture_gate.py's approval contract, structured capture approval
ledger, synthesis_gate.py's approval contract, the structured synthesis-run
ledger, operational helper coverage, and Tier-1 lint over the live corpus. The autonomy harness suites
(apply, ingest, pipeline, policy, provider, route, run, schemas, semantic)
are archived with the harness under archive/wiki-harness/ per
decisions/archive-wiki-autonomy-harness; restore them from there if the
harness is reopened.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


SUITES = {
    "rebuild": [sys.executable, "scripts/wiki_eval_rebuild.py"],
    "lint": [sys.executable, "scripts/wiki_eval_lint.py"],
    "gate": [sys.executable, "scripts/wiki_eval_gate.py"],
    "capture-runs": [sys.executable, "scripts/validate_capture_runs.py"],
    "synthesis-gate": [sys.executable, "scripts/wiki_eval_synthesis_gate.py"],
    "synthesis-runs": [sys.executable, "scripts/validate_synthesis_runs.py"],
    "operational": [sys.executable, "scripts/wiki_eval_operational.py"],
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
        "rebuild",
        "lint",
        "gate",
        "capture-runs",
        "synthesis-gate",
        "synthesis-runs",
        "operational",
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
