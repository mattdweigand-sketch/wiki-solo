#!/usr/bin/env python3
"""Regression eval for capture_gate.py.

The gate is the approval boundary between an agent and durable analysis,
promotion, or synthesis writes. This suite pins which routes require approval,
which proceed freely, which are blocked, and whether gate-created ledgers
validate against validate_capture_runs.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "scripts" / "capture_gate.py"
VALIDATOR = REPO_ROOT / "scripts" / "validate_capture_runs.py"
SYNTHESIZE_WORKFLOW = REPO_ROOT / "workflows" / "maintenance" / "synthesize.md"
TMP = tempfile.TemporaryDirectory()
APPROVAL_LEDGER = Path(TMP.name) / "capture-runs.jsonl"
DRAFT = Path(TMP.name) / "draft.md"
DRAFT.write_text("word " * 350)  # >300 measured words so the analysis bar is met
SHORT_DRAFT = Path(TMP.name) / "short-draft.md"
SHORT_DRAFT.write_text("word " * 50)  # 50 measured words, below the 300-word bar

results = Results()


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
    detail = (
        f"exit {proc.returncode} (expected {expect_code}); stdout: "
        + proc.stdout.replace("\n", " | ")
        + "; stderr: "
        + proc.stderr.replace("\n", " | ")
    )
    results.record(name, ok, detail)


ANALYSIS = ["--phase", "accepted", "--synthesized-pages", "3", "--domain-context", "yes",
            "--primary-home", "wiki/analyses/eval.md",
            "--pages-touched", "wiki/analyses/eval.md,wiki/log.md",
            "--path", str(DRAFT)]

PROMO = ["--phase", "accepted", "--trigger", "reusable_distinction",
         "--primary-home", "wiki/concepts/foo.md", "--pages-touched", "wiki/concepts/foo.md"]

SYNTHESIS = [
    "--kind", "synthesis",
    "--drafts", "wiki/primer.md local-AI routing row",
    "--pages-touched", "wiki/primer.md,wiki/synthesis.md,wiki/log.md",
]


def approval_records(record_type):
    if not APPROVAL_LEDGER.exists():
        return []
    out = []
    for line in APPROVAL_LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("record_type") == record_type:
            out.append(record)
    return out


def check_no_ledger(name):
    ok = not APPROVAL_LEDGER.exists()
    detail = "" if ok else "unexpected ledger: " + APPROVAL_LEDGER.read_text().replace("\n", " | ")
    results.record(name, ok, detail)


def check_record_count(name, record_type, expected_count):
    count = len(approval_records(record_type))
    ok = count == expected_count
    results.record(name, ok, f"{record_type} count {count} (expected {expected_count})")


def check_gate_created_ledger_validates(name):
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(APPROVAL_LEDGER)],
        text=True, capture_output=True,
    )
    ok = proc.returncode == 0
    results.record(name, ok, "validator: " + proc.stdout.replace("\n", " | "))


def check_synthesis_record() -> None:
    records = approval_records("synthesis_approval")
    ok = (
        len(records) == 1
        and records[0].get("record_type") == "synthesis_approval"
        and records[0].get("approval_status") == "approved"
        and records[0].get("primary_home") == "wiki/synthesis.md"
        and records[0].get("ledger_update_required") is True
        and records[0].get("pages_touched") == ["wiki/primer.md", "wiki/synthesis.md", "wiki/log.md"]
        and "run_id" not in records[0]
    )
    results.record("synthesis-approved-writes-structured-record", ok, "records: " + repr(records))


def check_synthesis_idempotent() -> None:
    before = approval_records("synthesis_approval")
    proc = subprocess.run(
        [sys.executable, str(GATE), "--artifact", "eval fixture",
         "--approval-ledger", str(APPROVAL_LEDGER), *SYNTHESIS, "--approved"],
        text=True,
        capture_output=True,
        check=False,
    )
    after = approval_records("synthesis_approval")
    ok = (
        proc.returncode == 0
        and len(before) == 1
        and before == after
        and "already present" in proc.stdout
    )
    results.record("synthesis-approved-structured-record-idempotent", ok,
                   f"exit {proc.returncode}; stdout: " + proc.stdout.replace("\n", " | ")
                   + f"; before: {before!r}; after: {after!r}")


def check_workflow_contract() -> None:
    text = SYNTHESIZE_WORKFLOW.read_text()
    required = (
        "scripts/capture_gate.py",
        "scripts/capture-runs.jsonl",
        "scripts/validate_capture_runs.py",
        "APPROVAL REQUIRED",
        "wiki/synthesis.md",
        "--approved",
        "before the durable change crosses the promotion boundary",
    )
    missing = [marker for marker in required if marker not in text]
    ok = not missing
    results.record("synthesize-workflow-requires-gate", ok, "missing: " + ", ".join(missing))


# Approval-required capture routes: exit 2 until --approved, then 0.
run_case("analysis-requires-approval", ANALYSIS, 2,
         expect=("analysis-capture", "APPROVAL REQUIRED",
                 "What you are approving:",
                 'Reply with plain-language approval'),
         absent=("Reply exactly:",))
check_no_ledger("unapproved-analysis-does-not-write-structured-record")
run_case("analysis-approved-proceeds", ANALYSIS + ["--approved"], 0,
         expect=("Approval: confirmed", "Structured approval record: appended", "APPROVAL CONFIRMED"),
         absent=("APPROVAL REQUIRED",))
check_record_count("approved-analysis-writes-structured-record", "capture_approval", 1)
run_case("analysis-approved-idempotent", ANALYSIS + ["--approved"], 0,
         expect=("Structured approval record: already present", "APPROVAL CONFIRMED"))
check_record_count("approved-analysis-record-stays-idempotent", "capture_approval", 1)
run_case("promotion-requires-approval", PROMO, 2,
         expect=("promotion-audit", "APPROVAL REQUIRED",
                 "Durable action: Apply an artifact promotion to the wiki.",
                 "reusable distinction"))
run_case("promotion-approved-proceeds", PROMO + ["--approved"], 0,
         expect=("Structured approval record: appended",))
check_record_count("approved-promotion-writes-structured-record", "capture_approval", 2)
check_gate_created_ledger_validates("capture-gate-created-ledger-validates")

# Free capture routes: no approval needed, exit 0.
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
run_case("capture-kind-without-phase-blocked", [], 3,
         expect=("BLOCKED", "--phase is required"))
run_case("source-without-path-blocked", ["--phase", "source"], 3,
         expect=("BLOCKED",))
run_case("below-analysis-bar-chat-only",
         ["--phase", "accepted", "--synthesized-pages", "2",
          "--word-count", "400", "--domain-context", "yes"], 0,
         expect=("chat-only",), absent=("APPROVAL REQUIRED",))
run_case("approved-flag-cannot-skip-block",
         ["--phase", "source", "--approved"], 3, expect=("BLOCKED",))

# Determinism guards: the gate cannot be talked around.
run_case("free-route-cannot-target-analyses",
         ["--phase", "experience", "--primary-home", "wiki/analyses/sneaky.md",
          "--pages-touched", "wiki/analyses/sneaky.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
run_case("free-route-analyses-dotslash-blocked",
         ["--phase", "experience", "--primary-home", "wiki/people/p.md",
          "--pages-touched", "./wiki/analyses/sneaky.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
run_case("free-route-analyses-dotdot-blocked",
         ["--phase", "experience", "--primary-home", "wiki/people/p.md",
          "--pages-touched", "wiki/foo/../analyses/sneaky.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
run_case("analysis-without-path-blocked",
         ["--phase", "accepted", "--synthesized-pages", "3", "--word-count", "400",
          "--domain-context", "yes", "--primary-home", "wiki/analyses/real.md"], 3,
         expect=("BLOCKED", "requires --path"))
run_case("placeholder-home-blocked",
         ["--phase", "accepted", "--trigger", "reusable_distinction"], 3,
         expect=("BLOCKED", "concrete --primary-home"))
run_case("out-of-root-scope-blocked",
         PROMO + ["--pages-touched", "wiki/concepts/foo.md,/etc/passwd"], 3,
         expect=("BLOCKED", "allowed root"))
run_case("measured-count-overrides-declared-high",
         ["--phase", "accepted", "--synthesized-pages", "3", "--domain-context", "yes",
          "--word-count", "400", "--primary-home", "wiki/analyses/x.md",
          "--pages-touched", "wiki/analyses/x.md", "--path", str(SHORT_DRAFT)], 3)
run_case("empty-artifact-blocked",
         ANALYSIS + ["--artifact", "   ", "--approved"], 3,
         expect=("BLOCKED", "non-empty"))
check_record_count("empty-artifact-writes-no-record", "capture_approval", 2)
run_case("free-route-raw-destination-blocked",
         ["--phase", "experience", "--primary-home", "wiki/people/p.md",
          "--pages-touched", "raw/evil.md"], 3,
         expect=("BLOCKED", "allowed root"))
run_case("free-route-out-of-root-blocked",
         ["--phase", "experience", "--primary-home", "wiki/people/p.md",
          "--pages-touched", "/etc/passwd"], 3,
         expect=("BLOCKED", "allowed root"))

# Synthesis approval branch. SYNTHESIS intentionally passes no --phase, so this
# guards the parser-level optionality required by --kind=synthesis.
run_case(
    "synthesis-requires-approval",
    SYNTHESIS,
    2,
    expect=("CAPTURE GATE", "APPROVAL REQUIRED", "Drafts for review:",
            "wiki/primer.md local-AI routing row", "Do not update wiki/synthesis.md"),
    absent=("APPROVAL CONFIRMED",),
)
check_record_count("unapproved-synthesis-does-not-write-structured-record", "synthesis_approval", 0)
run_case(
    "synthesis-approved-proceeds",
    SYNTHESIS + ["--approved"],
    0,
    expect=("Approval: confirmed", "Structured approval record: appended",
            "APPROVAL CONFIRMED", "Proceed only within this approved scope."),
    absent=("APPROVAL REQUIRED",),
)
check_synthesis_record()
check_synthesis_idempotent()
check_gate_created_ledger_validates("merged-gate-created-ledger-validates")
run_case(
    "synthesis-ledger-scope-required",
    ["--kind", "synthesis",
     "--drafts", "wiki/primer.md local-AI routing row",
     "--pages-touched", "wiki/primer.md,wiki/log.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "primary home wiki/synthesis.md must be included in --pages-touched"),
)
run_case(
    "synthesis-primary-home-scope-required",
    ["--kind", "synthesis",
     "--drafts", "wiki/overview.md exact reviewed update",
     "--primary-home", "wiki/overview.md",
     "--pages-touched", "wiki/log.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "primary home wiki/overview.md must be included in --pages-touched"),
)
run_case(
    "synthesis-drafts-required",
    ["--kind", "synthesis",
     "--drafts", " ",
     "--pages-touched", "wiki/primer.md,wiki/synthesis.md,wiki/log.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "requires --drafts"),
)
run_case(
    "synthesis-empty-artifact-blocked",
    ["--kind", "synthesis",
     "--drafts", "wiki/primer.md local-AI routing row",
     "--pages-touched", "wiki/primer.md,wiki/synthesis.md,wiki/log.md",
     "--artifact", "   ",
     "--approved"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "non-empty"),
)
check_synthesis_record()
run_case(
    "synthesis-raw-destination-blocked",
    ["--kind", "synthesis",
     "--drafts", "wiki/primer.md local-AI routing row",
     "--pages-touched", "wiki/synthesis.md,raw/evil.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "allowed root"),
)
check_workflow_contract()

exit_code = results.finish()
TMP.cleanup()
sys.exit(exit_code)
