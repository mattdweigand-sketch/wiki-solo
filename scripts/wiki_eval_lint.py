#!/usr/bin/env python3
"""Regression eval for lint.py.

Guards lint's checks against going vacuous: every Tier-1 check added since
the phantom-link incident gets a seeded violation that must fire, and the
Tier-2 adjudication/suppression machinery gets positive and negative cases.
A check that cannot fail is indistinguishable from no check; this suite
exists so a future lint edit cannot silently disarm one.

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


def run_case(name, mutate, args=("--tier1",), expect_code=0, expect=(), absent=()):
    """Copy the fixture, apply `mutate(root)`, run lint, assert on output."""
    with tempfile.TemporaryDirectory(prefix="wiki-lint-eval-") as td:
        root = Path(td)
        shutil.copytree(FIXTURE / "wiki", root / "wiki")
        shutil.copytree(FIXTURE / "scripts", root / "scripts")
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
    "adjudication-stale-fires",
    lambda r: write_adjudications(r, accepted_orphans=[
        {"page": "sources/renamed-away.md", "reason": "x", "date": "2026-06-11"}]),
    expect_code=1, expect=("adjudication-stale", "renamed-away"),
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
    "unexpected-wiki-folder-fires",
    lambda r: (r / "wiki" / "misc").mkdir(),
    expect_code=1, expect=("wiki-structure", "unexpected wiki/ folder"),
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
    "finder-metadata-fires",
    lambda r: (r / "wiki" / ".DS_Store").write_text("metadata"),
    expect_code=1, expect=("os-metadata", ".DS_Store"),
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

print()
failed = [n for n, ok in results if not ok]
print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
