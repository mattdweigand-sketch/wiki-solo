#!/usr/bin/env python3
"""Regression eval for synthesis_gate.py.

The gate pins the approval boundary for synthesize runs: agents may draft
synthesis output, but cannot update wiki/synthesis.md or log a promotion until
the user has approved the displayed draft and file scope.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "synthesis_gate.py"
SYNTHESIZE_WORKFLOW = REPO_ROOT / "workflows" / "maintenance" / "synthesize.md"
TMP = tempfile.TemporaryDirectory()
APPROVAL_LEDGER = Path(TMP.name) / "synthesis-runs.jsonl"

BASE = [
    "--artifact",
    "eval synthesis",
    "--drafts",
    "wiki/primer.md local-AI routing row",
    "--pages-touched",
    "wiki/primer.md,wiki/synthesis.md,wiki/log.md",
    "--approval-ledger",
    str(APPROVAL_LEDGER),
]

results: list[tuple[str, bool]] = []


def run_case(name: str, args: list[str], expect_code: int, expect=(), absent=()) -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    ok = proc.returncode == expect_code
    for marker in expect:
        ok = ok and marker in proc.stdout
    for marker in absent:
        ok = ok and marker not in proc.stdout
    results.append((name, ok))
    if ok:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        print(f"  exit {proc.returncode} (expected {expect_code})")
        print("  stdout: " + proc.stdout.replace("\n", " | "))
        print("  stderr: " + proc.stderr.replace("\n", " | "))


def check_workflow_contract() -> None:
    text = SYNTHESIZE_WORKFLOW.read_text()
    required = (
        "scripts/synthesis_gate.py",
        "scripts/synthesis-runs.jsonl",
        "scripts/validate_synthesis_runs.py",
        "APPROVAL REQUIRED",
        "wiki/synthesis.md",
        "--approved",
        "before updating `wiki/synthesis.md`",
    )
    missing = [marker for marker in required if marker not in text]
    ok = not missing
    results.append(("synthesize-workflow-requires-gate", ok))
    if ok:
        print("PASS synthesize-workflow-requires-gate")
    else:
        print("FAIL synthesize-workflow-requires-gate")
        print("  missing: " + ", ".join(missing))


def check_approval_ledger_absent() -> None:
    ok = not APPROVAL_LEDGER.exists()
    results.append(("unapproved-does-not-write-structured-record", ok))
    if ok:
        print("PASS unapproved-does-not-write-structured-record")
    else:
        print("FAIL unapproved-does-not-write-structured-record")
        print(f"  unexpected ledger: {APPROVAL_LEDGER.read_text()}")


def approved_records() -> list[dict[str, object]]:
    if not APPROVAL_LEDGER.exists():
        return []
    records = []
    for line in APPROVAL_LEDGER.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def check_approval_ledger_record() -> None:
    records = approved_records()
    ok = (
        len(records) == 1
        and records[0].get("record_type") == "synthesis_approval"
        and records[0].get("approval_status") == "approved"
        and records[0].get("primary_home") == "wiki/synthesis.md"
        and records[0].get("ledger_update_required") is True
        and records[0].get("pages_touched") == ["wiki/primer.md", "wiki/synthesis.md", "wiki/log.md"]
        and isinstance(records[0].get("run_id"), str)
    )
    results.append(("approved-writes-structured-record", ok))
    if ok:
        print("PASS approved-writes-structured-record")
    else:
        print("FAIL approved-writes-structured-record")
        print("  records: " + repr(records))


def check_approval_ledger_idempotent() -> None:
    before = approved_records()
    proc = subprocess.run(
        [sys.executable, str(GATE), *BASE, "--approved"],
        text=True,
        capture_output=True,
        check=False,
    )
    after = approved_records()
    ok = (
        proc.returncode == 0
        and len(before) == 1
        and before == after
        and "already present" in proc.stdout
    )
    results.append(("approved-structured-record-idempotent", ok))
    if ok:
        print("PASS approved-structured-record-idempotent")
    else:
        print("FAIL approved-structured-record-idempotent")
        print(f"  exit {proc.returncode}")
        print("  stdout: " + proc.stdout.replace("\n", " | "))
        print("  before: " + repr(before))
        print("  after: " + repr(after))


run_case(
    "synthesis-requires-approval",
    BASE,
    2,
    expect=("SYNTHESIS GATE", "APPROVAL REQUIRED", "Drafts for review:", "Do not update wiki/synthesis.md"),
    absent=("APPROVAL CONFIRMED",),
)
check_approval_ledger_absent()
run_case(
    "synthesis-approved-proceeds",
    BASE + ["--approved"],
    0,
    expect=("Approval: confirmed", "Structured approval record: appended", "APPROVAL CONFIRMED", "Proceed only within this approved scope."),
    absent=("APPROVAL REQUIRED",),
)
check_approval_ledger_record()
check_approval_ledger_idempotent()
run_case(
    "ledger-scope-required",
    [
        "--artifact",
        "eval synthesis",
        "--drafts",
        "wiki/primer.md local-AI routing row",
        "--pages-touched",
        "wiki/primer.md,wiki/log.md",
    ],
    3,
    expect=("SYNTHESIS GATE: BLOCKED", "Ledger approval scope must include wiki/synthesis.md"),
)
run_case(
    "drafts-required",
    [
        "--artifact",
        "eval synthesis",
        "--drafts",
        " ",
        "--pages-touched",
        "wiki/primer.md,wiki/synthesis.md,wiki/log.md",
    ],
    3,
    expect=("SYNTHESIS GATE: BLOCKED", "requires --drafts"),
)
check_workflow_contract()

print()
failed = [name for name, ok in results if not ok]
print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
TMP.cleanup()
sys.exit(1 if failed else 0)
