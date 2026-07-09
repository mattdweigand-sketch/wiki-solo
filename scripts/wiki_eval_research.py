#!/usr/bin/env python3
"""Regression evals for the wiki-research runtime and workflow contract.

The suite runs the runtime against a hermetic fixture corpus that exercises provenance
closure (slug chains, authority_ref, cycles, dangling refs, multi-path chains),
high-stakes answer eligibility (type allowlist, owner registry, analysis
precedence), the claim-ledger grammar, quote anchoring with decoy regions, and
the answer grammar.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results


REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH = REPO_ROOT / "scripts" / "wiki_research.py"
ROOT_CONTEXT = REPO_ROOT / "CONTEXT.md"
RESEARCH_CONTEXT = REPO_ROOT / "workflows" / "research" / "CONTEXT.md"
RESEARCH_WORKFLOW = REPO_ROOT / "workflows" / "research" / "wiki-research.md"
CLAUDE_WRAPPER = REPO_ROOT / ".claude" / "commands" / "wiki-research.md"
CODEX_WRAPPER = REPO_ROOT / ".codex" / "skills" / "wiki-research" / "SKILL.md"

results = Results()


def run_research(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RESEARCH), *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


def packet_path(body: str) -> Path:
    path = Path(tempfile.mkdtemp(prefix="wiki-research-eval-")) / "packet.md"
    path.write_text(body, encoding="utf-8")
    return path


def build_fixture_root() -> Path:
    """Hermetic mini-corpus so corpus-aware packet checks never depend on the
    live wiki's contents. Raw files exist on disk because the ledger checks
    existence; page bodies carry known quotable sentences plus decoy text in
    every stripped region."""
    root = Path(tempfile.mkdtemp(prefix="wiki-research-eval-corpus-"))
    for folder in ("customers", "sources", "decisions", "analyses", "metrics", "concepts", "people"):
        (root / "wiki" / folder).mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "raw" / "records").mkdir(parents=True)

    raw_files = ["policy.pdf", "kitchen-binder.pdf", "cycle.pdf", "shared.pdf", "authority.pdf"]
    raw_files += [f"r{i:02d}.pdf" for i in range(1, 11)]
    for name in raw_files:
        (root / "raw" / "records" / name).write_text("fixture raw artifact\n", encoding="utf-8")
    # A raw-tree symlink that resolves outside root/raw, for containment checks.
    (root / "raw" / "records" / "escape.pdf").symlink_to(
        Path("..") / ".." / "wiki" / "sources" / "home-policy.md"
    )

    def page(rel: str, frontmatter: str, body: str) -> None:
        (root / "wiki" / rel).write_text(
            f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8"
        )

    page("index.md", "title: Index\ntype: meta", "Corpus index fixture.")
    page("primer.md", "title: Primer\ntype: meta", "Corpus primer fixture.")
    page("contradictions.md", "title: Contradictions\ntype: meta", "Register fixture.")
    page(
        "customers/current-account.md",
        "title: Current Account\ntype: customer",
        "Current-state fixture.",
    )
    binder_sources = ", ".join(
        ["raw/records/kitchen-binder.pdf"] + [f"raw/records/r{i:02d}.pdf" for i in range(1, 11)]
    )
    page(
        "sources/kitchen-binder.md",
        f"title: Kitchen Binder\ntype: source\nsources: [{binder_sources}]",
        "Source page fixture for raw provenance checks.",
    )
    page(
        "sources/home-policy.md",
        "title: Home Policy\ntype: source\n"
        "sources: [raw/records/policy.pdf]\n"
        "decoy_note: frontmatter decoy phrase alpha",
        "The policy summary for the fixture home.\n"
        "\n"
        "Flood damage is excluded under section 4. Wind damage is covered in full.\n"
        "\n"
        "```\n"
        "codefence decoy phrase gamma\n"
        "```\n"
        "\n"
        "## Related pages\n"
        "\n"
        "- related decoy phrase beta [[index]]\n"
        "\n"
        "## Referenced by\n"
        "\n"
        "- referenced decoy phrase delta",
    )
    page(
        "decisions/roof-repair.md",
        "title: Roof Repair\ntype: decision",
        "The decision chose repair over full replacement after two quotes.",
    )
    page(
        "analyses/cost-summary.md",
        "title: Cost Summary\ntype: analysis",
        "The analysis restates the compiled totals for planning.",
    )
    page(
        "metrics/protocol.md",
        "title: Protocol\ntype: metric",
        "The page records the regimen as owner-verified truth.",
    )
    page(
        "concepts/free-concept.md",
        "title: Free Concept\ntype: concept",
        "The concept stands alone without sources and records a framework.",
    )
    page(
        "concepts/laundered-concept.md",
        "title: Laundered Concept\ntype: concept\nsources: [home-policy]",
        "The concept restates the exclusion from the policy source page.",
    )
    page(
        "concepts/dangling-source.md",
        "title: Dangling Source\ntype: concept\nsources: [missing-source]",
        "This concept cites a source page that does not exist.",
    )
    page(
        "concepts/dangling-authority.md",
        "title: Dangling Authority\ntype: concept\nauthority_kind: source-page\n"
        "authority_ref: wiki/sources/missing.md",
        "This concept names an authority file that does not exist.",
    )
    page(
        "concepts/authority-raw.md",
        "title: Authority Raw\ntype: concept\nauthority_kind: raw-source\n"
        "authority_ref: raw/records/authority.pdf",
        "This concept carries raw provenance only through authority_ref.",
    )
    page(
        "concepts/traversal-provenance.md",
        "title: Traversal Provenance\ntype: concept\nsources: [raw/../wiki/sources/fake-raw.md]",
        "This concept names a traversal raw path in provenance.",
    )
    page(
        "concepts/escape-provenance.md",
        "title: Escape Provenance\ntype: concept\nsources: [raw/records/escape.pdf]",
        "This concept cites a symlink that escapes the raw tree.",
    )
    page(
        "sources/cycle-a.md",
        "title: Cycle A\ntype: source\nsources: [cycle-b]",
        "Cycle fixture page A.",
    )
    page(
        "sources/cycle-b.md",
        "title: Cycle B\ntype: source\nsources: [cycle-a, raw/records/cycle.pdf]",
        "Cycle fixture page B.",
    )
    page(
        "concepts/shared-fact.md",
        "title: Shared Fact\ntype: concept\nsources: [chain-one, chain-two]",
        "A fact reachable through two source chains.",
    )
    page(
        "sources/chain-one.md",
        "title: Chain One\ntype: source\nsources: [raw/records/shared.pdf]",
        "First chain to the shared raw file.",
    )
    page(
        "sources/chain-two.md",
        "title: Chain Two\ntype: source\nsources: [raw/records/shared.pdf]",
        "Second chain to the shared raw file.",
    )
    page(
        "people/casual-person.md",
        "title: Casual Person\ntype: person",
        "A person page that is neither wiki-native for eligibility nor owner-registered.",
    )
    (root / "scripts" / "current-state-owners.json").write_text(
        json.dumps([
            "customers/current-account.md",
            "analyses/cost-summary.md",
            "metrics/protocol.md",
        ]) + "\n",
        encoding="utf-8",
    )
    return root


FIXTURE_ROOT = build_fixture_root()


def validate_packet(path_str: str) -> subprocess.CompletedProcess[str]:
    return run_research("validate-packet", "--packet", path_str, "--root", str(FIXTURE_ROOT))


def expect_valid(name: str, body: str) -> None:
    proc = validate_packet(str(packet_path(body)))
    results.record(name, proc.returncode == 0 and "valid" in proc.stdout, proc.stdout + proc.stderr)


def expect_invalid(name: str, body: str, *markers: str) -> None:
    proc = validate_packet(str(packet_path(body)))
    ok = proc.returncode == 1 and all(marker in proc.stdout for marker in markers)
    results.record(name, ok, proc.stdout + proc.stderr)


LANE_RESULTS = (
    "Lane results: Planner scoped the question; Page Scout tagged page relevance; "
    "Evidence Extractor built the claim ledger; Raw Verifier stated the raw decision; "
    "Contradiction Staleness Checker surfaced open conflicts; Synthesizer drafted the answer; "
    "Citation Auditor completed the citation audit; Reviewer completed scope-retention review; "
    "helper lanes returned notes only."
)

GOOD_STANDARD = f"""WIKI-RESEARCH PACKET
Verdict: DEEP RESEARCH
Question: /wiki-research what did the roof decision choose?
Stakes: standard
Source scope: wiki/index.md, wiki/primer.md, selected pages
Pages consulted: [[index]], [[primer]], [[roof-repair]]
{LANE_RESULTS}
Claim ledger:
C1. The roof decision chose repair over replace | wiki: [[roof-repair]] | quote: "chose repair over full replacement" | status: wiki-backed
C2. Cost drove the choice | from: C1 | status: inference
Contradictions or stale areas: no relevant conflicts for this narrow decision question
Raw sources checked: not checked - orientation question, compiled pages suffice
Raw extraction limits: none - raw was not checked
Raw coverage: 0 raw-verified / 1 wiki-backed / 0 raw-only / 1 inference of 2 claims; waiver: orientation question
Raw-only findings: none - no raw-only findings
Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].
What not to say: do not overclaim beyond the decision page
Checks actually run: preflight, packet validation
Durable-write status: chat-only; no durable write
Promotion audit: none
"""

GOOD_HIGH = f"""WIKI-RESEARCH PACKET
Verdict: DEEP RESEARCH
Question: /wiki-research does the home policy exclude flood damage? treat as an insurance check
Stakes: high (insurance)
Source scope: wiki/index.md, wiki/primer.md, selected pages
Pages consulted: [[index]], [[primer]], [[home-policy]]
{LANE_RESULTS}
Claim ledger:
C1. The policy excludes flood damage | wiki: [[home-policy]] | raw: [policy.pdf p.12](raw/records/policy.pdf) | quote: "flood damage is excluded under section 4" | status: raw-verified
Contradictions or stale areas: no relevant conflicts for this question
Raw sources checked: raw/records/policy.pdf via pdftotext -layout
Raw extraction limits: no unreadable regions found in the extracted text
Raw coverage: 1 raw-verified / 0 wiki-backed / 0 raw-only / 0 inference of 1 claims; waiver: none
Raw-only findings: none - no raw-only findings
Answer: The policy excludes flood damage [C1].
What not to say: do not extend the exclusion beyond section 4
Checks actually run: preflight, packet validation
Durable-write status: chat-only; no durable write
Promotion audit: none
"""


def waiver_packet(slug: str, quote: str, *, extra_pages: str = "", question_tail: str = "for a legal check",
                  contradictions: str = "no relevant conflicts for this question",
                  waiver: str = "no raw provenance exists across consulted pages",
                  coverage_waiver: str = "no raw provenance exists",
                  claim_extra: str = "", answer: str = "The cited page supports the claim [C1].") -> str:
    """High-stakes packet whose only claim is wiki-backed against `slug`, with
    the raw check waived. The eligibility, waiver, and closure fixtures all
    derive from this shape."""
    return f"""WIKI-RESEARCH PACKET
