#!/usr/bin/env python3
"""Regression evals for the structured approval ledger validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results


REPO_ROOT = Path(__file__).resolve().parents[1]
APPROVAL_VALIDATOR = REPO_ROOT / "scripts" / "validate_capture_runs.py"

results = Results()


def run_validator(name: str, lines: list[object | str], expect_code: int,
                  expect: tuple[str, ...] = ()) -> None:
    with tempfile.TemporaryDirectory(prefix="wiki-ledger-eval-") as td:
        path = Path(td) / "ledger.jsonl"
        rendered = []
        for line in lines:
            if isinstance(line, str):
                rendered.append(line)
            else:
                rendered.append(json.dumps(line, sort_keys=True, separators=(",", ":")))
        path.write_text("\n".join(rendered) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(APPROVAL_VALIDATOR), str(path)],
            text=True,
            capture_output=True,
            check=False,
        )
    output = proc.stdout + proc.stderr
    ok = proc.returncode == expect_code and all(marker in output for marker in expect)
    missing = [marker for marker in expect if marker not in output]
    detail = f"exit {proc.returncode} (expected {expect_code}); missing {missing}; output: " + output.replace("\n", " | ")
    results.record(name, ok, detail)


def approval_schema() -> dict[str, object]:
    return {
        "record_type": "schema",
        "schema_version": 1,
        "description": "approval ledger fixture",
    }


def capture_record() -> dict[str, object]:
    return {
        "record_type": "capture_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "artifact": "Fixture analysis",
        "route": "analysis-capture",
        "phase": "accepted",
        "primary_home": "wiki/analyses/fixture.md",
        "pages_touched": ["wiki/analyses/fixture.md", "wiki/index.md"],
        "source_path": "",
        "synthesized_pages": 3,
        "word_count": 301,
        "domain_context": True,
        "triggers": [],
        "approved_at": "2026-06-15T00:00:00+00:00",
    }


def synthesis_record() -> dict[str, object]:
    return {
        "record_type": "synthesis_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "artifact": "Fixture synthesis",
        "drafts": "wiki/overview.md draft",
        "primary_home": "wiki/synthesis.md",
        "pages_touched": ["wiki/synthesis.md", "wiki/overview.md"],
        "ledger_update_required": True,
        "approved_at": "2026-06-15T00:00:00+00:00",
    }


run_validator(
    "capture-valid-passes",
    [approval_schema(), capture_record()],
    0,
    ("validation passed",),
)
run_validator(
    "capture-malformed-json-fails",
    [approval_schema(), "{not json"],
    1,
    ("invalid JSON",),
)
duplicate_capture = capture_record()
duplicate_capture_later = capture_record()
duplicate_capture_later["approved_at"] = "2026-06-16T00:00:00+00:00"
run_validator(
    "capture-duplicate-approval-fails",
    [approval_schema(), duplicate_capture, duplicate_capture_later],
    1,
    ("duplicate approval record",),
)
invalid_trigger_capture = capture_record()
invalid_trigger_capture["triggers"] = ["not_a_valid_trigger"]
run_validator(
    "capture-invalid-trigger-fails",
    [approval_schema(), invalid_trigger_capture],
    1,
    ("triggers must be a list of valid promotion triggers",),
)
out_of_root_capture = capture_record()
out_of_root_capture["pages_touched"] = ["wiki/analyses/fixture.md", "secret/leak.md"]
run_validator(
    "capture-out-of-root-scope-fails",
    [approval_schema(), out_of_root_capture],
    1,
    ("allowed root",),
)
home_not_touched_capture = capture_record()
home_not_touched_capture["primary_home"] = "wiki/analyses/other.md"
run_validator(
    "capture-primary-home-not-in-pages-touched-fails",
    [approval_schema(), home_not_touched_capture],
    1,
    ("primary_home must be included in pages_touched",),
)
run_validator(
    "capture-missing-schema-fails",
    [capture_record()],
    1,
    ("expected exactly one schema record",),
)
run_validator(
    "capture-duplicate-schema-fails",
    [approval_schema(), approval_schema(), capture_record()],
    1,
    ("expected exactly one schema record",),
)
run_validator(
    "capture-schema-not-first-fails",
    [capture_record(), approval_schema()],
    1,
    ("schema record must be the first line",),
)

run_validator(
    "synthesis-valid-passes",
    [approval_schema(), synthesis_record()],
    0,
    ("validation passed",),
)
run_validator(
    "synthesis-malformed-json-fails",
    [approval_schema(), "{not json"],
    1,
    ("invalid JSON",),
)
duplicate_synthesis = synthesis_record()
duplicate_synthesis_later = synthesis_record()
duplicate_synthesis_later["approved_at"] = "2026-06-16T00:00:00+00:00"
run_validator(
    "synthesis-duplicate-approval-fails",
    [approval_schema(), duplicate_synthesis, duplicate_synthesis_later],
    1,
    ("duplicate approval record",),
)
pending_synthesis = synthesis_record()
pending_synthesis["approval_status"] = "pending"
run_validator(
    "synthesis-pending-status-fails",
    [approval_schema(), pending_synthesis],
    1,
    ("approval_status must be approved",),
)
bad_synthesis_ledger = synthesis_record()
bad_synthesis_ledger["ledger_update_required"] = False
run_validator(
    "synthesis-home-ledger-flag-fails",
    [approval_schema(), bad_synthesis_ledger],
    1,
    ("ledger_update_required true",),
)
synthesis_home_not_touched = synthesis_record()
synthesis_home_not_touched["primary_home"] = "wiki/overview.md"
synthesis_home_not_touched["pages_touched"] = ["wiki/synthesis.md", "wiki/log.md"]
synthesis_home_not_touched["ledger_update_required"] = False
run_validator(
    "synthesis-primary-home-not-in-pages-touched-fails",
    [approval_schema(), synthesis_home_not_touched],
    1,
    ("primary_home must be included in pages_touched",),
)
missing_ledger_flag = synthesis_record()
missing_ledger_flag["primary_home"] = "wiki/overview.md"
missing_ledger_flag["pages_touched"] = ["wiki/overview.md", "wiki/index.md"]
del missing_ledger_flag["ledger_update_required"]
run_validator(
    "synthesis-ledger-flag-not-boolean-fails",
    [approval_schema(), missing_ledger_flag],
    1,
    ("ledger_update_required must be a boolean",),
)
out_of_root_synthesis = synthesis_record()
out_of_root_synthesis["pages_touched"] = ["wiki/synthesis.md", "secret/leak.md"]
run_validator(
    "synthesis-out-of-root-scope-fails",
    [approval_schema(), out_of_root_synthesis],
    1,
    ("allowed root",),
)
# Reverse ledger-flag check: a non-synthesis.md home may not claim a ledger
# update is required.
reverse_ledger_flag = synthesis_record()
reverse_ledger_flag["primary_home"] = "wiki/overview.md"
reverse_ledger_flag["pages_touched"] = ["wiki/overview.md", "wiki/log.md"]
reverse_ledger_flag["ledger_update_required"] = True
run_validator(
    "synthesis-reverse-ledger-flag-fails",
    [approval_schema(), reverse_ledger_flag],
    1,
    ("unless primary_home is wiki/synthesis.md",),
)
run_validator(
    "synthesis-missing-schema-fails",
    [synthesis_record()],
    1,
    ("expected exactly one schema record",),
)
run_validator(
    "synthesis-duplicate-schema-fails",
    [approval_schema(), approval_schema(), synthesis_record()],
    1,
    ("expected exactly one schema record",),
)
run_validator(
    "synthesis-schema-not-first-fails",
    [synthesis_record(), approval_schema()],
    1,
    ("schema record must be the first line",),
)

# Structural and per-field branches: blank lines, timestamps, analysis
# thresholds, promotion triggers, backfill rules, and placeholder scopes.
run_validator(
    "blank-line-fails",
    [approval_schema(), "", capture_record()],
    1,
    ("blank lines are not allowed",),
)
bad_timestamp = capture_record()
bad_timestamp["approved_at"] = "mid-June sometime"
run_validator(
    "capture-bad-timestamp-fails",
    [approval_schema(), bad_timestamp],
    1,
    ("ISO-8601",),
)
below_bar = capture_record()
below_bar["word_count"] = 200
run_validator(
    "analysis-below-word-bar-fails",
    [approval_schema(), below_bar],
    1,
    ("3+ pages, >300 words",),
)
empty_trigger_promo = capture_record()
empty_trigger_promo["route"] = "promotion-audit"
empty_trigger_promo["triggers"] = []
run_validator(
    "promotion-empty-triggers-fails",
    [approval_schema(), empty_trigger_promo],
    1,
    ("at least one trigger",),
)
backfill_no_source = capture_record()
backfill_no_source["backfilled"] = True
run_validator(
    "backfill-without-source-fails",
    [approval_schema(), backfill_no_source],
    1,
    ("backfill_source",),
)
backfill_not_bool = capture_record()
backfill_not_bool["backfilled"] = "yes"
run_validator(
    "backfill-non-boolean-fails",
    [approval_schema(), backfill_not_bool],
    1,
    ("backfilled must be a boolean",),
)
# Backfilled records may reference paths that predate the current roots.
backfill_legacy_root = capture_record()
backfill_legacy_root["backfilled"] = True
backfill_legacy_root["backfill_source"] = "wiki/log.md entry 2026-05-01"
backfill_legacy_root["pages_touched"] = ["wiki/analyses/fixture.md", "legacy/old.md"]
run_validator(
    "backfill-legacy-root-passes",
    [approval_schema(), backfill_legacy_root],
    0,
    ("validation passed",),
)
placeholder_pages = capture_record()
placeholder_pages["pages_touched"] = ["wiki/analyses/fixture.md", "wiki/<entity>/x.md"]
run_validator(
    "capture-placeholder-pages-fails",
    [approval_schema(), placeholder_pages],
    1,
    ("placeholder paths",),
)
placeholder_home = capture_record()
placeholder_home["primary_home"] = "wiki/analyses/<slug>.md"
placeholder_home["pages_touched"] = ["wiki/analyses/<slug>.md", "wiki/index.md"]
run_validator(
    "capture-placeholder-home-fails",
    [approval_schema(), placeholder_home],
    1,
    ("primary_home must not be a placeholder",),
)

sys.exit(results.finish())
