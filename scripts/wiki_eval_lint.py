#!/usr/bin/env python3
"""Regression eval for lint.py.

Guards lint's checks against going vacuous: every generic Tier-1 check
(filename, folder structure incl. root/wiki file and directory branches,
entity folder, frontmatter presence and keys, type/folder, confidence,
source-type, dates, raw/ and bare-slug source refs, dangling links including
code-span exemptions, related labels, confidence restate, index coverage,
adjudication integrity, raw-buckets integrity, meta-page dangling links, and
stray tool-call tag artifacts including the in-prose negative) gets a seeded
violation that must fire, and the Tier-2 candidate and
adjudication/suppression machinery gets positive and negative cases. A check
that cannot fail is indistinguishable from no check; this suite exists so a
future lint edit cannot silently disarm one.

Runs against the fixture mini-wiki in scripts/fixtures/wiki-lint/, copied to
a system temp directory per case. Writes nothing inside the repo.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LINT = REPO_ROOT / "scripts" / "lint.py"
FIXTURE = REPO_ROOT / "scripts" / "fixtures" / "wiki-lint"

results = []


def copy_fixture(root):
    """Materialize the fixture mini-wiki (wiki/ + scripts/) under `root`."""
    shutil.copytree(FIXTURE / "wiki", root / "wiki")
    shutil.copytree(FIXTURE / "scripts", root / "scripts")


def run_case(name, mutate, args=("--tier1",), expect_code=0, expect=(), absent=()):
    """Copy the fixture, apply `mutate(root)`, run lint, assert on output."""
    with tempfile.TemporaryDirectory(prefix="wiki-lint-eval-") as td:
        root = Path(td)
        copy_fixture(root)
        if mutate:
            mutate(root)
        proc = subprocess.run(
            [sys.executable, str(LINT), *args],
            cwd=root, text=True, capture_output=True,
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
            for marker in expect:
                if marker not in proc.stdout:
                    print(f"  missing: {marker!r}")
            for marker in absent:
                if marker in proc.stdout:
                    print(f"  unexpected: {marker!r}")
        else:
            print(f"PASS {name}")


def append(root, rel, text):
    p = root / rel
    p.write_text(p.read_text() + text)


def edit(root, rel, old, new):
    p = root / rel
    t = p.read_text()
    assert old in t, f"fixture drift: {old!r} not in {rel}"
    p.write_text(t.replace(old, new, 1))


def write_adjudications(root, **kwargs):
    base = {"accepted_orphans": [], "hub_pages": [], "skipped_crossref_pairs": [],
            "reviewed_confidence_low": [], "reviewed_near_duplicates": [],
            "reviewed_quotes": []}
    base.update(kwargs)
    (root / "scripts" / "lint-adjudications.json").write_text(json.dumps(base))


def write_raw_buckets(root, buckets):
    (root / "scripts" / "raw-buckets.json").write_text(json.dumps({"buckets": buckets}))


# ---- Tier 1: clean fixture is the control ----
run_case("clean-fixture-passes", None)

# ---- Tier 1: each check fires on a seeded violation ----
run_case(
    "filename-nonkebab-fires",
    lambda r: shutil.copy(r / "wiki/concepts/alpha.md", r / "wiki/concepts/Bad_Name.md"),
    expect_code=1, expect=("filename", "not kebab-case"),
)
run_case(
    "filename-date-prefix-fires",
    lambda r: shutil.copy(r / "wiki/concepts/alpha.md", r / "wiki/concepts/2026-06-01-alpha.md"),
    expect_code=1, expect=("filename", "has date prefix"),
)
run_case(
    "missing-frontmatter-key-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "tags: [fixture]\n", ""),
    expect_code=1, expect=("frontmatter", "missing keys: tags"),
)
run_case(
    "type-folder-mismatch-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "type: concept", "type: source"),
    expect_code=1, expect=("type", "folder type 'concept'"),
)
run_case(
    "invalid-confidence-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "confidence: medium", "confidence: certain"),
    expect_code=1, expect=("confidence", "invalid value 'certain'"),
)
run_case(
    "malformed-date-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "created: 2026-06-01", "created: 2026/06/01"),
    expect_code=1, expect=("date", "created '2026/06/01'"),
)
run_case(
    "invalid-source-type-fires",
    lambda r: edit(r, "wiki/sources/gamma.md", "source_type: other", "source_type: memo"),
    expect_code=1, expect=("source-type", "invalid value 'memo'"),
)
run_case(
    "source-type-on-non-source-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "agent_use_cases:", "source_type: other\nagent_use_cases:"),
    expect_code=1, expect=("source-type", "source_type set on non-source page"),
)
run_case(
    "index-missing-fires",
    lambda r: edit(r, "wiki/index.md", "| [alpha.md](concepts/alpha.md) | Test concept alpha |\n", ""),
    expect_code=1, expect=("index-missing", "concepts/alpha.md"),
)
run_case(
    "index-stale-fires",
    lambda r: append(r, "wiki/index.md", "| [missing.md](concepts/missing.md) | stale fixture |\n"),
    expect_code=1, expect=("index-stale", "concepts/missing.md"),
)
run_case(
    "related-label-fires",
    lambda r: append(r, "wiki/concepts/alpha.md", "- Causes: [[delta-one]]\n"),
    expect_code=1, expect=("related-label", "'Causes:'"),
)
run_case(
    "confidence-restate-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md", "confidence: medium", "confidence: low"),
    expect_code=1, expect=("confidence-restate", "not restated in body"),
)
run_case(
    "confidence-restate-satisfied",
    lambda r: (
        edit(r, "wiki/concepts/alpha.md", "confidence: medium", "confidence: low"),
        edit(r, "wiki/concepts/alpha.md", "Alpha body text",
             "Confidence is low; fixture restatement. Alpha body text"),
    ),
)
run_case(
    "contested-needs-disagreement",
    lambda r: (
        edit(r, "wiki/concepts/alpha.md", "confidence: medium", "confidence: contested"),
        edit(r, "wiki/concepts/alpha.md", "Alpha body text",
             "Confidence is contested. Alpha body text"),
    ),
    expect_code=1, expect=("confidence-restate", "Disagreement"),
)
run_case(
    "dangling-link-fires",
    lambda r: append(r, "wiki/concepts/alpha.md", "- [[no-such-page]]\n"),
    expect_code=1, expect=("dangling-link",),
)
run_case(
    "in-code-span-link-not-dangling",
    lambda r: append(r, "wiki/concepts/alpha.md",
                     "\nLink syntax example: `[[some-undefined-demo-page]]`.\n"),
    expect_code=0, absent=("some-undefined-demo-page",),
)
run_case(
    "raw-token-in-title-not-source-ref",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   'title: "Alpha"',
                   'title: "How to use raw/data pipelines"'),
    expect_code=0, absent=("source-ref",),
)
run_case(
    "related-label-prose-bullet-allowed",
    lambda r: append(r, "wiki/concepts/alpha.md", "- Background: context, no link\n"),
    expect_code=0, absent=("related-label",),
)
run_case(
    "related-label-with-link-still-fires",
    lambda r: append(r, "wiki/concepts/alpha.md", "- Causes: [[delta-one]] context\n"),
    expect_code=1, expect=("related-label", "'Causes:'"),
)
run_case(
    "bare-slug-source-ref-typo-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   'sources: ["experience: lint eval fixture"]',
                   'sources: [gamma-typo-not-a-real-source]'),
    expect_code=1, expect=("source-ref", "matches no wiki/sources/ page"),
)
run_case(
    "bare-slug-source-ref-resolves-passes",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   'sources: ["experience: lint eval fixture"]',
                   'sources: [gamma]'),
    expect_code=0, absent=("source-ref",),
)
run_case(
    "adjudication-stale-fires",
    lambda r: write_adjudications(r, accepted_orphans=[
        {"page": "sources/renamed-away.md", "reason": "x", "date": "2026-06-11"}]),
    expect_code=1, expect=("adjudication-stale", "renamed-away"),
)
run_case(
    "adjudication-stale-fires-reviewed-quotes",
    lambda r: write_adjudications(r, reviewed_quotes=[
        {"page": "concepts/renamed-quote-page.md", "quote": "x", "reason": "y",
         "date": "2026-06-11"}]),
    expect_code=1, expect=("adjudication-stale", "renamed-quote-page"),
)
run_case(
    "non-utf8-page-fails-cleanly",
    lambda r: (r / "wiki/concepts/alpha.md").write_bytes(b"---\ntitle: x\n---\n\xff\xfe"),
    expect_code=1, expect=("encoding", "not valid UTF-8"),
)
run_case(
    "malformed-adjudication-json-fails-cleanly",
    lambda r: (r / "scripts/lint-adjudications.json").write_text("{not json"),
    expect_code=1, expect=("adjudication-file", "unreadable JSON"),
)
run_case(
    "misshapen-adjudication-entry-fails-cleanly",
    lambda r: (r / "scripts/lint-adjudications.json").write_text(
        '{"accepted_orphans": [{"reason": "no page key"}]}'),
    expect_code=1, expect=("adjudication-file", "string 'page'"),
)
run_case(
    "duplicate-stem-fires",
    lambda r: (
        shutil.copy(r / "wiki/concepts/delta-three.md", r / "wiki/sources/delta-three.md"),
        edit(r, "wiki/sources/delta-three.md", "type: concept", "type: source\nsource_type: other"),
        append(r, "wiki/index.md", "| [delta-three.md](sources/delta-three.md) | dup stem |\n"),
    ),
    expect_code=1, expect=("duplicate-stem",),
)
run_case(
    "missing-raw-source-ref-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   'sources: ["experience: lint eval fixture"]',
                   'sources: [raw/notes/does-not-exist.md]'),
    expect_code=1, expect=("source-ref", "does-not-exist"),
)
run_case(
    "resolving-raw-source-ref-passes",
    lambda r: (
        (r / "raw" / "notes").mkdir(parents=True),
        write_raw_buckets(r, {"notes": "fixture notes"}),
        (r / "raw" / "notes" / "real.md").write_text("raw fixture"),
        edit(r, "wiki/concepts/alpha.md",
             'sources: ["experience: lint eval fixture"]',
             'sources: [raw/notes/real.md]'),
    ),
)
run_case(
    "unexpected-root-file-fires",
    lambda r: (r / "loose.txt").write_text("loose root file"),
    expect_code=1, expect=("repo-structure", "unexpected top-level file"),
)
run_case(
    "unexpected-root-dir-fires",
    lambda r: (r / "notabucket").mkdir(),
    expect_code=1, expect=("repo-structure", "unexpected top-level directory"),
)
run_case(
    "unexpected-wiki-folder-fires",
    lambda r: (r / "wiki" / "misc").mkdir(),
    expect_code=1, expect=("wiki-structure", "unexpected wiki/ folder"),
)
run_case(
    "stray-wiki-root-file-fires",
    lambda r: (r / "wiki" / "notes.txt").write_text("stray wiki root file"),
    expect_code=1, expect=("wiki-structure", "unexpected wiki/ root file"),
)
run_case(
    "unknown-entity-folder-fires",
    lambda r: (
        (r / "wiki" / "misc").mkdir(),
        shutil.copy(r / "wiki/concepts/alpha.md", r / "wiki/misc/alpha.md"),
    ),
    expect_code=1, expect=("entity-folder", "unknown folder 'misc'"),
)
run_case(
    "body-only-page-fires",
    lambda r: (r / "wiki/concepts/alpha.md").write_text("Just a body, no frontmatter.\n"),
    expect_code=1, expect=("frontmatter", "missing or malformed"),
)
run_case(
    "loose-raw-file-fires",
    lambda r: (
        (r / "raw").mkdir(),
        (r / "raw" / "source.pdf").write_text("loose source artifact"),
    ),
    expect_code=1, expect=("raw-structure", "loose raw/ file"),
)
run_case(
    "unknown-raw-bucket-fires",
    lambda r: (
        (r / "raw" / "misc").mkdir(parents=True),
        write_raw_buckets(r, {"notes": "fixture notes"}),
    ),
    expect_code=1, expect=("raw-structure", "missing from scripts/raw-buckets.json"),
)
run_case(
    "missing-raw-buckets-file-fires",
    lambda r: (r / "raw" / "notes").mkdir(parents=True),
    expect_code=1, expect=("raw-buckets", "raw bucket taxonomy file is missing"),
)
run_case(
    "corrupt-raw-buckets-fires",
    lambda r: (
        (r / "raw" / "notes").mkdir(parents=True),
        (r / "raw" / "notes" / ".gitkeep").write_text(""),
        (r / "scripts" / "raw-buckets.json").write_text("{not valid json"),
    ),
    expect_code=1, expect=("raw-buckets", "unreadable JSON"),
)
run_case(
    "wrong-shape-raw-buckets-fires",
    lambda r: (
        (r / "raw" / "notes").mkdir(parents=True),
        (r / "raw" / "notes" / ".gitkeep").write_text(""),
        (r / "scripts" / "raw-buckets.json").write_text('{"buckets": ["notes"]}'),
    ),
    expect_code=1, expect=("raw-buckets", "must contain a 'buckets' object"),
)
run_case(
    "raw-folder-nonkebab-fires",
    lambda r: (r / "raw" / "BadBucket").mkdir(parents=True),
    expect_code=1, expect=("raw-structure", "raw/ folder is not kebab-case"),
)
run_case(
    "markdown-md-link-fires",
    lambda r: append(r, "wiki/index.md", "[Missing](missing.md)\n"),
    expect_code=1, expect=("markdown-link", "missing.md"),
)
run_case(
    "meta-dangling-link-fires",
    lambda r: append(r, "wiki/index.md", "[[no-such-meta-target]]\n"),
    expect_code=1, expect=("meta-dangling-link", "no-such-meta-target"),
)
run_case(
    "empty-agent-use-cases-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   "agent_use_cases:\n  - lint eval fixture",
                   "agent_use_cases:"),
    expect_code=1, expect=("frontmatter", "agent_use_cases has no list items"),
)
run_case(
    "bad-review-by-date-fires",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   "confidence: medium",
                   "confidence: medium\nreview_by: 2026-13-99"),
    expect_code=1, expect=("date", "not a real calendar date"),
)
run_case(
    "loose-deliverable-fires",
    lambda r: (
        (r / "deliverables").mkdir(),
        (r / "deliverables" / "model.xlsx").write_text("loose deliverable"),
    ),
    expect_code=1, expect=("deliverables-structure", "loose deliverable"),
)
run_case(
    "deliverables-folder-nonkebab-fires",
    lambda r: (r / "deliverables" / "Bad Folder").mkdir(parents=True),
    expect_code=1, expect=("deliverables-structure", "deliverables/ subfolder is not kebab-case"),
)
run_case(
    "finder-metadata-fires",
    lambda r: (r / "wiki" / ".DS_Store").write_text("metadata"),
    expect_code=1, expect=("os-metadata", ".DS_Store"),
)
run_case(
    "stray-content-tag-fires",
    lambda r: append(r, "wiki/concepts/alpha.md", "\n</content>\n"),
    expect_code=1, expect=("stray-tag", "</content>"),
)
run_case(
    "stray-parameter-tag-fires",
    lambda r: append(r, "wiki/concepts/alpha.md", '\n<parameter name="content">x\n'),
    expect_code=1, expect=("stray-tag", "<parameter"),
)
run_case(
    "stray-tag-in-prose-does-not-fire",
    lambda r: append(r, "wiki/concepts/alpha.md",
                     "\nThe maintenance sweep removed two stray </content> "
                     "ingestion artifacts from the corpus.\n"),
    expect_code=0, absent=("stray-tag",),
)

# ---- Tier 2: quote mismatches (evidence check, deterministic half) ----
FIXTURE_QUOTE = "The gamma fixture contains this exact sentence for verbatim quoting."


def seed_quote(root):
    edit(root, "wiki/concepts/beta.md",
         "Beta body text for the lint eval fixture.",
         f'Beta body text for the lint eval fixture. '
         f'"{FIXTURE_QUOTE}" (source: [[gamma]])')


run_case(
    "quote-mismatch-fires",
    seed_quote,
    args=(), expect=("quote mismatch", "not found in cited source"),
)
run_case(
    "quote-verbatim-passes",
    lambda r: (
        edit(r, "wiki/sources/gamma.md",
             "Gamma is an orphan source page.",
             f"Gamma is an orphan source page. {FIXTURE_QUOTE}"),
        seed_quote(r),
    ),
    args=(), absent=("not found in cited source",),
)
run_case(
    "quote-mismatch-suppressed",
    lambda r: (
        seed_quote(r),
        write_adjudications(r, reviewed_quotes=[
            {"page": "concepts/beta.md", "quote": FIXTURE_QUOTE,
             "reason": "fixture", "date": "2026-06-11"}]),
    ),
    args=(), expect=("suppressed",), absent=("not found in cited source",),
)

# ---- Tier 2: candidates and suppression ----
run_case(
    "orphan-and-crossref-surface",
    None, args=(),
    expect=("sources/gamma.md",
            "concepts/alpha.md  +  concepts/beta.md"),
)
run_case(
    "orphan-suppressed-by-adjudication",
    lambda r: write_adjudications(r, accepted_orphans=[
        {"page": "sources/gamma.md", "reason": "fixture", "date": "2026-06-11"}]),
    # the bare line is the orphan listing; the thin-pages listing has a "(Nw)" suffix
    args=(), expect=("suppressed",), absent=("      sources/gamma.md\n",),
)
run_case(
    "crossref-pair-suppressed",
    lambda r: write_adjudications(r, skipped_crossref_pairs=[
        {"pair": ["concepts/alpha.md", "concepts/beta.md"], "reason": "fixture", "date": "2026-06-11"}]),
    args=(), absent=("concepts/alpha.md  +  concepts/beta.md",),
)
run_case(
    "hub-page-suppresses-pairs",
    lambda r: write_adjudications(r, hub_pages=[
        {"page": "concepts/alpha.md", "reason": "fixture", "date": "2026-06-11"}]),
    args=(), absent=("concepts/alpha.md  +  concepts/beta.md",),
)
run_case(
    "missing-adjudication-file-degrades-gracefully",
    lambda r: (r / "scripts" / "lint-adjudications.json").unlink(),
    args=(), expect=("sources/gamma.md",),
)
run_case(
    "low-overlap-pair-not-reported",
    # diluting alpha's link profile with meta-page links drops Jaccard below 0.5
    lambda r: append(r, "wiki/concepts/alpha.md",
                     "- [[log]]\n- [[glossary]]\n- [[overview]]\n- [[primer]]\n"),
    args=(), absent=("concepts/alpha.md  +  concepts/beta.md",),
)

# ---- Tier 2: positive cases for generic categories ----
NEAR_DUP_BODY = (
    "Market positioning strategy across multiple customer segments requires "
    "balancing product capabilities against buyer urgency, competitive pressure, "
    "implementation risk, pricing thresholds, deployment dependencies, support "
    "load, expansion potential, and the exact evidence available from current "
    "source material before making durable claims in the wiki."
)
run_case(
    "near-duplicate-pair-surfaces",
    lambda r: (
        edit(r, "wiki/concepts/delta-one.md", "Delta one body.", NEAR_DUP_BODY),
        edit(r, "wiki/concepts/delta-two.md", "Delta two body.", NEAR_DUP_BODY),
    ),
    args=(), expect=("concepts/delta-one.md", "concepts/delta-two.md", "jaccard"),
)
run_case(
    "confidence-upgrade-surfaces",
    lambda r: (
        edit(r, "wiki/concepts/delta-one.md", "confidence: medium", "confidence: low"),
        edit(r, "wiki/concepts/delta-one.md", "Delta one body.",
             "Delta one body. Confidence is low here for the fixture."),
    ),
    args=(), expect=("confidence:low with >=2 inbound", "concepts/delta-one.md"),
)
run_case(
    "missing-open-questions-surfaces",
    lambda r: edit(r, "wiki/concepts/alpha.md",
                   "## Open questions / gaps", "## Notes"),
    args=(), expect=("non-source pages missing Open questions", "concepts/alpha.md"),
)

DECISION_BODY = (
    "This fixture decision exists to exercise the review_by enrollment signal. "
    "It carries a deliberately dense body so it clears the thin-page threshold "
    "and its only appearance in lint output comes from the enrollment check "
    "rather than the orphan or thin listings. The decision describes a dated "
    "choice whose realized outcome should eventually be graded against what "
    "actually happened instead of standing on self-assessed confidence forever, "
    "which is exactly the population the outcome-review loop is meant to enroll."
)


def seed_decision_without_review_by(root):
    (root / "wiki" / "decisions").mkdir()
    (root / "wiki" / "decisions" / "template-decision.md").write_text(
        '---\ntitle: "Template Decision"\ntype: decision\ncreated: 2026-06-01\n'
        'updated: 2026-06-01\nsources: ["experience: lint eval fixture"]\n'
        'tags: [fixture]\nconfidence: medium\nagent_use_cases:\n'
        '  - lint eval fixture\n---\n\n'
        f'{DECISION_BODY}\n\n'
        '## Open questions / gaps\n\n- Fixture page; no real questions.\n'
    )
    append(root, "wiki/index.md",
           "| [template-decision.md](decisions/template-decision.md) | fixture decision |\n")
    append(root, "wiki/concepts/alpha.md", "- Related: [[template-decision]]\n")


run_case(
    "review-by-missing-fires",
    seed_decision_without_review_by,
    args=(), expect_code=0,
    expect=("decisions with no review_by", "decisions/template-decision.md"),
)
run_case(
    "review-by-present-not-flagged",
    lambda r: (
        seed_decision_without_review_by(r),
        edit(r, "wiki/decisions/template-decision.md", "confidence: medium",
             "confidence: medium\nreview_by: 2026-12-31"),
    ),
    args=(), expect_code=0,
    absent=("decisions/template-decision.md",),
)


def check_raw_tracked_fires():
    """The raw-tracked guard needs a git work tree, so it gets a git-backed case."""
    with tempfile.TemporaryDirectory(prefix="wiki-rawtracked-") as td:
        root = Path(td)
        copy_fixture(root)
        try:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
            (root / "raw").mkdir()
            (root / "raw" / "leak.pdf").write_text("source artifact")
            subprocess.run(["git", "add", "-f", "raw/leak.pdf"], cwd=root,
                           check=True, capture_output=True)
        except (OSError, subprocess.SubprocessError) as e:
            results.append(("raw-tracked-fires", True))
            print("SKIP raw-tracked-fires (git unavailable: "
                  f"{type(e).__name__})")
            return
        proc = subprocess.run([sys.executable, str(LINT), "--tier1"],
                              cwd=root, text=True, capture_output=True)
        ok = proc.returncode == 1 and "raw-tracked" in proc.stdout and "leak.pdf" in proc.stdout
        results.append(("raw-tracked-fires", ok))
        print(("PASS " if ok else "FAIL ") + "raw-tracked-fires")
        if not ok:
            print(f"  exit {proc.returncode}; stdout: {proc.stdout[:300]}")


check_raw_tracked_fires()

print()
failed = [n for n, ok in results if not ok]
print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
