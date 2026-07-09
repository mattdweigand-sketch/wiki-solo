#!/usr/bin/env python3
"""Regression evals for the wiki-swarm runtime and workflow contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results


REPO_ROOT = Path(__file__).resolve().parents[1]
SWARM = REPO_ROOT / "scripts" / "wiki_swarm.py"
ROOT_CONTEXT = REPO_ROOT / "CONTEXT.md"
RESEARCH_CONTEXT = REPO_ROOT / "workflows" / "research" / "CONTEXT.md"
SWARM_WORKFLOW = REPO_ROOT / "workflows" / "research" / "wiki-swarm.md"
CLAUDE_SWARM = REPO_ROOT / ".claude" / "commands" / "wiki-swarm.md"
CODEX_SWARM = REPO_ROOT / ".codex" / "skills" / "wiki-swarm" / "SKILL.md"

results = Results()


def run_swarm(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SWARM), *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


def packet_path(body: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix="wiki-swarm-eval-")) / "packet.md"
    path.write_text(body, encoding="utf-8")
    return path


GOOD_PACKET = """WIKI-SWARM PACKET
Verdict: SINGLE-AGENT SWARM
Question: /wiki-swarm What does the wiki say?
Source scope: wiki/index.md, wiki/primer.md, selected pages
Pages consulted: [[index]], [[primer]]
Lane results: Planner scoped the question; Page Scout tagged page relevance; Reviewer completed scope-retention review; helper lanes returned notes only.
Supported facts: Facts are cited to [[index]].
Inferences: Inferences are labeled.
Contradictions or stale areas: none found
Raw sources checked: not triggered - ordinary lookup
Raw extraction limits: not triggered - no raw verification performed
Raw-only findings: none - no raw-only findings
Answer: concise answer from [[primer]]
What not to say: do not overclaim
Checks actually run: preflight, packet validation
Durable-write status: chat-only; no durable write
Promotion audit: none
"""


def check_preflight() -> None:
    accepted = run_swarm("preflight", "--question", "/wiki-swarm answer this from the wiki")
    results.record(
        "explicit-trigger-accepted",
        accepted.returncode == 0 and "PREFLIGHT: ACCEPTED" in accepted.stdout,
        accepted.stdout + accepted.stderr,
    )

    for name, question in (
        ("ordinary-broad-rejected", "answer this carefully from the wiki"),
        ("use-agents-rejected", "be thorough and use agents"),
        ("standalone-swarm-rejected", "swarm this research problem"),
    ):
        proc = run_swarm("preflight", "--question", question)
        results.record(
            name,
            proc.returncode == 2 and "PREFLIGHT: REJECTED" in proc.stdout,
            proc.stdout + proc.stderr,
        )


def check_manifest() -> None:
    proc = run_swarm("manifest", "--json")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {}
    lanes = data.get("lanes", [])
    lane_map = {lane.get("name"): lane for lane in lanes}
    planner = lane_map.get("planner", {})
    page_scout = lane_map.get("page-scout", {})
    evidence = lane_map.get("evidence-extractor", {})
    synthesizer = lane_map.get("synthesizer", {})
    reviewer = lane_map.get("reviewer", {})
    ok = (
        proc.returncode == 0
        and data.get("trigger_phrases") == ["/wiki-swarm", "wiki-swarm", "swarm the wiki answer"]
        and data.get("required_consulted_pages") == ["index", "primer"]
        and data.get("citation_required_sections") == ["Supported facts", "Answer"]
        and data.get("scope_retention_dimensions") == [
            "material caveats",
            "status qualifiers",
            "exclusions",
            "adverse facts",
        ]
        and data.get("page_relevance_tags") == [
            "project timeline",
            "operating state",
            "condition caveat",
            "contradiction",
            "open follow-up",
            "source register",
            "cost/economics",
            "evidence gap",
        ]
        and data.get("scope_retention_output_targets") == [
            "Supported facts",
            "Contradictions or stale areas",
            "Answer",
            "What not to say",
            "Raw-only findings",
        ]
        and "scope-retention" in data.get("scope_retention_review_markers", [])
        and "may not support" in data.get("citation_integrity_failure_markers", [])
        and "[[contradictions]]" in data.get("contradiction_page_markers", [])
        and "none found" in data.get("contradiction_dismissal_markers", [])
        and "filed analysis" in data.get("durable_write_claim_markers", [])
        and "capture-runs.jsonl" in data.get("durable_write_approval_proof_markers", [])
        and "validate_capture_runs.py" in data.get("durable_write_validation_proof_markers", [])
        and "wiki/analyses/" in data.get("durable_write_destination_markers", [])
        and "complete history" in data.get("raw_check_required_markers", [])
        and "not triggered" in data.get("raw_qualified_skip_markers", [])
        and "none - no raw-only findings" in data.get("raw_only_qualified_none_markers", [])
        and "re-ingest" in data.get("raw_only_reingest_markers", [])
        and data.get("max_raw_files") == 3
        and len(lanes) == 7
        and any(lane.get("name") == "raw-evidence-extractor" for lane in lanes)
        and "scope-retention risks" in planner.get("allowed_outputs", [])
        and "page relevance tags" in page_scout.get("allowed_outputs", [])
        and "material caveats" in evidence.get("allowed_outputs", [])
        and "retained caveats" in synthesizer.get("allowed_outputs", [])
        and "scope-retention gaps" in reviewer.get("allowed_outputs", [])
        and "scope-retention gaps" in reviewer.get("responsibility", "")
        and all(lane.get("read_only") is True for lane in lanes)
        and all(lane.get("may_edit_files") is False for lane in lanes)
        and all(lane.get("may_run_durable_writes") is False for lane in lanes)
        and all(lane.get("may_send_external_output") is False for lane in lanes)
        and all(lane.get("may_decide_final_synthesis") is False for lane in lanes)
    )
    results.record("manifest-pins-read-only-lanes", ok, proc.stdout + proc.stderr)


def check_packet_validation() -> None:
    good = packet_path(GOOD_PACKET)
    proc = run_swarm("validate-packet", "--packet", str(good))
    results.record(
        "valid-packet-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    missing = packet_path(GOOD_PACKET.replace("Promotion audit: none\n", ""))
    proc = run_swarm("validate-packet", "--packet", str(missing))
    results.record(
        "missing-section-fails",
        proc.returncode == 1 and "missing packet section: Promotion audit" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    empty_verdict = packet_path(GOOD_PACKET.replace(
        "Verdict: SINGLE-AGENT SWARM",
        "Verdict:",
    ))
    proc = run_swarm("validate-packet", "--packet", str(empty_verdict))
    results.record(
        "empty-verdict-fails",
        proc.returncode == 1 and "invalid verdict" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    proposed = packet_path(GOOD_PACKET.replace(
        "Checks actually run: preflight, packet validation",
        "Checks actually run: proposed lint and planned packet validation",
    ))
    proc = run_swarm("validate-packet", "--packet", str(proposed))
    results.record(
        "proposed-check-claim-fails",
        proc.returncode == 1 and "proposed or planned" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    helper_write = packet_path(GOOD_PACKET.replace(
        "helper lanes returned notes only",
        "helper lanes edited files and returned notes",
    ))
    proc = run_swarm("validate-packet", "--packet", str(helper_write))
    results.record(
        "helper-write-claim-fails",
        proc.returncode == 1 and "read-only" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    negated_helper_write = packet_path(GOOD_PACKET.replace(
        "helper lanes returned notes only",
        "helper lanes returned notes only; no durable write was requested",
    ))
    proc = run_swarm("validate-packet", "--packet", str(negated_helper_write))
    results.record(
        "negated-helper-write-claim-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    missing_scope_review = packet_path(GOOD_PACKET.replace(
        "Reviewer completed scope-retention review; ",
        "",
    ))
    proc = run_swarm("validate-packet", "--packet", str(missing_scope_review))
    results.record(
        "missing-scope-retention-review-fails",
        proc.returncode == 1 and "scope-retention review" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    bypass = packet_path(GOOD_PACKET.replace(
        "Durable-write status: chat-only; no durable write",
        "Durable-write status: filed analysis by direct write",
    ))
    proc = run_swarm("validate-packet", "--packet", str(bypass))
    results.record(
        "durable-bypass-claim-fails",
        proc.returncode == 1 and "analysis-capture" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    durable_route_without_proof = packet_path(GOOD_PACKET.replace(
        "Durable-write status: chat-only; no durable write",
        "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture",
    ))
    proc = run_swarm("validate-packet", "--packet", str(durable_route_without_proof))
    results.record(
        "durable-route-without-proof-fails",
        proc.returncode == 1
        and "approval record" in proc.stdout
        and "validate_capture_runs.py" in proc.stdout
        and "primary destination" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    durable_proof = packet_path(GOOD_PACKET.replace(
        "Durable-write status: chat-only; no durable write",
        "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture; "
        "approval record in scripts/capture-runs.jsonl; validate_capture_runs.py passed; "
        "primary home wiki/analyses/example.md",
    ))
    proc = run_swarm("validate-packet", "--packet", str(durable_proof))
    results.record(
        "durable-proof-packet-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    missing_index_primer = packet_path(GOOD_PACKET.replace(
        "Pages consulted: [[index]], [[primer]]",
        "Pages consulted: [[agent-harness]]",
    ))
    proc = run_swarm("validate-packet", "--packet", str(missing_index_primer))
    results.record(
        "missing-index-primer-fails",
        proc.returncode == 1
        and "Pages consulted must include [[index]]" in proc.stdout
        and "Pages consulted must include [[primer]]" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    uncited_answer = packet_path(GOOD_PACKET.replace(
        "Answer: concise answer from [[primer]]",
        "Answer: concise answer with no citation",
    ))
    proc = run_swarm("validate-packet", "--packet", str(uncited_answer))
    results.record(
        "uncited-answer-fails",
        proc.returncode == 1 and "Answer must include at least one wiki citation" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    uncited_facts = packet_path(GOOD_PACKET.replace(
        "Supported facts: Facts are cited to [[index]].",
        "Supported facts: Facts are not cited.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(uncited_facts))
    results.record(
        "uncited-supported-facts-fail",
        proc.returncode == 1 and "Supported facts must include at least one wiki citation" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    unconsulted_citation = packet_path(GOOD_PACKET.replace(
        "Answer: concise answer from [[primer]]",
        "Answer: concise answer from [[context-as-moat]]",
    ))
    proc = run_swarm("validate-packet", "--packet", str(unconsulted_citation))
    results.record(
        "unconsulted-citation-fails",
        proc.returncode == 1 and "cites pages not listed in Pages consulted: context-as-moat" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    self_disclaimed_citation = packet_path(GOOD_PACKET.replace(
        "Answer: concise answer from [[primer]]",
        "Answer: concise answer from [[primer]], but the citation may not support every claim.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(self_disclaimed_citation))
    results.record(
        "self-disclaimed-citation-support-fails",
        proc.returncode == 1 and "must not disclaim or weaken its own citation support" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    smoothed_contradiction = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm What are the current customer status priorities and contradictions?",
    ).replace(
        "Pages consulted: [[index]], [[primer]]",
        "Pages consulted: [[index]], [[primer]], [[customer-status]]",
    ).replace(
        "Answer: concise answer from [[primer]]",
        "Answer: current status answer from [[customer-status]]",
    ).replace(
        "Contradictions or stale areas: none found",
        "Contradictions or stale areas: none found",
    ))
    proc = run_swarm("validate-packet", "--packet", str(smoothed_contradiction))
    results.record(
        "contradiction-sensitive-packet-requires-contradictions-check",
        proc.returncode == 1 and "must consult [[contradictions]]" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    not_applicable_contradiction_bypass = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm What are the current customer account status risks?",
    ).replace(
        "Pages consulted: [[index]], [[primer]]",
        "Pages consulted: [[index]], [[primer]], [[customer-status]]",
    ).replace(
        "Contradictions or stale areas: none found",
        "Contradictions or stale areas: not applicable",
    ).replace(
        "Answer: concise answer from [[primer]]",
        "Answer: current status answer from [[customer-status]]",
    ))
    proc = run_swarm("validate-packet", "--packet", str(not_applicable_contradiction_bypass))
    results.record(
        "contradiction-not-applicable-bypass-fails",
        proc.returncode == 1
        and "must consult [[contradictions]]" in proc.stdout
        and "must not dismiss" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    contradiction_register_smoothed = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm What are the current customer account status risks?",
    ).replace(
        "Pages consulted: [[index]], [[primer]]",
        "Pages consulted: [[index]], [[primer]], [[customer-status]], [[contradictions]]",
    ).replace(
        "Contradictions or stale areas: none found",
        "Contradictions or stale areas: none found",
    ).replace(
        "Answer: concise answer from [[primer]]",
        "Answer: current status answer from [[customer-status]]",
    ))
    proc = run_swarm("validate-packet", "--packet", str(contradiction_register_smoothed))
    results.record(
        "contradiction-register-smoothing-fails",
        proc.returncode == 1
        and "must cite [[contradictions]]" in proc.stdout
        and "must not dismiss" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_required_bare_none = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm tell me the complete history of the kitchen remodel",
    ).replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: none",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_required_bare_none))
    results.record(
        "raw-required-bare-none-fails",
        proc.returncode == 1 and "Raw sources checked must list checked raw files" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_required_qualified_skip = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm tell me the complete history of the kitchen remodel",
    ).replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: not triggered - consulted source page is already the durable truth for this ordinary lookup",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_required_qualified_skip))
    results.record(
        "raw-required-qualified-skip-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_checked = packet_path(GOOD_PACKET.replace(
        "Question: /wiki-swarm What does the wiki say?",
        "Question: /wiki-swarm tell me the complete history of the kitchen remodel",
    ).replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/kitchen-binder.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits: no unreadable regions found in the extracted text",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_checked))
    results.record(
        "raw-checked-with-limits-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    too_many_raw_files = packet_path(GOOD_PACKET.replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/one.pdf via pdftotext; "
        "raw/records/two.pdf via pdftotext; raw/records/three.pdf via pdftotext; "
        "raw/records/four.pdf via pdftotext",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits: no unreadable regions found in extracted text",
    ))
    proc = run_swarm("validate-packet", "--packet", str(too_many_raw_files))
    results.record(
        "too-many-raw-files-fails",
        proc.returncode == 1 and "no more than 3 raw/ paths" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_checked_empty_limits = packet_path(GOOD_PACKET.replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/kitchen-binder.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits:",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_checked_empty_limits))
    results.record(
        "raw-checked-empty-limits-fails",
        proc.returncode == 1 and "Raw extraction limits must be stated" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_path_in_answer = packet_path(GOOD_PACKET.replace(
        "Answer: concise answer from [[primer]]",
        "Answer: concise answer from [[primer]] and raw/records/kitchen-binder.pdf",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_path_in_answer))
    results.record(
        "raw-path-in-answer-fails",
        proc.returncode == 1 and "Answer must not include raw/ paths" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_path_in_supported_facts = packet_path(GOOD_PACKET.replace(
        "Supported facts: Facts are cited to [[index]].",
        "Supported facts: Facts are cited to [[index]] and raw/records/kitchen-binder.pdf.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_path_in_supported_facts))
    results.record(
        "raw-path-in-supported-facts-fails",
        proc.returncode == 1 and "Supported facts must not include raw/ paths" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_path_laundering = packet_path(GOOD_PACKET.replace(
        "Pages consulted: [[index]], [[primer]]",
        "Pages consulted: [[index]], [[primer]], raw/videos/foo.md",
    ).replace(
        "Answer: concise answer from [[primer]]",
        "Answer: concise answer from [[foo]]",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_path_laundering))
    results.record(
        "raw-path-page-mention-laundering-fails",
        proc.returncode == 1 and "cites pages not listed in Pages consulted: foo" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_only_finding = packet_path(GOOD_PACKET.replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/kitchen-binder.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits: no unreadable regions found in the extracted text",
    ).replace(
        "Raw-only findings: none - no raw-only findings",
        "Raw-only findings: raw-only finding: binder has an omitted invoice detail; recommend re-ingest and update source page before durable use.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_only_finding))
    results.record(
        "raw-only-finding-with-recommendation-passes",
        proc.returncode == 0 and "valid" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_only_without_recommendation = packet_path(GOOD_PACKET.replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/kitchen-binder.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits: no unreadable regions found in the extracted text",
    ).replace(
        "Raw-only findings: none - no raw-only findings",
        "Raw-only findings: raw-only finding: binder has an omitted invoice detail.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_only_without_recommendation))
    results.record(
        "raw-only-finding-without-recommendation-fails",
        proc.returncode == 1 and "Raw-only findings must recommend" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_only_without_raw_path = packet_path(GOOD_PACKET.replace(
        "Raw-only findings: none - no raw-only findings",
        "Raw-only findings: raw-only finding: omitted invoice detail; recommend re-ingest and update source page before durable use.",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_only_without_raw_path))
    results.record(
        "raw-only-finding-without-raw-check-fails",
        proc.returncode == 1 and "Raw-only findings require at least one raw file" in proc.stdout,
        proc.stdout + proc.stderr,
    )

    raw_only_with_durable_filing = packet_path(GOOD_PACKET.replace(
        "Raw sources checked: not triggered - ordinary lookup",
        "Raw sources checked: raw/records/kitchen-binder.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: not triggered - no raw verification performed",
        "Raw extraction limits: no unreadable regions found in the extracted text",
    ).replace(
        "Raw-only findings: none - no raw-only findings",
        "Raw-only findings: raw-only finding: omitted invoice detail; recommend re-ingest and update source page before durable use.",
    ).replace(
        "Durable-write status: chat-only; no durable write",
        "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture; "
        "approval record in scripts/capture-runs.jsonl; validate_capture_runs.py passed; "
        "primary home wiki/analyses/example.md",
    ))
    proc = run_swarm("validate-packet", "--packet", str(raw_only_with_durable_filing))
    results.record(
        "raw-only-finding-with-durable-filing-fails",
        proc.returncode == 1 and "raw-only findings must not claim an analysis was filed" in proc.stdout,
        proc.stdout + proc.stderr,
    )


def check_docs_contract() -> None:
    root_text = ROOT_CONTEXT.read_text(encoding="utf-8")
    research_text = RESEARCH_CONTEXT.read_text(encoding="utf-8")
    swarm_text = SWARM_WORKFLOW.read_text(encoding="utf-8")
    claude_text = CLAUDE_SWARM.read_text(encoding="utf-8")
    codex_text = CODEX_SWARM.read_text(encoding="utf-8")

    results.record(
        "normal-research-no-whole-workflow-claim",
        "this `CONTEXT.md` is the whole workflow" not in research_text.lower()
        and "Single task." not in research_text,
        "research context still claims to be the whole workflow",
    )
    results.record(
        "swarm-doc-uses-runtime-trigger-boundary",
        "scripts/wiki_swarm.py preflight" in swarm_text
        and "scripts/wiki_swarm.py manifest" in swarm_text
        and "explicit trigger phrases above" not in swarm_text,
        "swarm workflow must point at runtime-owned trigger boundary",
    )
    results.record(
        "route-doc-does-not-copy-trigger-list",
        '"/wiki-swarm", or "swarm the wiki answer"' not in root_text
        and "scripts/wiki_swarm.py preflight" in root_text,
        "root CONTEXT.md should route by runtime boundary, not copied trigger list",
    )
    results.record(
        "swarm-read-only-rule-not-softened",
        "read-only by default" not in swarm_text
        and "Split lanes are read-only." in swarm_text,
        "split lanes rule is softened or absent",
    )
    results.record(
        "swarm-doc-delegates-lane-manifest",
        "Run every lane in `python3 scripts/wiki_swarm.py manifest`" in swarm_text
        and "**Planner:**" not in swarm_text
        and "**Page Scout:**" not in swarm_text
        and "**Evidence Extractor:**" not in swarm_text,
        "swarm workflow should not duplicate the runtime lane manifest",
    )
    results.record(
        "swarm-doc-preserves-scope-caveats-generally",
        "## Scope Retention" in swarm_text
        and "For any wiki-swarm question" in swarm_text
        and "runtime-owned scope-retention dimensions" in swarm_text
        and "runtime-owned page relevance tags" in swarm_text
        and "runtime-owned output targets" in swarm_text
        and "Reviewer should check that no material caveat from a consulted page was silently dropped" in swarm_text
        and "Raw verification must not narrow the compiled-page scope" in swarm_text,
        "swarm workflow must preserve material caveats for every query, not only complete-history prompts",
    )
    results.record(
        "swarm-doc-does-not-duplicate-scope-taxonomy",
        "project timeline, operating state, condition caveat" not in swarm_text
        and "material caveats, status qualifiers, exclusions, and adverse facts" not in swarm_text,
        "swarm workflow should defer scope taxonomy to scripts/wiki_swarm.py manifest",
    )
    results.record(
        "swarm-doc-uses-runtime-raw-file-cap",
        "runtime-owned raw-file maximum" in swarm_text
        and "at most three raw files" not in swarm_text,
        "swarm workflow should defer the raw-file cap to scripts/wiki_swarm.py manifest",
    )
    forbidden_script_duplications = (
        "scripts/capture_gate.py",
        "scripts/validate_capture_runs.py",
        "scripts/rebuild_referenced_by.py",
        "scripts/lint.py --tier1",
    )
    results.record(
        "swarm-doc-does-not-duplicate-analysis-capture-script-list",
        all(marker not in swarm_text for marker in forbidden_script_duplications)
        and "## Analysis Capture" in research_text
        and "workflows/research/CONTEXT.md#analysis-capture" in swarm_text,
        "swarm workflow duplicates normal research analysis-capture mechanics",
    )
    for label, text in (("claude", claude_text), ("codex", codex_text)):
        results.record(
            f"{label}-swarm-wrapper-routes-through-root",
            "AGENTS.md" in text and "CONTEXT.md" in text and "workflows/research/wiki-swarm.md" not in text,
            f"{label} wrapper should stay a thin root-router pointer",
        )


check_preflight()
check_manifest()
check_packet_validation()
check_docs_contract()

sys.exit(results.finish())
