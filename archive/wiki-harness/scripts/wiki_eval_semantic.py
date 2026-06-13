#!/usr/bin/env python3
"""Smoke-test no-write semantic stub artifacts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from wiki_eval_sources import ensure_eval_sources, remove_existing_source_page, write_existing_source_page
from typing import Any


RUNS_ROOT = Path("tmp/wiki-runs")
SEMANTIC_FIXTURE_DIR = Path("tests/fixtures/wiki-semantic")
SCHEMA_PATHS = [
    Path("schemas/wiki-visual-evidence-artifact.schema.json"),
    Path("schemas/wiki-classifier-artifact.schema.json"),
    Path("schemas/wiki-contradiction-artifact.schema.json"),
    Path("schemas/wiki-link-scorer-artifact.schema.json"),
]
CASES = [
    {
        "id": "classifier-new-source",
        "run_id": "eval-classifier-new-source",
        "source_path": "raw/ai-research/folder-organization-guide.md",
        "expected_mode": "source_only",
    },
    {
        "id": "classifier-existing-source",
        "run_id": "eval-classifier-existing-source",
        "source_path": "raw/videos/2026-06-08-pewdiepie-did-it-again.md",
        "expected_mode": "no_op",
    },
]
VISUAL_EVIDENCE_CASES = [
    {
        "id": "visual-evidence-no-sidecar",
        "run_id": "eval-visual-evidence-no-sidecar",
        "source_path": "tests/fixtures/wiki-semantic/visual-sidecar-missing.jpg",
        "expected_performed": False,
        "expected_source": "none",
        "expected_summary_contains": "",
    },
    {
        "id": "visual-evidence-with-sidecar",
        "run_id": "eval-visual-evidence-with-sidecar",
        "source_path": "tests/fixtures/wiki-semantic/visual-sidecar-present.jpg",
        "expected_performed": True,
        "expected_source": "ocr",
        "expected_summary_contains": "RubricMiddleware",
    },
    {
        "id": "visual-evidence-empty-sidecar",
        "run_id": "eval-visual-evidence-empty-sidecar",
        "source_path": "tests/fixtures/wiki-semantic/visual-sidecar-empty.jpg",
        "expected_performed": False,
        "expected_source": "none",
        "expected_summary_contains": "",
    },
]
CLASSIFIER_KEYS = {
    "classifier_version",
    "provider",
    "source_path",
    "primary_home",
    "page_home_mode",
    "confidence",
    "rationale",
    "findings",
    "human_review_required",
    "writes_wiki",
    "provider_metadata",
}
CONTRADICTION_KEYS = {
    "contradiction_detector_version",
    "provider",
    "source_path",
    "primary_home",
    "status",
    "potential_contradictions",
    "findings",
    "human_review_required",
    "writes_wiki",
    "provider_metadata",
}
LINK_SCORER_KEYS = {
    "link_scorer_version",
    "provider",
    "source_path",
    "primary_home",
    "scored_links",
    "findings",
    "human_review_required",
    "writes_wiki",
    "provider_metadata",
}
EVIDENCE_KEYS = {
    "visual_evidence_version",
    "provider",
    "source_path",
    "primary_home",
    "required",
    "evidence_extraction_performed",
    "evidence_source",
    "visible_text_summary",
    "findings",
    "human_review_required",
    "writes_wiki",
    "provider_metadata",
}
VISUAL_SOURCE_FLAG = "visual_source_requires_review"
VISUAL_EVIDENCE_SOURCES = {"visual", "ocr", "human_verified", "none"}


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def git_status_wiki() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no", "wiki"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def set_nested(value: dict[str, Any], key_path: list[str], replacement: Any) -> None:
    current: Any = value
    for key in key_path[:-1]:
        if isinstance(current, dict):
            current = current.setdefault(key, {})
        elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
            current = current[int(key)]
        else:
            return
    if isinstance(current, dict):
        current[key_path[-1]] = replacement
    elif isinstance(current, list) and key_path[-1].isdigit() and int(key_path[-1]) < len(current):
        current[int(key_path[-1])] = replacement


def validate_schema_files() -> list[str]:
    errors: list[str] = []
    for path in SCHEMA_PATHS:
        if not path.exists():
            errors.append(f"missing schema file: {path}")
            continue
        try:
            load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"schema file is invalid JSON: {path}: {exc}")
    return errors


def create_run(run_id: str, source_path: str) -> tuple[Path, list[str]]:
    run_dir = RUNS_ROOT / run_id
    shutil.rmtree(run_dir, ignore_errors=True)
    result = run_command(
        [
            sys.executable,
            "scripts/wiki_run.py",
            source_path,
            "--run-id",
            run_id,
        ],
    )
    if result.returncode != 0:
        return run_dir, [result.stderr.strip() or result.stdout.strip()]
    return run_dir, []


def create_semantic_run(run_id: str, source_path: str) -> tuple[Path, list[str]]:
    run_dir, errors = create_run(run_id, source_path)
    if errors:
        return run_dir, errors

    result = run_command(
        [
            sys.executable,
            "scripts/wiki_semantic.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ],
    )
    if result.returncode != 0:
        return run_dir, [result.stderr.strip() or result.stdout.strip()]
    return run_dir, []


def create_visual_evidence_packet(run_id: str, source_path: str) -> Path:
    run_dir = RUNS_ROOT / run_id
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True)
    packet = {
        "source_path": source_path,
        "primary_home": "wiki/sources/visual-sidecar-fixture.md",
        "page_home_decision": {
            "mode": "source_only",
            "rationale": "Visual evidence fixture for semantic artifact validation.",
        },
        "risk_flags": [VISUAL_SOURCE_FLAG],
    }
    write_json(run_dir / "packet.json", packet)
    return run_dir


def apply_semantic_mutations(run_dir: Path, mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    allowed_artifacts = {"evidence.json", "classifier.json", "contradictions.json", "links.json"}
    for index, mutation in enumerate(mutations):
        artifact = mutation.get("artifact")
        if artifact not in allowed_artifacts:
            errors.append(
                f"mutation[{index}] artifact must be evidence.json, classifier.json, contradictions.json, or links.json",
            )
            continue
        path = run_dir / str(artifact)
        if not path.exists():
            errors.append(f"mutation[{index}] target does not exist: {path}")
            continue

        value = load_json(path)
        for change in mutation.get("set", []):
            key_path = change.get("path") if isinstance(change, dict) else None
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"mutation[{index}] set path must be a list of strings")
                continue
            set_nested(value, key_path, change.get("value"))
        write_json(path, value)
    return errors


def visual_source_required(packet: dict[str, Any]) -> bool:
    risk_flags = packet.get("risk_flags", [])
    if not isinstance(risk_flags, list):
        return False
    return VISUAL_SOURCE_FLAG in risk_flags


def validate_evidence(run_dir: Path) -> list[str]:
    errors: list[str] = []
    packet = load_json(run_dir / "packet.json")
    evidence = load_json(run_dir / "evidence.json")

    missing = sorted(EVIDENCE_KEYS - evidence.keys())
    extra = sorted(evidence.keys() - EVIDENCE_KEYS)
    if missing:
        errors.append(f"visual evidence artifact missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"visual evidence artifact has unsupported fields: {', '.join(extra)}")

    if evidence.get("visual_evidence_version") != "wiki-visual-evidence.v1":
        errors.append("visual evidence version must be wiki-visual-evidence.v1")
    if evidence.get("provider") != "stub":
        errors.append("visual evidence provider must be stub")
    if evidence.get("source_path") != packet.get("source_path"):
        errors.append("visual evidence source_path must match packet source_path")
    if evidence.get("primary_home") != packet.get("primary_home"):
        errors.append("visual evidence primary_home must match packet primary_home")

    expected_required = visual_source_required(packet)
    required = evidence.get("required")
    if not isinstance(required, bool):
        errors.append("visual evidence required must be a boolean")
    elif required is not expected_required:
        errors.append(f"visual evidence required: expected {expected_required!r}, got {required!r}")

    performed = evidence.get("evidence_extraction_performed")
    evidence_source = evidence.get("evidence_source")
    summary = evidence.get("visible_text_summary")
    if not isinstance(performed, bool):
        errors.append("visual evidence evidence_extraction_performed must be a boolean")
    if evidence_source not in VISUAL_EVIDENCE_SOURCES:
        errors.append("visual evidence evidence_source is invalid")
    if not isinstance(summary, str):
        errors.append("visual evidence visible_text_summary must be a string")
    if performed is True and evidence_source == "none":
        errors.append("visual evidence evidence_source cannot be none when extraction was performed")
    if performed is False and evidence_source != "none":
        errors.append("visual evidence evidence_source must be none when extraction was not performed")
    if performed is True and isinstance(summary, str) and not summary.strip():
        errors.append("visual evidence visible_text_summary is required when extraction was performed")
    if performed is False and isinstance(summary, str) and summary.strip():
        errors.append("visual evidence visible_text_summary must be empty when extraction was not performed")

    if evidence.get("writes_wiki") is not False:
        errors.append("visual evidence extractor must declare writes_wiki=false")
    if evidence.get("human_review_required") is not True:
        errors.append("visual evidence extractor must require human review")
    if not isinstance(evidence.get("findings"), list):
        errors.append("visual evidence findings must be a list")
    if not isinstance(evidence.get("provider_metadata"), dict):
        errors.append("visual evidence provider_metadata must be an object")

    return errors


def validate_classifier(
    run_dir: Path,
    expected_mode: str,
) -> list[str]:
    errors: list[str] = []
    packet = load_json(run_dir / "packet.json")
    classifier = load_json(run_dir / "classifier.json")

    missing = sorted(CLASSIFIER_KEYS - classifier.keys())
    extra = sorted(classifier.keys() - CLASSIFIER_KEYS)
    if missing:
        errors.append(f"classifier artifact missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"classifier artifact has unsupported fields: {', '.join(extra)}")

    if classifier.get("classifier_version") != "wiki-classifier.v1":
        errors.append("classifier_version must be wiki-classifier.v1")
    if classifier.get("provider") != "stub":
        errors.append("classifier provider must be stub")
    if classifier.get("source_path") != packet.get("source_path"):
        errors.append("classifier source_path must match packet source_path")
    if classifier.get("primary_home") != packet.get("primary_home"):
        errors.append("classifier primary_home must match packet primary_home")
    if classifier.get("page_home_mode") != expected_mode:
        errors.append(
            f"classifier page_home_mode: expected {expected_mode!r}, got {classifier.get('page_home_mode')!r}",
        )
    if classifier.get("writes_wiki") is not False:
        errors.append("classifier must declare writes_wiki=false")
    if classifier.get("human_review_required") is not True:
        errors.append("classifier must require human review")
    if not isinstance(classifier.get("findings"), list):
        errors.append("classifier findings must be a list")
    if not isinstance(classifier.get("provider_metadata"), dict):
        errors.append("classifier provider_metadata must be an object")

    return errors


def validate_contradictions(run_dir: Path) -> list[str]:
    errors: list[str] = []
    packet = load_json(run_dir / "packet.json")
    contradictions = load_json(run_dir / "contradictions.json")

    missing = sorted(CONTRADICTION_KEYS - contradictions.keys())
    extra = sorted(contradictions.keys() - CONTRADICTION_KEYS)
    if missing:
        errors.append(f"contradiction artifact missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"contradiction artifact has unsupported fields: {', '.join(extra)}")

    if contradictions.get("contradiction_detector_version") != "wiki-contradiction-detector.v1":
        errors.append("contradiction_detector_version must be wiki-contradiction-detector.v1")
    if contradictions.get("provider") != "stub":
        errors.append("contradiction provider must be stub")
    if contradictions.get("source_path") != packet.get("source_path"):
        errors.append("contradiction source_path must match packet source_path")
    if contradictions.get("primary_home") != packet.get("primary_home"):
        errors.append("contradiction primary_home must match packet primary_home")
    if contradictions.get("status") not in {"no_conflict_found", "potential_conflict", "blocked"}:
        errors.append("contradiction status is invalid")
    if contradictions.get("potential_contradictions") != []:
        errors.append("stub contradiction detector must not emit potential contradictions")
    if contradictions.get("writes_wiki") is not False:
        errors.append("contradiction detector must declare writes_wiki=false")
    if contradictions.get("human_review_required") is not True:
        errors.append("contradiction detector must require human review")
    if not isinstance(contradictions.get("findings"), list):
        errors.append("contradiction findings must be a list")
    if not isinstance(contradictions.get("provider_metadata"), dict):
        errors.append("contradiction provider_metadata must be an object")

    return errors


def validate_links(run_dir: Path) -> list[str]:
    errors: list[str] = []
    packet = load_json(run_dir / "packet.json")
    links = load_json(run_dir / "links.json")

    missing = sorted(LINK_SCORER_KEYS - links.keys())
    extra = sorted(links.keys() - LINK_SCORER_KEYS)
    if missing:
        errors.append(f"link scorer artifact missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"link scorer artifact has unsupported fields: {', '.join(extra)}")

    if links.get("link_scorer_version") != "wiki-link-scorer.v1":
        errors.append("link_scorer_version must be wiki-link-scorer.v1")
    if links.get("provider") != "stub":
        errors.append("link scorer provider must be stub")
    if links.get("source_path") != packet.get("source_path"):
        errors.append("link scorer source_path must match packet source_path")
    if links.get("primary_home") != packet.get("primary_home"):
        errors.append("link scorer primary_home must match packet primary_home")
    if not isinstance(links.get("scored_links"), list):
        errors.append("link scorer scored_links must be a list")
    else:
        proposed_links = packet.get("proposed_links", [])
        expected_count = len(proposed_links) if isinstance(proposed_links, list) else 0
        if len(links["scored_links"]) != expected_count:
            errors.append("link scorer must score exactly packet proposed_links")
        for index, scored_link in enumerate(links["scored_links"]):
            if not isinstance(scored_link, dict):
                errors.append(f"link scorer scored_links[{index}] must be an object")
                continue
            score = scored_link.get("score")
            if not isinstance(score, int) or score < 0 or score > 3:
                errors.append(f"link scorer scored_links[{index}].score must be 0..3")
    if links.get("writes_wiki") is not False:
        errors.append("link scorer must declare writes_wiki=false")
    if links.get("human_review_required") is not True:
        errors.append("link scorer must require human review")
    if not isinstance(links.get("findings"), list):
        errors.append("link scorer findings must be a list")
    if not isinstance(links.get("provider_metadata"), dict):
        errors.append("link scorer provider_metadata must be an object")

    return errors


def run_case(case: dict[str, str]) -> list[str]:
    run_dir, errors = create_run(case["run_id"], case["source_path"])
    if errors:
        return errors

    result = run_command(
        [
            sys.executable,
            "scripts/wiki_semantic.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ]
    )
    if result.returncode != 0:
        return [result.stderr.strip() or result.stdout.strip()]

    expected_artifacts = [
        "evidence.json",
        "classifier.json",
        "contradictions.json",
        "links.json",
    ]
    for artifact in expected_artifacts:
        if not (run_dir / artifact).exists():
            return [f"missing semantic artifact: {artifact}"]

    errors.extend(validate_evidence(run_dir))
    errors.extend(validate_classifier(run_dir, case["expected_mode"]))
    errors.extend(validate_contradictions(run_dir))
    errors.extend(validate_links(run_dir))
    return errors


def run_visual_evidence_case(case: dict[str, Any]) -> list[str]:
    run_dir = create_visual_evidence_packet(str(case["run_id"]), str(case["source_path"]))
    result = run_command(
        [
            sys.executable,
            "scripts/wiki_visual_extractor.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ]
    )
    if result.returncode != 0:
        return [result.stderr.strip() or result.stdout.strip()]

    errors = validate_evidence(run_dir)
    evidence = load_json(run_dir / "evidence.json")
    if evidence.get("evidence_extraction_performed") is not case["expected_performed"]:
        errors.append(
            "visual evidence extraction state: "
            f"expected {case['expected_performed']!r}, got {evidence.get('evidence_extraction_performed')!r}",
        )
    if evidence.get("evidence_source") != case["expected_source"]:
        errors.append(
            f"visual evidence source: expected {case['expected_source']!r}, got {evidence.get('evidence_source')!r}",
        )
    expected_summary = str(case.get("expected_summary_contains", ""))
    summary = evidence.get("visible_text_summary")
    if expected_summary and (not isinstance(summary, str) or expected_summary not in summary):
        errors.append(f"visual evidence summary missing expected text: {expected_summary}")
    if not expected_summary and summary:
        errors.append("visual evidence summary should be empty")
    return errors


def run_negative_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    fixture_id = str(fixture.get("id", path.stem))
    run_id = str(fixture.get("run_id") or f"eval-{fixture_id}")
    source_path = str(fixture["source_path"])
    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]

    run_dir, errors = create_semantic_run(run_id, source_path)
    if errors:
        return errors

    errors.extend(apply_semantic_mutations(run_dir, mutations))
    if errors:
        return errors

    result = run_command([sys.executable, "scripts/wiki_validate_semantic.py", str(run_dir)])
    if result.returncode == 0:
        return ["semantic validator unexpectedly passed"]

    output = result.stderr.strip() or result.stdout.strip()
    expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
    missing_errors = [expected for expected in expected_errors if expected not in output]
    return [f"missing expected error: {error}" for error in missing_errors]


def validate_negative_fixtures() -> tuple[int, int]:
    if not SEMANTIC_FIXTURE_DIR.exists():
        print(f"FAIL semantic-fixtures")
        print(f"  - missing semantic fixture dir: {SEMANTIC_FIXTURE_DIR}")
        return 1, 1

    fixture_paths = sorted(SEMANTIC_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        print("FAIL semantic-fixtures")
        print(f"  - no semantic fixtures found in {SEMANTIC_FIXTURE_DIR}")
        return 1, 1

    failures = 0
    for path in fixture_paths:
        fixture_id = path.stem
        try:
            fixture = load_json(path)
            fixture_id = str(fixture.get("id", path.stem))
            errors = run_negative_fixture(path)
        except Exception as exc:
            errors = [str(exc)]
        if errors:
            failures += 1
            print(f"FAIL {fixture_id}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {fixture_id}")
    return len(fixture_paths), failures


def main() -> int:
    ensure_eval_sources()
    write_existing_source_page()
    before = git_status_wiki()
    failures = 0
    schema_errors = validate_schema_files()
    if schema_errors:
        failures += 1
        print("FAIL semantic-schemas")
        for error in schema_errors:
            print(f"  - {error}")
    else:
        print("PASS semantic-schemas")

    for case in CASES:
        errors = run_case(case)
        if errors:
            failures += 1
            print(f"FAIL {case['id']}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {case['id']}")

    for case in VISUAL_EVIDENCE_CASES:
        errors = run_visual_evidence_case(case)
        if errors:
            failures += 1
            print(f"FAIL {case['id']}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"PASS {case['id']}")

    fixture_count, fixture_failures = validate_negative_fixtures()
    failures += fixture_failures

    after = git_status_wiki()
    if before != after:
        failures += 1
        print("FAIL semantic-no-write")
        print("  - wiki/ git status changed during semantic eval")
    remove_existing_source_page()

    total_cases = len(CASES) + len(VISUAL_EVIDENCE_CASES) + 1 + fixture_count
    print(f"\nSummary: {total_cases - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
