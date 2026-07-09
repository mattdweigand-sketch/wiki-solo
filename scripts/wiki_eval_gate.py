#!/usr/bin/env python3
"""Regression eval for capture_gate.py.

The gate is the approval boundary between an agent and durable analysis,
promotion, or synthesis writes. This suite pins which routes require approval,
which proceed freely, which are blocked, and whether gate-created ledgers
validate against validate_capture_runs.py.
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results
from validate_capture_runs import validate_approval

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
# Sandbox repo root for existence-sensitive cases: the synthesis branch checks
# analyses paths against the invocation cwd, so these cases run inside here.
SANDBOX = Path(TMP.name) / "sandbox-repo"
(SANDBOX / "wiki" / "analyses").mkdir(parents=True)
(SANDBOX / "wiki" / "analyses" / "existing-eval.md").write_text("existing analysis page\n")

results = Results()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_case(name, args, expect_code, expect=(), absent=(), cwd=None):
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
        text=True, capture_output=True, cwd=cwd,
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


def approval_records_from(path: Path, record_type: str):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
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
    # Structural markers only: script paths, banner, and flag. Full-sentence
    # markers would couple this eval to prose wording that legitimately evolves.
    required = (
        "scripts/capture_gate.py",
        "scripts/capture-runs.jsonl",
        "scripts/validate_capture_runs.py",
        "APPROVAL REQUIRED",
        "wiki/synthesis.md",
        "--approved",
    )
    missing = [marker for marker in required if marker not in text]
    ok = not missing
    results.record("synthesize-workflow-requires-gate", ok, "missing: " + ", ".join(missing))


def capture_record_fixture(**updates):
    record = {
        "record_type": "capture_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "approved_at": "2026-07-08T00:00:00Z",
        "artifact": "eval fixture",
        "route": "analysis-capture",
        "phase": "accepted",
        "primary_home": "wiki/analyses/eval.md",
        "pages_touched": ["wiki/analyses/eval.md", "wiki/log.md"],
        "source_path": "",
        "synthesized_pages": 3,
        "word_count": 350,
        "word_count_source": "measured",
        "word_count_path": str(DRAFT),
        "domain_context": True,
        "triggers": [],
    }
    record.update(updates)
    return record


def check_validator_draft_hash_rules() -> None:
    missing_errors = validate_approval(capture_record_fixture())
    malformed_errors = validate_approval(capture_record_fixture(
        approved_at="2026-07-08T00:00:00Z",
        draft_sha256="ABC",
    ))
    pre_cutoff_errors = validate_approval(capture_record_fixture(
        approved_at="2026-07-07T23:59:59Z",
    ))
    post_cutoff_unmeasured_errors = validate_approval(capture_record_fixture(
        route="promotion-audit",
        primary_home="wiki/concepts/foo.md",
        pages_touched=["wiki/concepts/foo.md"],
        synthesized_pages=0,
        word_count=0,
        word_count_source="unmeasured",
        word_count_path="",
        domain_context=False,
        triggers=["existing_page_update"],
    ))
    ok = (
        any("draft_sha256" in error for error in missing_errors)
        and any("draft_sha256" in error for error in malformed_errors)
        and pre_cutoff_errors == []
        and post_cutoff_unmeasured_errors == []
    )
    detail = (
        f"missing: {missing_errors!r}; malformed: {malformed_errors!r}; "
        f"pre_cutoff: {pre_cutoff_errors!r}; "
        f"post_cutoff_unmeasured: {post_cutoff_unmeasured_errors!r}"
    )
    results.record("capture-validator-enforces-commissioned-draft-sha", ok, detail)


def check_changed_draft_hash_identity() -> None:
    ledger = Path(TMP.name) / "changed-draft-capture-runs.jsonl"
    draft = Path(TMP.name) / "changed-draft.md"
    draft.write_text("same " * 350)
    args = [
        sys.executable,
        str(GATE),
        "--artifact",
        "changed draft fixture",
        "--approval-ledger",
        str(ledger),
        "--phase",
        "accepted",
        "--synthesized-pages",
        "3",
        "--domain-context",
        "yes",
        "--primary-home",
        "wiki/analyses/changed-draft.md",
        "--pages-touched",
        "wiki/analyses/changed-draft.md,wiki/log.md",
        "--path",
        str(draft),
        "--approved",
    ]
    first_hash = file_sha256(draft)
    first = subprocess.run(args, text=True, capture_output=True, check=False)
    first_records = approval_records_from(ledger, "capture_approval")
    second = subprocess.run(args, text=True, capture_output=True, check=False)
    second_records = approval_records_from(ledger, "capture_approval")
    draft.write_text("changed " * 350)
    changed_hash = file_sha256(draft)
    third = subprocess.run(args, text=True, capture_output=True, check=False)
    third_records = approval_records_from(ledger, "capture_approval")

    ok = (
        first.returncode == 0
        and second.returncode == 0
        and third.returncode == 0
        and len(first_records) == 1
        and first_records[0].get("draft_sha256") == first_hash
        and len(second_records) == 1
        and "already present" in second.stdout
        and len(third_records) == 2
        and {record.get("draft_sha256") for record in third_records}
        == {first_hash, changed_hash}
        and "appended" in third.stdout
    )
    detail = (
        f"exits: {first.returncode}, {second.returncode}, {third.returncode}; "
        f"counts: {len(first_records)}, {len(second_records)}, {len(third_records)}; "
        f"hashes: {[record.get('draft_sha256') for record in third_records]!r}; "
        f"second stdout: {second.stdout.replace(chr(10), ' | ')}; "
        f"third stdout: {third.stdout.replace(chr(10), ' | ')}"
    )
    results.record("changed-measured-draft-appends-new-approval", ok, detail)


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
check_validator_draft_hash_rules()
run_case("analysis-approved-idempotent", ANALYSIS + ["--approved"], 0,
         expect=("Structured approval record: already present", "APPROVAL CONFIRMED"))
check_record_count("approved-analysis-record-stays-idempotent", "capture_approval", 1)
check_changed_draft_hash_identity()
run_case("promotion-requires-approval", PROMO, 2,
         expect=("promotion-audit", "APPROVAL REQUIRED",
                 "Durable action: Apply an artifact promotion to the wiki.",
                 "reusable distinction"))
run_case("promotion-approved-proceeds", PROMO + ["--approved"], 0,
         expect=("Structured approval record: appended",))
check_record_count("approved-promotion-writes-structured-record", "capture_approval", 2)
check_gate_created_ledger_validates("capture-gate-created-ledger-validates")

# Free phases: never require this gate; route judgment lives in the prose
# workflows, so the gate prints a short non-approval notice and exits 0.
for free_phase in ("drafting", "source", "decision", "experience", "workflow"):
    run_case(f"{free_phase}-phase-never-requires-approval", ["--phase", free_phase], 0,
             expect=(f"non-approval (phase {free_phase})", "not required"),
             absent=("APPROVAL REQUIRED",))

# Boundary conditions.
run_case("capture-kind-without-phase-blocked", [], 3,
         expect=("BLOCKED", "--phase is required"))
run_case("below-analysis-bar-chat-only",
         ["--phase", "accepted", "--synthesized-pages", "2",
          "--path", str(DRAFT), "--domain-context", "yes"], 0,
         expect=("chat-only",), absent=("APPROVAL REQUIRED",))
run_case("approved-flag-cannot-skip-block",
         ["--phase", "experience", "--approved",
          "--primary-home", "wiki/analyses/sneaky.md",
          "--pages-touched", "wiki/analyses/sneaky.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))

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
         ["--phase", "accepted", "--synthesized-pages", "3",
          "--domain-context", "yes", "--primary-home", "wiki/analyses/real.md",
          "--trigger", "existing_page_update"], 3,
         expect=("BLOCKED", "requires --path"))
run_case("placeholder-home-blocked",
         ["--phase", "accepted", "--trigger", "reusable_distinction"], 3,
         expect=("BLOCKED", "concrete --primary-home"))
run_case("placeholder-pages-touched-blocked",
         PROMO[:6] + ["--pages-touched", "wiki/concepts/foo.md,wiki/<entity>/bar.md"], 3,
         expect=("BLOCKED", "not placeholders"))
run_case("placeholder-pages-touched-blocked-even-approved",
         PROMO[:6] + ["--pages-touched", "wiki/concepts/foo.md,wiki/<entity>/bar.md",
                      "--approved"], 3,
         expect=("BLOCKED", "not placeholders"))
check_record_count("placeholder-scope-writes-no-record", "capture_approval", 2)
run_case("out-of-root-scope-blocked",
         PROMO + ["--pages-touched", "wiki/concepts/foo.md,/etc/passwd"], 3,
         expect=("BLOCKED", "allowed root"))
# Any route whose primary home is under wiki/analyses/ must measure the draft.
run_case("promotion-into-analyses-requires-path",
         ["--phase", "accepted", "--trigger", "existing_page_update",
          "--primary-home", "wiki/analyses/update.md",
          "--pages-touched", "wiki/analyses/update.md"], 3,
         expect=("BLOCKED", "requires --path"))
run_case("promotion-into-analyses-with-path-proceeds",
         ["--phase", "accepted", "--trigger", "existing_page_update",
          "--primary-home", "wiki/analyses/update.md",
          "--pages-touched", "wiki/analyses/update.md", "--path", str(DRAFT)], 2,
         expect=("promotion-audit", "APPROVAL REQUIRED"))
# The measurement rule covers the whole scope, not just the primary home: an
# analyses page named only in --pages-touched must still demand a draft.
run_case("analyses-in-pages-touched-requires-path",
         ["--phase", "accepted", "--trigger", "existing_page_update",
          "--primary-home", "wiki/concepts/foo.md",
          "--pages-touched", "wiki/concepts/foo.md,wiki/analyses/sneaky.md"], 3,
         expect=("BLOCKED", "requires --path"))
run_case("analyses-in-pages-touched-with-path-proceeds",
         ["--phase", "accepted", "--trigger", "existing_page_update",
          "--primary-home", "wiki/concepts/foo.md",
          "--pages-touched", "wiki/concepts/foo.md,wiki/analyses/sneaky.md",
          "--path", str(DRAFT)], 2,
         expect=("promotion-audit", "APPROVAL REQUIRED"))
# Case-variant spellings must not slip past the analyses rules (APFS is
# case-insensitive, so wiki/Analyses/ IS the analyses folder on disk).
run_case("case-variant-analyses-still-guarded",
         ["--phase", "experience", "--primary-home", "wiki/Analyses/sneaky.md",
          "--pages-touched", "wiki/Analyses/sneaky.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
# An unreadable --path blocks with the precise diagnosis instead of
# misclassifying the run as chat-only.
run_case("unreadable-path-blocked-with-diagnosis",
         ["--phase", "accepted", "--synthesized-pages", "3", "--domain-context", "yes",
          "--primary-home", "wiki/analyses/x.md", "--pages-touched", "wiki/analyses/x.md",
          "--path", "tmp/does-not-exist.md"], 3,
         expect=("BLOCKED", "is not a readable file"))
run_case("short-measured-draft-cannot-reach-analyses",
         ["--phase", "accepted", "--synthesized-pages", "3", "--domain-context", "yes",
          "--primary-home", "wiki/analyses/x.md",
          "--pages-touched", "wiki/analyses/x.md", "--path", str(SHORT_DRAFT)], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
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

# The guards check declared inputs, not the route-derived home: a chat-only
# classification discards --primary-home, but a declared analyses or
# out-of-root destination must still block, with a hint toward measurement.
run_case("chat-only-declared-analyses-home-blocked",
         ["--phase", "accepted", "--primary-home", "wiki/analyses/foo.md"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/", "re-run with --path"))
run_case("chat-only-declared-out-of-root-home-blocked",
         ["--phase", "accepted", "--primary-home", "/etc/passwd"], 3,
         expect=("BLOCKED", "allowed root"))
# The bare directory (trailing-slash spelling, normalized to 'wiki/analyses')
# is still the analyses folder.
run_case("analyses-trailing-slash-blocked",
         ["--phase", "experience", "--primary-home", "wiki/analyses/"], 3,
         expect=("BLOCKED", "may not write to wiki/analyses/"))
# Scope entries the validator would reject must block before a record exists.
run_case("none-token-in-scope-blocked",
         PROMO[:6] + ["--pages-touched", "wiki/concepts/foo.md,none", "--approved"], 3,
         expect=("BLOCKED", "'none'"))
check_record_count("none-scope-writes-no-record", "capture_approval", 2)
run_case("negative-synthesized-pages-blocked",
         ["--phase", "accepted", "--synthesized-pages", "-2", "--domain-context", "yes",
          "--primary-home", "wiki/analyses/eval.md",
          "--pages-touched", "wiki/analyses/eval.md",
          "--path", str(DRAFT), "--approved"], 3,
         expect=("BLOCKED", "non-negative"))
check_record_count("negative-synthesized-pages-writes-no-record", "capture_approval", 2)
# Duplicate scope declarations collapse to one normalized entry.
run_case("duplicate-scope-entries-deduped",
         PROMO[:6] + ["--pages-touched", "wiki/concepts/foo.md,./wiki/concepts/foo.md"], 2,
         expect=("Pages touched: wiki/concepts/foo.md",),
         absent=("wiki/concepts/foo.md, wiki/concepts/foo.md",))
# argparse usage errors exit 3, never 2: exit 2 means only "approval required".
run_case("usage-error-exits-3", ["--no-such-flag"], 3)
# A short measured draft updating an EXISTING analyses page via a promotion
# trigger is the intended update path and stays approvable.
run_case("short-draft-promotion-into-analyses-approvable",
         ["--phase", "accepted", "--trigger", "existing_page_update",
          "--primary-home", "wiki/analyses/update.md",
          "--pages-touched", "wiki/analyses/update.md", "--path", str(SHORT_DRAFT)], 2,
         expect=("promotion-audit", "APPROVAL REQUIRED"))


def check_analysis_record_measurement_provenance():
    records = [r for r in approval_records("capture_approval")
               if r.get("route") == "analysis-capture"]
    expected_hash = file_sha256(DRAFT)
    ok = (
        len(records) == 1
        and records[0].get("word_count_path") == str(DRAFT)
        and records[0].get("word_count_source") == "measured"
        and records[0].get("draft_sha256") == expected_hash
    )
    results.record("analysis-record-carries-measurement-provenance", ok,
                   "records: " + repr(records))


check_analysis_record_measurement_provenance()

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
run_case(
    "synthesis-placeholder-scope-blocked",
    ["--kind", "synthesis",
     "--drafts", "wiki/primer.md local-AI routing row",
     "--pages-touched", "wiki/synthesis.md,wiki/<entity>/x.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "not placeholders"),
)
# The synthesis branch is unmeasured, so it may only touch analyses pages that
# already exist; a NEW analyses destination must go through analysis-capture.
run_case(
    "synthesis-new-analyses-page-blocked",
    ["--kind", "synthesis",
     "--drafts", "status flip for a page that does not exist",
     "--pages-touched", "wiki/synthesis.md,wiki/analyses/missing-eval.md"],
    3,
    expect=("CAPTURE GATE: BLOCKED", "existing", "analysis-capture"),
    cwd=SANDBOX,
)
run_case(
    "synthesis-existing-analyses-page-proceeds",
    ["--kind", "synthesis",
     "--drafts", "status flip on the reviewed existing analysis",
     "--pages-touched", "wiki/synthesis.md,wiki/analyses/existing-eval.md"],
    2,
    expect=("APPROVAL REQUIRED",),
    cwd=SANDBOX,
)
check_workflow_contract()

# Appending after a truncated trailing newline must not merge two records into
# one corrupt line.
APPROVAL_LEDGER.write_bytes(APPROVAL_LEDGER.read_bytes().rstrip(b"\n"))
run_case("append-after-missing-trailing-newline",
         PROMO + ["--artifact", "newline repair fixture", "--approved"], 0,
         expect=("Structured approval record: appended",))
check_gate_created_ledger_validates("ledger-validates-after-newline-repair")

exit_code = results.finish()
TMP.cleanup()
sys.exit(exit_code)
