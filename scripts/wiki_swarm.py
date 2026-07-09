#!/usr/bin/env python3
"""Deterministic guardrails for the wiki-swarm research overlay.

The script does not spawn agents or synthesize answers. It owns the checkable
policy around explicit invocation, read-only helper lanes, and packet shape so
the prose workflow can stay thin and inspectable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


TRIGGER_PHRASES = (
    "/wiki-swarm",
    "wiki-swarm",
    "swarm the wiki answer",
)

NON_TRIGGER_EXAMPLES = (
    "be thorough",
    "use agents",
    "high-stakes wording",
    "standalone swarm",
)


@dataclass(frozen=True)
class Lane:
    name: str
    responsibility: str
    allowed_outputs: tuple[str, ...]
    read_only: bool = True
    may_edit_files: bool = False
    may_run_durable_writes: bool = False
    may_send_external_output: bool = False
    may_decide_final_synthesis: bool = False


LANES = (
    Lane(
        name="planner",
        responsibility="Restate the question, intended output, source scope, and stop conditions.",
        allowed_outputs=("question", "output shape", "scope", "stop conditions"),
    ),
    Lane(
        name="page-scout",
        responsibility="Use wiki/index.md and wiki/primer.md to identify and narrow candidate pages.",
        allowed_outputs=("candidate pages", "consulted page list", "scope notes"),
    ),
    Lane(
        name="evidence-extractor",
        responsibility="Extract source-backed facts from consulted pages with wiki citations.",
        allowed_outputs=("cited facts", "source-backed notes"),
    ),
    Lane(
        name="raw-evidence-extractor",
        responsibility=(
            "When triggered, spot-check targeted raw files named in consulted-page provenance; "
            "otherwise report a qualified skip."
        ),
        allowed_outputs=(
            "raw files checked",
            "extraction methods",
            "extraction limits",
            "raw-only findings",
            "qualified skip",
        ),
    ),
    Lane(
        name="contradiction-staleness-checker",
        responsibility="Check relevant contradictions and stale/current-state claims.",
        allowed_outputs=("contradictions", "stale areas", "open conflicts"),
    ),
    Lane(
        name="synthesizer",
        responsibility="Draft the answer, separating source-backed facts from inference.",
        allowed_outputs=("answer draft", "inferences", "support notes"),
    ),
    Lane(
        name="reviewer",
        responsibility="Check citation coverage, unsupported leaps, missed pages, stale claims, and durable-write routing.",
        allowed_outputs=("review notes", "gaps", "recommended route"),
    ),
)

PACKET_SECTIONS = (
    "Verdict",
    "Question",
    "Source scope",
    "Pages consulted",
    "Lane results",
    "Supported facts",
    "Inferences",
    "Contradictions or stale areas",
    "Raw sources checked",
    "Raw extraction limits",
    "Raw-only findings",
    "Answer",
    "What not to say",
    "Checks actually run",
    "Durable-write status",
    "Promotion audit",
)

VALID_VERDICTS = ("NORMAL RESEARCH", "SINGLE-AGENT SWARM", "SPLIT LANES", "STOP")
SECTION_RE = re.compile(r"^([A-Z][A-Za-z -]+):\s*(.*)$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
PATH_PAGE_RE = re.compile(r"(?:wiki/)?(?:[a-z0-9-]+/)*([a-z0-9-]+)\.md")
RAW_PATH_RE = re.compile(r"\braw/[^\s),;]+")
REQUIRED_CONSULTED_PAGES = {
    "index": ("[[index]]", "wiki/index.md"),
    "primer": ("[[primer]]", "wiki/primer.md"),
}
CITATION_REQUIRED_SECTIONS = ("Supported facts", "Answer")
RAW_CHECK_REQUIRED_MARKERS = (
    "complete history",
    "full record",
    "primary source",
    "reconstruct",
    "all documents",
    "every invoice",
    "exact timeline",
)
RAW_QUALIFIED_SKIP_MARKERS = (
    "not triggered",
    "not required",
    "no raw verification",
    "compiled-only",
    "ordinary lookup",
    "simple lookup",
    "orientation question",
)
RAW_ONLY_QUALIFIED_NONE_MARKERS = (
    "none - no raw-only findings",
    "no raw-only findings",
    "not triggered - no raw verification performed",
)
RAW_ONLY_REINGEST_MARKERS = (
    "re-ingest",
    "update source page",
    "sourcing-queue",
)
CONTRADICTION_PAGE_MARKERS = ("[[contradictions]]", "wiki/contradictions.md", "contradictions.md")
CONTRADICTION_REQUIRED_MARKERS = (
    "current",
    "current-state",
    "open priorities",
    "property",
    "account",
    "customer",
    "vendor",
    "status",
    "maintenance",
    "stale",
    "contradiction",
)
CONTRADICTION_DISMISSAL_MARKERS = (
    "none found",
    "not applicable",
    "no contradiction",
    "no contradictions",
)
CONTRADICTION_QUALIFIED_CLEAR_MARKERS = (
    "no relevant",
    "no material",
    "not relevant",
)
CITATION_INTEGRITY_FAILURE_MARKERS = (
    "citation may not support",
    "may not support",
    "could be unrelated",
    "unrelated citation",
    "citation is unrelated",
    "unsupported citation",
)
DURABLE_CLAIM_MARKERS = (
    "filed analysis",
    "analysis filed",
    "filed as wiki/analyses",
    "saved analysis",
    "saved to wiki/analyses",
    "wrote analysis",
    "wrote wiki/analyses",
    "durable write completed",
)
DURABLE_APPROVAL_PROOF_MARKERS = (
    "capture-runs.jsonl",
    "approval record",
    "approved capture record",
)
DURABLE_VALIDATION_PROOF_MARKERS = (
    "validate_capture_runs.py",
    "validate capture runs",
)
DURABLE_DESTINATION_MARKERS = (
    "primary home",
    "primary_home",
    "wiki/analyses/",
)
NEGATORS = (
    "no",
    "not",
    "never",
    "without",
    "did not",
    "didn't",
    "must not",
    "may not",
    "should not",
    "cannot",
    "can't",
)


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def has_marker(text: str, markers: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(normalize(marker) in normalized for marker in markers)


def has_wikilink(text: str) -> bool:
    return bool(WIKILINK_RE.search(text))


def canonical_page_name(raw: str) -> str:
    target = raw.split("|", 1)[0].strip()
    target = target.rstrip("/")
    if "/" in target:
        target = target.rsplit("/", 1)[-1]
    if target.endswith(".md"):
        target = target[:-3]
    return normalize(target)


def wikilinks(text: str) -> set[str]:
    return {canonical_page_name(match.group(1)) for match in WIKILINK_RE.finditer(text)}


def raw_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in RAW_PATH_RE.finditer(text):
        paths.append(match.group(0).rstrip(".,:"))
    return paths


def page_mentions(text: str) -> set[str]:
    mentions = set(wikilinks(text))
    raw_spans = [match.span() for match in RAW_PATH_RE.finditer(text)]
    for match in PATH_PAGE_RE.finditer(text):
        if any(match.start() >= start and match.end() <= end for start, end in raw_spans):
            continue
        mentions.add(normalize(match.group(1)))
    return mentions


def has_self_disclaimed_citation_support(text: str) -> bool:
    return has_marker(text, CITATION_INTEGRITY_FAILURE_MARKERS)


def has_unqualified_contradiction_dismissal(text: str) -> bool:
    if has_marker(text, CONTRADICTION_QUALIFIED_CLEAR_MARKERS):
        return False
    return has_marker(text, CONTRADICTION_DISMISSAL_MARKERS)


def raw_check_required(sections: dict[str, str]) -> bool:
    return has_marker(sections.get("Question", ""), RAW_CHECK_REQUIRED_MARKERS)


def has_qualified_raw_skip(text: str) -> bool:
    return has_marker(text, RAW_QUALIFIED_SKIP_MARKERS)


def has_qualified_raw_only_none(text: str) -> bool:
    return has_marker(text, RAW_ONLY_QUALIFIED_NONE_MARKERS)


def has_raw_only_finding(text: str) -> bool:
    return bool(text.strip()) and not has_qualified_raw_only_none(text)


def is_negated(prefix: str) -> bool:
    prefix = normalize(prefix)
    return any(prefix.endswith(f"{negator} ") or prefix.endswith(negator) for negator in NEGATORS)


def has_unnegated_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    for phrase in phrases:
        pattern = re.escape(normalize(phrase))
        for match in re.finditer(pattern, normalized):
            prefix = normalized[max(0, match.start() - 40):match.start()]
            if is_negated(prefix):
                continue
            return True
    return False


def has_explicit_trigger(question: str) -> bool:
    text = normalize(question)
    return any(trigger in text for trigger in TRIGGER_PHRASES)


def is_standalone_swarm(question: str) -> bool:
    text = normalize(question)
    return bool(re.search(r"\bswarm\b", text)) and not has_explicit_trigger(question)


def registry() -> dict[str, object]:
    return {
        "trigger_phrases": TRIGGER_PHRASES,
        "non_trigger_examples": NON_TRIGGER_EXAMPLES,
        "lanes": [asdict(lane) for lane in LANES],
        "packet_sections": PACKET_SECTIONS,
        "valid_verdicts": VALID_VERDICTS,
        "required_consulted_pages": tuple(REQUIRED_CONSULTED_PAGES),
        "citation_required_sections": CITATION_REQUIRED_SECTIONS,
        "raw_check_required_markers": RAW_CHECK_REQUIRED_MARKERS,
        "raw_qualified_skip_markers": RAW_QUALIFIED_SKIP_MARKERS,
        "raw_only_qualified_none_markers": RAW_ONLY_QUALIFIED_NONE_MARKERS,
        "raw_only_reingest_markers": RAW_ONLY_REINGEST_MARKERS,
        "citation_integrity_failure_markers": CITATION_INTEGRITY_FAILURE_MARKERS,
        "contradiction_page_markers": CONTRADICTION_PAGE_MARKERS,
        "contradiction_page_required_when": CONTRADICTION_REQUIRED_MARKERS,
        "contradiction_dismissal_markers": CONTRADICTION_DISMISSAL_MARKERS,
        "durable_write_claim_markers": DURABLE_CLAIM_MARKERS,
        "durable_write_approval_proof_markers": DURABLE_APPROVAL_PROOF_MARKERS,
        "durable_write_validation_proof_markers": DURABLE_VALIDATION_PROOF_MARKERS,
        "durable_write_destination_markers": DURABLE_DESTINATION_MARKERS,
        "analysis_capture_owner": "workflows/research/CONTEXT.md#analysis-capture",
    }


def print_manifest(*, json_mode: bool = False) -> None:
    if json_mode:
        print(json.dumps(registry(), indent=2, sort_keys=True))
        return
    print("WIKI-SWARM MANIFEST")
    print("Trigger phrases:")
    for trigger in TRIGGER_PHRASES:
        print(f"- {trigger}")
    print("Non-trigger examples:")
    for example in NON_TRIGGER_EXAMPLES:
        print(f"- {example}")
    print("Lanes:")
    for lane in LANES:
        print(f"- {lane.name}: read_only={str(lane.read_only).lower()}; {lane.responsibility}")
    print("Packet sections:")
    for section in PACKET_SECTIONS:
        print(f"- {section}")


def run_preflight(question: str, *, json_mode: bool = False) -> int:
    accepted = has_explicit_trigger(question)
    if json_mode:
        print(json.dumps({
            "accepted": accepted,
            "reason": "explicit wiki-swarm trigger" if accepted else "no explicit wiki-swarm trigger",
            "standalone_swarm": is_standalone_swarm(question),
            "lanes": [asdict(lane) for lane in LANES] if accepted else [],
        }, indent=2, sort_keys=True))
        return 0 if accepted else 2

    if not accepted:
        if is_standalone_swarm(question):
            print("WIKI-SWARM PREFLIGHT: REJECTED")
            print("Reason: standalone 'swarm' is not enough; use the explicit wiki-swarm boundary.")
        else:
            print("WIKI-SWARM PREFLIGHT: REJECTED")
            print("Reason: no explicit wiki-swarm trigger. Use normal research.")
        return 2

    print("WIKI-SWARM PREFLIGHT: ACCEPTED")
    print("Reason: explicit wiki-swarm trigger.")
    print("Helper lanes are read-only and may not edit files, run durable writes, send external output, or decide final synthesis.")
    print("Required lanes:")
    for lane in LANES:
        print(f"- {lane.name}: {lane.responsibility}")
    return 0


def packet_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if match and match.group(1) in PACKET_SECTIONS:
            current = match.group(1)
            sections[current] = [match.group(2)]
            continue
        if current:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def non_stop_verdict(verdict: str) -> bool:
    return bool(verdict) and verdict != "STOP"


def needs_contradiction_page(sections: dict[str, str]) -> bool:
    combined = " ".join(
        sections.get(section, "")
        for section in ("Question", "Source scope", "Pages consulted", "Answer")
    )
    return has_marker(combined, CONTRADICTION_REQUIRED_MARKERS)


def validate_packet_text(text: str) -> list[str]:
    problems: list[str] = []
    stripped = text.lstrip()
    if not stripped.startswith("WIKI-SWARM PACKET"):
        problems.append("packet must start with WIKI-SWARM PACKET")

    sections = packet_sections(text)
    for section in PACKET_SECTIONS:
        if section not in sections:
            problems.append(f"missing packet section: {section}")

    verdict = sections.get("Verdict", "").splitlines()[0].strip() if sections.get("Verdict") else ""
    if verdict not in VALID_VERDICTS:
        problems.append(f"invalid verdict: {verdict or '<empty>'}")

    checks = normalize(sections.get("Checks actually run", ""))
    proposed_markers = ("proposed", "planned", "would run", "should run", "not yet run")
    if any(marker in checks for marker in proposed_markers):
        problems.append("Checks actually run must not list proposed or planned checks")
    if non_stop_verdict(verdict) and "preflight" not in checks:
        problems.append("Checks actually run must include preflight for non-STOP packets")

    if non_stop_verdict(verdict):
        pages = sections.get("Pages consulted", "")
        consulted_pages = page_mentions(pages)
        for page_name, markers in REQUIRED_CONSULTED_PAGES.items():
            if not has_marker(pages, markers):
                problems.append(f"Pages consulted must include [[{page_name}]] for non-STOP packets")

        for section in CITATION_REQUIRED_SECTIONS:
            section_text = sections.get(section, "")
            if raw_paths(section_text):
                problems.append(f"{section} must not include raw/ paths")
            cited_pages = wikilinks(section_text)
            if not cited_pages:
                problems.append(f"{section} must include at least one wiki citation")
            unconsulted = sorted(cited_pages - consulted_pages)
            if unconsulted:
                problems.append(
                    f"{section} cites pages not listed in Pages consulted: {', '.join(unconsulted)}"
                )
            if has_self_disclaimed_citation_support(section_text):
                problems.append(f"{section} must not disclaim or weaken its own citation support")

        contradictions = sections.get("Contradictions or stale areas", "")
        if needs_contradiction_page(sections):
            if not has_marker(pages, CONTRADICTION_PAGE_MARKERS):
                problems.append(
                    "current-state, status, maintenance, or contradiction-sensitive packets must consult [[contradictions]]"
                )
            if not has_marker(contradictions, CONTRADICTION_PAGE_MARKERS):
                problems.append(
                    "Contradictions or stale areas must cite [[contradictions]] for contradiction-sensitive packets"
                )
            if has_unqualified_contradiction_dismissal(contradictions):
                problems.append(
                    "Contradictions or stale areas must not dismiss a contradiction-sensitive packet as none or not applicable without a relevance-qualified register note"
                )

        raw_checked = sections.get("Raw sources checked", "")
        raw_limits = sections.get("Raw extraction limits", "")
        raw_only = sections.get("Raw-only findings", "")
        checked_raw_paths = raw_paths(raw_checked)
        if raw_check_required(sections) and not checked_raw_paths and not has_qualified_raw_skip(raw_checked):
            problems.append(
                "Raw sources checked must list checked raw files or a qualified skip when the question asks for completeness or primary-source reconstruction"
            )
        if checked_raw_paths and not raw_limits.strip():
            problems.append("Raw extraction limits must be stated when raw sources are checked")
        if has_raw_only_finding(raw_only):
            if not checked_raw_paths:
                problems.append("Raw-only findings require at least one raw file in Raw sources checked")
            if not has_marker(raw_only, RAW_ONLY_REINGEST_MARKERS):
                problems.append(
                    "Raw-only findings must recommend re-ingest, source-page update, or sourcing-queue follow-up"
                )

    lane_results = normalize(sections.get("Lane results", ""))
    if has_unnegated_phrase(
        lane_results,
        (
            "edit files",
            "edited file",
            "edited files",
            "write files",
            "wrote file",
            "wrote files",
            "durable write",
            "sent external",
            "sent external output",
        ),
    ):
        problems.append("helper lanes must stay read-only and non-writing")

    durable = normalize(sections.get("Durable-write status", ""))
    if has_unnegated_phrase(durable, DURABLE_CLAIM_MARKERS):
        if has_raw_only_finding(sections.get("Raw-only findings", "")):
            problems.append("packets with raw-only findings must not claim an analysis was filed")
        if "analysis-capture" not in durable and "workflows/research/context.md#analysis-capture" not in durable:
            problems.append("durable analysis filing must route through normal research analysis-capture")
        if not has_marker(durable, DURABLE_APPROVAL_PROOF_MARKERS):
            problems.append("durable analysis filing must name an approval record such as scripts/capture-runs.jsonl")
        if not has_marker(durable, DURABLE_VALIDATION_PROOF_MARKERS):
            problems.append("durable analysis filing must name validate_capture_runs.py proof")
        if not has_marker(durable, DURABLE_DESTINATION_MARKERS):
            problems.append("durable analysis filing must name the primary destination")
    if has_unnegated_phrase(durable, ("bypassed", "direct write", "without approval")):
        problems.append("durable-write status claims a bypass or direct write")

    return problems


def run_validate_packet(path: Path, *, json_mode: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    problems = validate_packet_text(text)
    if json_mode:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2, sort_keys=True))
    elif problems:
        print("WIKI-SWARM PACKET: INVALID")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("WIKI-SWARM PACKET: valid")
    return 1 if problems else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic guardrails for wiki-swarm.")
    sub = p.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="Print canonical swarm policy.")
    manifest.add_argument("--json", action="store_true", help="Emit JSON.")

    preflight = sub.add_parser("preflight", help="Check whether a request explicitly invokes wiki-swarm.")
    preflight.add_argument("--question", required=True)
    preflight.add_argument("--json", action="store_true", help="Emit JSON.")

    validate = sub.add_parser("validate-packet", help="Validate a completed WIKI-SWARM PACKET.")
    validate.add_argument("--packet", required=True, type=Path)
    validate.add_argument("--json", action="store_true", help="Emit JSON.")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "manifest":
        print_manifest(json_mode=args.json)
        return 0
    if args.command == "preflight":
        return run_preflight(args.question, json_mode=args.json)
    if args.command == "validate-packet":
        return run_validate_packet(args.packet, json_mode=args.json)
    raise AssertionError(f"unknown command {args.command}")


if __name__ == "__main__":
    sys.exit(main())
