#!/usr/bin/env python3
"""Regression eval for capture_gate.py.

The gate is the approval boundary between an agent and durable analysis or
promotion writes. This suite pins its contract: which routes require
approval (exit 2 until --approved), which proceed freely (exit 0), and
which are blocked (exit 3). A regression that quietly stops requiring
approval would otherwise be invisible until an unapproved write happened.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "capture_gate.py"
TMP = tempfile.TemporaryDirectory()
APPROVAL_LEDGER = Path(TMP.name) / "capture-runs.jsonl"

results = []


def run_case(name, args, expect_code, expect=(), absent=()):
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--artifact",
            "eval fixture",
            "--approval-ledger",
            str(APPROVAL_LEDGER),
            *args,
        ],
        text=True, capture_output=True,
    )
    ok = proc.returncode == expect_code
    for marker in expect:
        ok = ok and marker in proc.stdout
    for marker in absent:
        ok = ok and marker not in proc.stdout
    results.append((name, ok))
    if not ok:
        print(f"FAIL {name}")
        print(f"  exit {proc.returncode} (expected {expect_code})")
        print("  stdout: " + proc.stdout.replace("\n", " | "))
    else:
        print(f"PASS {name}")


ANALYSIS = ["--phase", "accepted", "--synthesized-pages", "3",
            "--word-count", "400", "--domain-context", "yes"]


def approved_records():
    if not APPROVAL_LEDGER.exists():
        return []
    return [line for line in APPROVAL_LEDGER.read_text().splitlines() if line.strip()]


def check_no_approval_record(name):
    ok = not APPROVAL_LEDGER.exists()
    results.append((name, ok))
    if ok:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        print("  unexpected ledger: " + APPROVAL_LEDGER.read_text().replace("\n", " | "))


def check_approval_record(name, expected_count):
    records = approved_records()
    ok = len(records) == expected_count
    results.append((name, ok))
    if ok:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        print(f"  record count {len(records)} (expected {expected_count})")
        print("  records: " + repr(records))

# Approval-required routes: exit 2 until --approved, then 0.
run_case("analysis-requires-approval", ANALYSIS, 2,
         expect=("analysis-capture", "APPROVAL REQUIRED",
                 "What you are approving:",
                 'Reply with plain-language approval'),
         absent=("Reply exactly:", "APPROVE analysis-capture |"))
check_no_approval_record("unapproved-analysis-does-not-write-structured-record")
run_case("analysis-approved-proceeds", ANALYSIS + ["--approved"], 0,
         expect=("Approval: confirmed", "Structured approval record: appended", "APPROVAL CONFIRMED"),
         absent=("APPROVAL REQUIRED",))
check_approval_record("approved-analysis-writes-structured-record", 1)
run_case("analysis-approved-idempotent", ANALYSIS + ["--approved"], 0,
         expect=("Structured approval record: already present", "APPROVAL CONFIRMED"))
check_approval_record("approved-analysis-record-stays-idempotent", 1)
run_case("promotion-requires-approval",
         ["--phase", "accepted", "--trigger", "reusable_distinction"], 2,
         expect=("promotion-audit", "APPROVAL REQUIRED",
                 "Durable action: Apply an artifact promotion to the wiki.",
                 "reusable distinction"))
run_case("promotion-approved-proceeds",
         ["--phase", "accepted", "--trigger", "reusable_distinction", "--approved"], 0,
         expect=("Structured approval record: appended",))
check_approval_record("approved-promotion-writes-structured-record", 2)

# Free routes: no approval needed, exit 0.
run_case("decision-capture-free", ["--phase", "decision"], 0,
         expect=("capture-decision", "not required"))
run_case("experience-capture-free", ["--phase", "experience"], 0,
         expect=("capture-experience",))
run_case("workflow-update-free", ["--phase", "workflow"], 0,
         expect=("workflow-update",))
run_case("ingest-free", ["--phase", "source", "--source-path", "raw/notes/x.md"], 0,
         expect=("ingest",))
run_case("drafting-stays-chat-only", ["--phase", "drafting"], 0,
         expect=("chat-only", "do not edit files"))

# Boundary conditions.
run_case("source-without-path-blocked", ["--phase", "source"], 3,
         expect=("BLOCKED",))
run_case("below-analysis-bar-chat-only",
         ["--phase", "accepted", "--synthesized-pages", "2",
          "--word-count", "400", "--domain-context", "yes"], 0,
         expect=("chat-only",), absent=("APPROVAL REQUIRED",))
run_case("approved-flag-cannot-skip-block",
         ["--phase", "source", "--approved"], 3, expect=("BLOCKED",))

print()
failed = [n for n, ok in results if not ok]
print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
TMP.cleanup()
sys.exit(1 if failed else 0)