Verdict: DEEP RESEARCH
Question: /wiki-research summarize the cited page {question_tail}
Stakes: high (legal)
Source scope: wiki/index.md, wiki/primer.md, selected pages
Pages consulted: [[index]], [[primer]], [[{slug}]]{extra_pages}
{LANE_RESULTS}
Claim ledger:
C1. The cited page supports the claim | wiki: [[{slug}]]{claim_extra} | quote: "{quote}" | status: wiki-backed
Contradictions or stale areas: {contradictions}
Raw sources checked: not checked - {waiver}
Raw extraction limits: none - raw was not checked
Raw coverage: 0 raw-verified / 1 wiki-backed / 0 raw-only / 0 inference of 1 claims; waiver: {coverage_waiver}
Raw-only findings: none - no raw-only findings
Answer: {answer}
What not to say: do not overclaim
Checks actually run: preflight, packet validation
Durable-write status: chat-only; no durable write
Promotion audit: none
"""


def check_preflight() -> None:
    accepted = run_research("preflight", "--question", "/wiki-research answer this from the wiki")
    results.record(
        "explicit-trigger-accepted",
        accepted.returncode == 0
        and "PREFLIGHT: ACCEPTED" in accepted.stdout
        and "Raw confirmation is the default" in accepted.stdout,
        accepted.stdout + accepted.stderr,
    )

    phrase = run_research("preflight", "--question", "please deep research the wiki on the roof")
    results.record(
        "deep-research-phrase-accepted",
        phrase.returncode == 0 and "PREFLIGHT: ACCEPTED" in phrase.stdout,
        phrase.stdout + phrase.stderr,
    )

    for name, question in (
        ("legacy-slash-trigger-tombstoned", "/wiki-swarm answer this from the wiki"),
        ("legacy-word-trigger-tombstoned", "run wiki-swarm on this"),
    ):
        proc = run_research("preflight", "--question", question)
        results.record(
            name,
            proc.returncode == 2
            and "PREFLIGHT: REJECTED" in proc.stdout
            and "renamed to wiki-research" in proc.stdout,
            proc.stdout + proc.stderr,
        )

    for name, question in (
        ("ordinary-broad-rejected", "answer this carefully from the wiki"),
        ("use-agents-rejected", "be thorough and use agents"),
        ("standalone-research-rejected", "research this problem thoroughly"),
        ("standalone-swarm-rejected", "swarm this problem"),
    ):
        proc = run_research("preflight", "--question", question)
        results.record(
            name,
            proc.returncode == 2
            and "PREFLIGHT: REJECTED" in proc.stdout
            and "renamed" not in proc.stdout,
            proc.stdout + proc.stderr,
        )


def check_manifest() -> None:
    proc = run_research("manifest", "--json")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        data = {}
    lanes = data.get("lanes", [])
    lane_names = [lane.get("name") for lane in lanes]
    ok = (
        proc.returncode == 0
        and data.get("trigger_phrases") == ["/wiki-research", "wiki-research", "deep research the wiki"]
        and data.get("legacy_trigger_phrases") == ["/wiki-swarm", "wiki-swarm", "swarm the wiki answer"]
        and "renamed to wiki-research" in data.get("legacy_tombstone", "")
        and data.get("claim_statuses") == ["raw-verified", "wiki-backed", "raw-only", "inference"]
        and data.get("claim_field_keys") == ["wiki", "raw", "from", "status", "quote"]
        and data.get("max_quote_words") == 15
        and data.get("max_raw_files") == 10
        and data.get("high_stakes_categories") == ["legal", "medical", "financial", "insurance", "property"]
        and data.get("high_stakes_wiki_native_types") == ["decision", "goal", "learning", "concept"]
        and data.get("raw_waiver_markers") == [
            "no raw provenance exists",
            "orientation question",
            "user waived raw confirmation",
        ]
        and "citation audit" in data.get("citation_audit_markers", [])
        and data.get("answer_eligibility_registry") == "scripts/current-state-owners.json"
        and data.get("current_state_owner_registry") == "scripts/current-state-owners.json"
        and data.get("valid_verdicts") == ["NORMAL RESEARCH", "DEEP RESEARCH", "SPLIT LANES", "STOP"]
        and data.get("research_verdicts") == ["DEEP RESEARCH", "SPLIT LANES"]
        and len(lanes) == 8
        and lane_names == [
            "planner",
            "page-scout",
            "evidence-extractor",
            "raw-verifier",
            "contradiction-staleness-checker",
            "synthesizer",
            "citation-auditor",
            "reviewer",
        ]
        and all(lane.get("read_only") is True for lane in lanes)
        and all(lane.get("may_edit_files") is False for lane in lanes)
        and all(lane.get("may_run_durable_writes") is False for lane in lanes)
        and all(lane.get("may_send_external_output") is False for lane in lanes)
        and all(lane.get("may_decide_final_synthesis") is False for lane in lanes)
        and "Stakes" in data.get("packet_sections", [])
        and "Claim ledger" in data.get("packet_sections", [])
        and "Raw coverage" in data.get("packet_sections", [])
        and "Supported facts" not in data.get("packet_sections", [])
        and "Inferences" not in data.get("packet_sections", [])
        and "Claim ledger" in data.get("scope_retention_output_targets", [])
    )
    results.record("manifest-pins-research-policy", ok, proc.stdout + proc.stderr)

    fixture_manifest = run_research("manifest", "--json", "--root", str(FIXTURE_ROOT))
    try:
        fixture_data = json.loads(fixture_manifest.stdout)
    except json.JSONDecodeError:
        fixture_data = {}
    fixture_markers = fixture_data.get("contradiction_page_required_when", [])
    results.record(
        "contradiction-markers-derive-from-current-state-registry",
        fixture_manifest.returncode == 0
        and "current-account" in fixture_markers
        and "current account" in fixture_markers
        and "cost summary" in fixture_markers
        and "protocol" in fixture_markers
        and "current" in fixture_markers,
        fixture_manifest.stdout + fixture_manifest.stderr,
    )


def check_packet_shape() -> None:
    expect_valid("valid-standard-deep-packet-passes", GOOD_STANDARD)
    expect_valid("valid-high-stakes-raw-verified-packet-passes", GOOD_HIGH)

    expect_invalid(
        "missing-section-fails",
        GOOD_STANDARD.replace("Promotion audit: none\n", ""),
        "missing packet section: Promotion audit",
    )
    expect_invalid(
        "empty-verdict-fails",
        GOOD_STANDARD.replace("Verdict: DEEP RESEARCH", "Verdict:"),
        "invalid verdict",
    )
    expect_invalid(
        "proposed-check-claim-fails",
        GOOD_STANDARD.replace(
            "Checks actually run: preflight, packet validation",
            "Checks actually run: preflight, proposed lint and planned packet validation",
        ),
        "proposed or planned",
    )
    expect_invalid(
        "helper-write-claim-fails",
        GOOD_STANDARD.replace("helper lanes returned notes only", "helper lanes edited files and returned notes"),
        "read-only",
    )
    expect_valid(
        "negated-helper-write-claim-passes",
        GOOD_STANDARD.replace(
            "helper lanes returned notes only.",
            "helper lanes returned notes only; no durable write was requested.",
        ),
    )
    expect_invalid(
        "missing-scope-retention-review-fails",
        GOOD_STANDARD.replace(
            "Reviewer completed scope-retention review",
            "Reviewer completed the routing review",
        ),
        "scope-retention review",
    )
    expect_invalid(
        "missing-lane-report-fails",
        GOOD_STANDARD.replace("Synthesizer drafted the answer; ", ""),
        "Lane results must report the synthesizer lane",
    )
    expect_invalid(
        "missing-citation-auditor-fails",
        GOOD_STANDARD.replace("Citation Auditor completed the citation audit; ", ""),
        "Lane results must report the citation-auditor lane",
        "citation audit for research-verdict packets",
    )
    expect_valid(
        "normal-research-verdict-skips-lane-reporting",
        GOOD_STANDARD.replace("Verdict: DEEP RESEARCH", "Verdict: NORMAL RESEARCH").replace(
            LANE_RESULTS,
            "Lane results: Reviewer completed scope-retention review; helper lanes returned notes only.",
        ),
    )
    expect_invalid(
        "missing-index-primer-fails",
        GOOD_STANDARD.replace(
            "Pages consulted: [[index]], [[primer]], [[roof-repair]]",
            "Pages consulted: [[roof-repair]]",
        ),
        "Pages consulted must include [[index]]",
        "Pages consulted must include [[primer]]",
    )
    expect_invalid(
        "duplicate-answer-section-fails",
        GOOD_STANDARD.replace(
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
            "Answer: an unanchored first answer with no claim identifiers\n"
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
        ),
        "duplicate packet section: Answer",
    )
    expect_invalid(
        "duplicate-raw-sources-section-fails",
        GOOD_STANDARD.replace(
            "Raw sources checked: not checked - orientation question, compiled pages suffice",
            "Raw sources checked: not checked - orientation question, compiled pages suffice\n"
            "Raw sources checked: not checked - orientation question, compiled pages suffice",
        ),
        "duplicate packet section: Raw sources checked",
    )
    expect_invalid(
        "preamble-text-outside-sections-fails",
        GOOD_STANDARD.replace(
            "WIKI-RESEARCH PACKET\nVerdict: DEEP RESEARCH",
            "WIKI-RESEARCH PACKET\nrogue preamble text the validator would never see\nVerdict: DEEP RESEARCH",
        ),
        "text outside recognized sections",
    )
    expect_invalid(
        "unknown-consulted-page-fails",
        GOOD_STANDARD.replace(
            "Pages consulted: [[index]], [[primer]], [[roof-repair]]",
            "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[ghost-page]]",
        ),
        "pages not in the wiki corpus: ghost-page",
    )


def check_stakes_and_verdicts() -> None:
    expect_invalid(
        "stakes-missing-declaration-fails",
        GOOD_STANDARD.replace("Stakes: standard", "Stakes:"),
        "Stakes must declare standard or high",
    )
    expect_invalid(
        "high-stakes-markers-declared-standard-fails",
        GOOD_STANDARD.replace(
            "Question: /wiki-research what did the roof decision choose?",
            "Question: /wiki-research what did the roof decision choose for insurance purposes?",
        ),
        "Stakes must be high",
    )
    expect_invalid(
        "stakes-marker-dodge-via-consulted-pages-fails",
        GOOD_STANDARD.replace(
            "Pages consulted: [[index]], [[primer]], [[roof-repair]]",
            "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[current-account]]",
        ),
        "Stakes must be high",
    )
    expect_invalid(
        "high-stakes-normal-research-incompatible",
        GOOD_STANDARD.replace("Verdict: DEEP RESEARCH", "Verdict: NORMAL RESEARCH")
        .replace(
            LANE_RESULTS,
            "Lane results: Reviewer completed scope-retention review; helper lanes returned notes only.",
        )
        .replace("Stakes: standard", "Stakes: high (insurance)"),
        "incompatible with Verdict: NORMAL RESEARCH",
    )


def check_claim_ledger() -> None:
    expect_invalid(
        "wiki-backed-claim-without-citation-fails",
        GOOD_STANDARD.replace(
            'C1. The roof decision chose repair over replace | wiki: [[roof-repair]] | quote: "chose repair over full replacement" | status: wiki-backed',
            "C1. The roof decision chose repair over replace | status: wiki-backed",
        ),
        "(wiki-backed) requires a wiki: field",
        "(wiki-backed) requires a quote: field",
    )
    expect_invalid(
        "unknown-status-fails",
        GOOD_STANDARD.replace("| status: wiki-backed", "| status: maybe"),
        "invalid status: maybe",
    )
    expect_invalid(
        "raw-verified-without-raw-fails",
        GOOD_STANDARD.replace("| status: wiki-backed", "| status: raw-verified").replace(
            "Raw coverage: 0 raw-verified / 1 wiki-backed",
            "Raw coverage: 1 raw-verified / 0 wiki-backed",
        ),
        "(raw-verified) requires a raw: field",
    )
    expect_invalid(
        "wiki-backed-with-raw-field-fails",
        GOOD_HIGH.replace("| status: raw-verified", "| status: wiki-backed").replace(
            "Raw coverage: 1 raw-verified / 0 wiki-backed",
            "Raw coverage: 0 raw-verified / 1 wiki-backed",
        ),
        "must not carry a raw: field",
    )
    expect_invalid(
        "inference-unknown-from-id-fails",
        GOOD_STANDARD.replace("| from: C1 |", "| from: C9 |"),
        "references unknown claim C9",
    )
    expect_invalid(
        "duplicate-claim-ids-fail",
        GOOD_STANDARD.replace("C2. Cost drove the choice", "C1. Cost drove the choice"),
        "unique and sequential",
    )
    expect_invalid(
        "multiline-claim-fails",
        GOOD_STANDARD.replace(
            "C2. Cost drove the choice | from: C1 | status: inference",
            "C2. Cost drove the choice | from: C1 | status: inference\nand this continuation line is not allowed",
        ),
        "non-claim line",
    )
    expect_valid(
        "pipe-in-claim-text-passes",
        GOOD_STANDARD.replace(
            "C1. The roof decision chose repair over replace |",
            "C1. The roof decision | repair track chose repair over replace |",
        ),
    )
    expect_invalid(
        "embedded-delimiter-fails-loudly",
        GOOD_STANDARD.replace(
            "C1. The roof decision chose repair over replace |",
            "C1. The roof decision | status: active chose repair over replace |",
        ),
        "duplicate 'status' field",
    )
    expect_invalid(
        "pipe-in-quote-value-fails",
        GOOD_STANDARD.replace(
            'quote: "chose repair over full replacement"',
            'quote: "chose repair , over full replacement" | quote-tail | status: wiki-backed',
        ).replace(" | status: wiki-backed\nC2", "\nC2"),
        "must not contain a pipe character",
    )
    expect_invalid(
        "ledger-wikilink-not-consulted-fails",
        GOOD_STANDARD.replace("| wiki: [[roof-repair]] |", "| wiki: [[kitchen-binder]] |"),
        "C1 cites [[kitchen-binder]] which is not in Pages consulted",
    )
    expect_invalid(
        "inference-without-from-fails",
        GOOD_STANDARD.replace("| from: C1 |", "|"),
        "(inference) requires a from: field",
    )


def check_quotes() -> None:
    expect_invalid(
        "quote-too-long-fails",
        GOOD_STANDARD.replace(
            '"chose repair over full replacement"',
            '"one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen"',
        ),
        "quote exceeds 15 words",
    )
    expect_invalid(
        "fabricated-quote-fails",
        GOOD_STANDARD.replace(
            '"chose repair over full replacement"',
            '"this exact sentence appears nowhere in the corpus"',
        ),
        "not found in the evidentiary body",
    )
    for name, decoy in (
        ("quote-in-frontmatter-fails", "frontmatter decoy phrase alpha"),
        ("quote-in-related-pages-fails", "related decoy phrase beta"),
        ("quote-in-referenced-by-fails", "referenced decoy phrase delta"),
        ("quote-in-code-fence-fails", "codefence decoy phrase gamma"),
    ):
        expect_invalid(
            name,
            GOOD_HIGH.replace('"flood damage is excluded under section 4"', f'"{decoy}"'),
            "not found in the evidentiary body",
        )
    expect_valid(
        "quote-normalization-passes",
        GOOD_HIGH.replace(
            '"flood damage is excluded under section 4"',
            '"FLOOD damage IS   excluded under Section 4"',
        ),
    )


def check_raw_sections() -> None:
    expect_invalid(
        "blank-raw-decision-fails",
        GOOD_STANDARD.replace(
            "Raw sources checked: not checked - orientation question, compiled pages suffice",
            "Raw sources checked:",
        ),
        "must list checked files or state a waiver",
    )
    expect_invalid(
        "bare-none-raw-decision-fails",
        GOOD_STANDARD.replace(
            "Raw sources checked: not checked - orientation question, compiled pages suffice",
            "Raw sources checked: none",
        ),
        "waiver from the",
    )
    expect_invalid(
        "raw-path-without-via-fails",
        GOOD_HIGH.replace(
            "Raw sources checked: raw/records/policy.pdf via pdftotext -layout",
            "Raw sources checked: raw/records/policy.pdf",
        ),
        "extraction method with 'via'",
    )
    too_many = ("; ".join(
        [f"raw/records/r{i:02d}.pdf via pdftotext" for i in range(1, 11)]
        + ["raw/records/policy.pdf via pdftotext"]
    ))
    expect_invalid(
        "too-many-raw-files-fails",
        GOOD_HIGH.replace(
            "Pages consulted: [[index]], [[primer]], [[home-policy]]",
            "Pages consulted: [[index]], [[primer]], [[home-policy]], [[kitchen-binder]]",
        ).replace(
            "Raw sources checked: raw/records/policy.pdf via pdftotext -layout",
            f"Raw sources checked: {too_many}",
        ),
        "no more than 10 raw/ paths",
    )
    expect_invalid(
        "raw-outside-consulted-chain-fails",
        GOOD_HIGH.replace(
            "Raw sources checked: raw/records/policy.pdf via pdftotext -layout",
            "Raw sources checked: raw/records/policy.pdf via pdftotext -layout; "
            "raw/records/kitchen-binder.pdf via pdftotext",
        ),
        "no fully consulted resolution chain",
    )
    expect_invalid(
        "raw-checked-empty-limits-fails",
        GOOD_HIGH.replace(
            "Raw extraction limits: no unreadable regions found in the extracted text",
            "Raw extraction limits:",
        ),
        "Raw extraction limits must be stated",
    )

    multi_path = GOOD_STANDARD.replace(
        "Pages consulted: [[index]], [[primer]], [[roof-repair]]",
        "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[shared-fact]], [[chain-one]]",
    ).replace(
        "Raw sources checked: not checked - orientation question, compiled pages suffice",
        "Raw sources checked: raw/records/shared.pdf via pdftotext -layout",
    ).replace(
        "Raw extraction limits: none - raw was not checked",
        "Raw extraction limits: no unreadable regions found in the extracted text",
    ).replace("waiver: orientation question", "waiver: none")
    expect_valid("multi-path-one-consulted-chain-passes", multi_path)
    expect_invalid(
        "multi-path-no-consulted-chain-fails",
        multi_path.replace(
            "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[shared-fact]], [[chain-one]]",
            "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[shared-fact]]",
        ),
        "no fully consulted resolution chain",
    )


def check_raw_coverage() -> None:
    expect_invalid(
        "coverage-missing-fails",
        GOOD_STANDARD.replace(
            "Raw coverage: 0 raw-verified / 1 wiki-backed / 0 raw-only / 1 inference of 2 claims; waiver: orientation question",
            "Raw coverage:",
        ),
        "Raw coverage must state",
    )
    expect_invalid(
        "coverage-arithmetic-mismatch-fails",
        GOOD_STANDARD.replace(
            "Raw coverage: 0 raw-verified / 1 wiki-backed / 0 raw-only / 1 inference of 2 claims",
            "Raw coverage: 1 raw-verified / 1 wiki-backed / 0 raw-only / 1 inference of 3 claims",
        ),
        "do not match the claim ledger",
    )
    expect_invalid(
        "coverage-waiver-mismatch-fails",
        GOOD_STANDARD.replace("waiver: orientation question", "waiver: none"),
        "must repeat the waiver",
    )
    expect_invalid(
        "coverage-waiver-with-checked-files-fails",
        GOOD_HIGH.replace("waiver: none", "waiver: orientation question"),
        "must be 'none' when raw files were checked",
    )


def check_high_stakes_waivers() -> None:
    expect_valid(
        "high-stakes-true-no-provenance-waiver-passes",
        waiver_packet("free-concept", "the concept stands alone without sources"),
    )
    expect_invalid(
        "high-stakes-orientation-waiver-fails",
        waiver_packet(
            "free-concept",
            "the concept stands alone without sources",
            waiver="orientation question, compiled pages suffice",
            coverage_waiver="orientation question",
        ),
        "accept only the 'no raw provenance exists' waiver",
    )
    expect_invalid(
        "high-stakes-false-waiver-direct-provenance-fails",
        waiver_packet("home-policy", "flood damage is excluded under section 4"),
        "waiver is false",
    )
    expect_invalid(
        "high-stakes-false-waiver-slug-chain-fails",
        waiver_packet("laundered-concept", "restates the exclusion from the policy source page"),
        "waiver is false",
    )
    expect_invalid(
        "high-stakes-false-waiver-authority-ref-fails",
        waiver_packet("authority-raw", "carries raw provenance only through authority_ref"),
        "waiver is false",
    )
    expect_invalid(
        "provenance-cycle-terminates-and-fails-waiver",
        waiver_packet("cycle-a", "cycle fixture page a"),
        "waiver is false",
    )
    expect_invalid(
        "traversal-raw-path-in-packet-fails",
        GOOD_HIGH.replace(
            "Raw sources checked: raw/records/policy.pdf via pdftotext -layout",
            "Raw sources checked: raw/../wiki/sources/fake-raw.md via pdftotext -layout",
        ).replace(
            "raw: [policy.pdf p.12](raw/records/policy.pdf)",
            "raw: raw/../wiki/sources/fake-raw.md",
        ),
        "must stay inside raw/",
    )
    expect_invalid(
        "traversal-provenance-page-fails-closed",
        waiver_packet("traversal-provenance", "names a traversal raw path in provenance"),
        "dangling provenance reference",
        "unsafe raw path",
    )
    expect_invalid(
        "symlink-escape-provenance-fails-closed",
        waiver_packet("escape-provenance", "cites a symlink that escapes the raw tree"),
        "dangling provenance reference",
        "unsafe raw path",
    )
    expect_invalid(
        "dangling-sources-slug-fails-closed",
        waiver_packet("dangling-source", "cites a source page that does not exist"),
        "dangling provenance reference",
        "matches no wiki/sources/ page",
    )
    expect_invalid(
        "dangling-authority-ref-fails-closed",
        waiver_packet("dangling-authority", "names an authority file that does not exist"),
        "dangling provenance reference",
        "wiki/sources/missing.md",
    )


def check_high_stakes_eligibility() -> None:
    expect_invalid(
        "high-stakes-wiki-backed-provenance-page-fails",
        GOOD_HIGH.replace(
            'C1. The policy excludes flood damage | wiki: [[home-policy]] | raw: [policy.pdf p.12](raw/records/policy.pdf) | quote: "flood damage is excluded under section 4" | status: raw-verified',
            'C1. The policy excludes flood damage | wiki: [[home-policy]] | quote: "flood damage is excluded under section 4" | status: wiki-backed',
        ).replace(
            "Raw coverage: 1 raw-verified / 0 wiki-backed",
            "Raw coverage: 0 raw-verified / 1 wiki-backed",
        ),
        "has raw provenance in its closure",
    )
    expect_valid(
        "high-stakes-decision-page-passes",
        waiver_packet("roof-repair", "chose repair over full replacement"),
    )
    expect_valid(
        "high-stakes-owner-registered-page-passes",
        waiver_packet(
            "protocol",
            "records the regimen as owner-verified truth",
            extra_pages=", [[contradictions]]",
            question_tail="for a medical check",
            contradictions="checked [[contradictions]]; no relevant conflicts for this question",
        ),
    )
    expect_invalid(
        "registered-analysis-page-still-fails",
        waiver_packet(
            "cost-summary",
            "restates the compiled totals for planning",
            extra_pages=", [[contradictions]]",
            contradictions="checked [[contradictions]]; no relevant conflicts for this question",
        ),
        "type: analysis page, excluded before both eligibility branches",
    )
    expect_invalid(
        "mixed-qualifying-and-nonqualifying-citations-fail",
        waiver_packet(
            "free-concept",
            "the concept stands alone without sources",
            extra_pages=", [[casual-person]]",
            claim_extra=", [[casual-person]]",
        ),
        "neither wiki-native nor owner-registered",
    )
    inference_chain = GOOD_HIGH.replace(
        'C1. The policy excludes flood damage | wiki: [[home-policy]] | raw: [policy.pdf p.12](raw/records/policy.pdf) | quote: "flood damage is excluded under section 4" | status: raw-verified',
        'C1. The policy excludes flood damage | wiki: [[home-policy]] | quote: "flood damage is excluded under section 4" | status: wiki-backed\n'
        "C2. The exclusion narrows coverage | from: C1 | status: inference\n"
        "C3. The narrowed coverage matters here | from: C2 | status: inference",
    ).replace(
        "Raw coverage: 1 raw-verified / 0 wiki-backed / 0 raw-only / 0 inference of 1 claims; waiver: none",
        "Raw coverage: 0 raw-verified / 1 wiki-backed / 0 raw-only / 2 inference of 3 claims; waiver: none",
    ).replace(
        "Answer: The policy excludes flood damage [C1].",
        "Answer: The narrowed coverage matters here [C3].",
    )
    expect_invalid(
        "multi-hop-inference-launders-ineligibility-fails",
        inference_chain,
        "inherits ineligibility",
    )


def check_answer_rules() -> None:
    expect_invalid(
        "unanchored-paragraph-fails",
        GOOD_STANDARD.replace(
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].\n"
            "\n"
            "This extra paragraph has no anchor at all.",
        ),
        "must reference at least one ledger claim ID",
    )
    expect_invalid(
        "wikilink-only-anchor-fails",
        GOOD_STANDARD.replace(
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
            "Answer: The roof decision chose repair over full replacement [C1].\n\nSee [[roof-repair]] for the reasoning.",
        ),
        "must reference at least one ledger claim ID",
    )
    for name, line in (
        ("heading-in-answer-fails", "# Summary heading"),
        ("blockquote-in-answer-fails", "> quoted conclusion"),
        ("html-in-answer-fails", "<div>markup</div>"),
    ):
        expect_invalid(
            name,
            GOOD_STANDARD.replace(
                "Answer: The roof decision chose repair over full replacement [C1].",
                f"Answer: The roof decision chose repair over full replacement [C1].\n{line}",
            ),
            "heading, blockquote, or HTML lines",
        )
    expect_invalid(
        "unanchored-list-item-fails",
        GOOD_STANDARD.replace(
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
            "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].\n"
            "- an unanchored bullet",
        ),
        "must reference at least one ledger claim ID",
    )
    table_answer = GOOD_STANDARD.replace(
        "Answer: The roof decision chose repair over full replacement [C1]. Cost likely drove the choice [C2].",
        "Answer: summary table below [C1]\n"
        "| Outcome [C1] | Basis [C2] |\n"
        "| --- | --- |\n"
        "| chose repair [C1] | decision page [C2] |",
    )
    expect_valid("anchored-table-with-separator-passes", table_answer)
    expect_invalid(
        "unanchored-table-header-fails",
        table_answer.replace("| Outcome [C1] | Basis [C2] |", "| Outcome | Basis |"),
        "must reference at least one ledger claim ID",
    )
    expect_invalid(
        "answer-unknown-claim-id-fails",
        GOOD_STANDARD.replace("[C2].", "[C2]. It also follows [C9]."),
        "Answer references unknown claim C9",
    )
    expect_valid(
        "answer-raw-path-listed-passes",
        GOOD_HIGH.replace(
            "Answer: The policy excludes flood damage [C1].",
            "Answer: The policy excludes flood damage [C1] (raw/records/policy.pdf).",
        ),
    )
    expect_invalid(
        "answer-raw-path-unlisted-fails",
        GOOD_HIGH.replace(
            "Answer: The policy excludes flood damage [C1].",
            "Answer: The policy excludes flood damage [C1] (raw/records/cycle.pdf).",
        ),
        "not listed in Raw sources checked",
    )
    expect_invalid(
        "self-disclaimed-citation-support-fails",
        GOOD_STANDARD.replace(
            "Cost likely drove the choice [C2].",
            "Cost likely drove the choice [C2], but the citation may not support every claim.",
        ),
        "must not disclaim or weaken its own citation support",
    )


def check_raw_only_rules() -> None:
    raw_only_base = GOOD_HIGH.replace(
        "Contradictions or stale areas:",
        "C2. The policy file shows an unrecorded rider | raw: raw/records/policy.pdf | status: raw-only\n"
        "Contradictions or stale areas:",
    ).replace(
        "Raw coverage: 1 raw-verified / 0 wiki-backed / 0 raw-only / 0 inference of 1 claims; waiver: none",
        "Raw coverage: 1 raw-verified / 0 wiki-backed / 1 raw-only / 0 inference of 2 claims; waiver: none",
    ).replace(
        "Raw-only findings: none - no raw-only findings",
        "Raw-only findings: C2: the policy file shows an unrecorded rider; recommend re-ingest and update source page.",
    )
    expect_valid("raw-only-finding-with-recommendation-passes", raw_only_base)
    expect_invalid(
        "raw-only-claim-in-answer-fails",
        raw_only_base.replace(
            "Answer: The policy excludes flood damage [C1].",
            "Answer: The policy excludes flood damage [C1] and the rider matters [C2].",
        ),
        "must not reference raw-only claim C2",
    )
    expect_invalid(
        "raw-only-not-reflected-in-findings-fails",
        raw_only_base.replace(
            "Raw-only findings: C2: the policy file shows an unrecorded rider; recommend re-ingest and update source page.",
            "Raw-only findings: none - no raw-only findings",
        ),
        "must be reflected in Raw-only findings",
    )
    expect_invalid(
        "raw-only-without-recommendation-fails",
        raw_only_base.replace(
            "recommend re-ingest and update source page.",
            "noted for later.",
        ),
        "Raw-only findings must recommend",
    )
    expect_invalid(
        "raw-only-with-durable-filing-fails",
        raw_only_base.replace(
            "Durable-write status: chat-only; no durable write",
            "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture; "
            "approval record in scripts/capture-runs.jsonl; validate_capture_runs.py passed; "
            "primary home wiki/analyses/example.md",
        ),
        "must not claim an analysis was filed",
    )
    expect_invalid(
        "raw-only-quote-forbidden-fails",
        raw_only_base.replace(
            "C2. The policy file shows an unrecorded rider | raw: raw/records/policy.pdf | status: raw-only",
            'C2. The policy file shows an unrecorded rider | raw: raw/records/policy.pdf | quote: "wind damage is covered in full" | status: raw-only',
        ),
        "must not carry a quote",
    )


def check_contradiction_rules() -> None:
    sensitive = GOOD_STANDARD.replace(
        "Question: /wiki-research what did the roof decision choose?",
        "Question: /wiki-research what are the current account priorities?",
    ).replace("Stakes: standard", "Stakes: high (property)")
    expect_invalid(
        "contradiction-sensitive-requires-register",
        sensitive,
        "must consult [[contradictions]]",
    )
    expect_invalid(
        "contradiction-register-smoothing-fails",
        sensitive.replace(
            "Pages consulted: [[index]], [[primer]], [[roof-repair]]",
            "Pages consulted: [[index]], [[primer]], [[roof-repair]], [[contradictions]]",
        ).replace(
            "Contradictions or stale areas: no relevant conflicts for this narrow decision question",
            "Contradictions or stale areas: none found",
        ),
        "must cite [[contradictions]]",
        "must not dismiss",
    )


def check_durable_rules() -> None:
    expect_invalid(
        "durable-bypass-claim-fails",
        GOOD_STANDARD.replace(
            "Durable-write status: chat-only; no durable write",
            "Durable-write status: filed analysis by direct write",
        ),
        "analysis-capture",
    )
    expect_invalid(
        "durable-route-without-proof-fails",
        GOOD_STANDARD.replace(
            "Durable-write status: chat-only; no durable write",
            "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture",
        ),
        "approval record",
        "validate_capture_runs.py",
        "primary destination",
    )
    expect_valid(
        "durable-proof-packet-passes",
        GOOD_STANDARD.replace(
            "Durable-write status: chat-only; no durable write",
            "Durable-write status: filed analysis through workflows/research/CONTEXT.md#analysis-capture; "
            "approval record in scripts/capture-runs.jsonl; validate_capture_runs.py passed; "
            "primary home wiki/analyses/example.md",
        ),
    )


def check_docs_contract() -> None:
    root_text = ROOT_CONTEXT.read_text(encoding="utf-8")
    research_text = RESEARCH_CONTEXT.read_text(encoding="utf-8")
    workflow_text = RESEARCH_WORKFLOW.read_text(encoding="utf-8")
    claude_text = CLAUDE_WRAPPER.read_text(encoding="utf-8")
    codex_text = CODEX_WRAPPER.read_text(encoding="utf-8")
    workflow_lower = workflow_text.lower()

    results.record(
        "normal-research-no-whole-workflow-claim",
        "this `CONTEXT.md` is the whole workflow" not in research_text.lower()
        and "Single task." not in research_text,
        "research context still claims to be the whole workflow",
    )
    results.record(
        "research-doc-uses-runtime-trigger-boundary",
        "scripts/wiki_research.py preflight" in workflow_text
        and "scripts/wiki_research.py manifest" in workflow_text
        and "scripts/wiki_research.py validate-packet" in workflow_text
        and "explicit trigger phrases above" not in workflow_text,
        "research workflow must point at runtime-owned trigger boundary",
    )
    results.record(
        "research-doc-pins-raw-default",
        "raw confirmation is the default" in workflow_lower,
        "research workflow must pin the raw-confirmation default",
    )
    results.record(
        "route-doc-does-not-copy-trigger-list",
        '"/wiki-research", or "deep research the wiki"' not in root_text
        and "scripts/wiki_research.py preflight" in root_text,
        "root CONTEXT.md should route by runtime boundary, not copied trigger list",
    )
    results.record(
        "research-read-only-rule-not-softened",
        "read-only by default" not in workflow_text
        and "Split lanes are read-only." in workflow_text,
        "split lanes rule is softened or absent",
    )
    results.record(
        "research-doc-delegates-lane-manifest",
        "Run every lane in `python3 scripts/wiki_research.py manifest`" in workflow_text
        and "**Planner:**" not in workflow_text
        and "**Page Scout:**" not in workflow_text
        and "**Evidence Extractor:**" not in workflow_text,
        "research workflow should not duplicate the runtime lane manifest",
    )
    results.record(
        "research-doc-preserves-scope-caveats-generally",
        "## Scope Retention" in workflow_text
        and "For any wiki-research question" in workflow_text
        and "runtime-owned scope-retention dimensions" in workflow_text
        and "runtime-owned page relevance tags" in workflow_text
        and "runtime-owned output targets" in workflow_text
        and "Reviewer should check that no material caveat from a consulted page was silently dropped" in workflow_text
        and "Raw verification must not narrow the compiled-page scope" in workflow_text,
        "research workflow must preserve material caveats for every query",
    )
    results.record(
        "research-doc-states-judgment-obligations",
        "citation-auditor" in workflow_lower
        and "owns the fact" in workflow_lower
        and "smuggled" in workflow_lower,
        "research workflow must state the citation-auditor and reviewer judgment obligations",
    )
    results.record(
        "research-doc-does-not-duplicate-runtime-vocabularies",
        "raw-verified, wiki-backed" not in workflow_lower
        and "orientation question" not in workflow_lower
        and "user waived raw confirmation" not in workflow_lower
        and "legal, medical, financial" not in workflow_lower
        and "decision, goal, learning" not in workflow_lower
        and "wiki, raw, from, status, quote" not in workflow_lower
        and "material caveats, status qualifiers, exclusions" not in workflow_lower
        and "project timeline, operating state, condition caveat" not in workflow_lower,
        "research workflow should defer vocabularies to scripts/wiki_research.py manifest",
    )
    forbidden_script_duplications = (
        "scripts/capture_gate.py",
        "scripts/validate_capture_runs.py",
        "scripts/rebuild_referenced_by.py",
        "scripts/lint.py --tier1",
    )
    results.record(
        "research-doc-does-not-duplicate-analysis-capture-script-list",
        all(marker not in workflow_text for marker in forbidden_script_duplications)
        and "## Analysis Capture" in research_text
        and "workflows/research/CONTEXT.md#analysis-capture" in workflow_text,
        "research workflow duplicates normal research analysis-capture mechanics",
    )
    for label, text in (("claude", claude_text), ("codex", codex_text)):
        results.record(
            f"{label}-research-wrapper-routes-through-root",
            "AGENTS.md" in text
            and "CONTEXT.md" in text
            and "workflows/research/wiki-research.md" not in text
            and "wiki-swarm" not in text,
            f"{label} wrapper should stay a thin root-router pointer",
        )


check_preflight()
check_manifest()
check_packet_shape()
check_stakes_and_verdicts()
check_claim_ledger()
check_quotes()
check_raw_sections()
check_raw_coverage()
check_high_stakes_waivers()
check_high_stakes_eligibility()
check_answer_rules()
check_raw_only_rules()
check_contradiction_rules()
check_durable_rules()
check_docs_contract()

sys.exit(results.finish())
