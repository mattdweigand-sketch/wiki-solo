#!/usr/bin/env python3
"""Smoke-test the no-write wiki apply boundary."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from wiki_eval_sources import ensure_eval_sources, remove_existing_source_page, write_existing_source_page
from typing import Any


RUNS_ROOT = Path("tmp/wiki-runs")
SOURCE = "raw/videos/2026-06-08-pewdiepie-did-it-again.md"
APPLY_PLAN_SCHEMA = Path("schemas/wiki-apply-plan.schema.json")
APPLY_PLAN_FIXTURE_DIR = Path("tests/fixtures/wiki-apply-plan")
APPLY_PLAN_VALID_FIXTURE_DIR = Path("tests/fixtures/wiki-apply-plan-valid")


def run_command(command: list[str], allowed: set[int] | None = None) -> subprocess.CompletedProcess[str]:
    allowed_codes = allowed or {0}
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode not in allowed_codes:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(message or f"{command[0]} exited {result.returncode}")
    return result


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


def validate_apply_plan_schema_file() -> list[str]:
    if not APPLY_PLAN_SCHEMA.exists():
        return [f"missing apply plan schema: {APPLY_PLAN_SCHEMA}"]
    try:
        load_json(APPLY_PLAN_SCHEMA)
    except json.JSONDecodeError as exc:
        return [f"apply plan schema is invalid JSON: {exc}"]
    return []


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def create_run(run_id: str, source_path: str = SOURCE) -> Path:
    run_dir = RUNS_ROOT / run_id
    shutil.rmtree(run_dir, ignore_errors=True)
    run_command(
        [
            sys.executable,
            "scripts/wiki_run.py",
            source_path,
            "--run-id",
            run_id,
        ],
    )
    run_command(
        [
            sys.executable,
            "scripts/wiki_writer.py",
            str(run_dir / "packet.json"),
            "--provider",
            "stub",
            "--overwrite",
        ],
    )
    run_command(
        [
            sys.executable,
            "scripts/wiki_judge.py",
            str(run_dir),
            "--provider",
            "stub",
            "--overwrite",
        ],
    )
    return run_dir


def mutate_json(path: Path, updates: dict[str, Any]) -> None:
    value = load_json(path)
    value.update(updates)
    write_json(path, value)


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


def apply_plan_fixture_base() -> dict[str, Any]:
    return {
        "apply_plan_version": "wiki-apply-plan.v1",
        "run_dir": "tmp/wiki-runs/eval-apply-plan-fixture",
        "status": "ready_for_approval",
        "required_approval": True,
        "target_files": [],
        "operations": [
            {
                "op": "no_op",
                "target_path": "",
                "draft_path": None,
                "status": "stub",
            }
        ],
        "blockers": [],
        "review_reasons": [
            "human approval is required before any durable wiki write",
        ],
        "writes_wiki": False,
    }


def apply_plan_mutations(plan: dict[str, Any], mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, mutation in enumerate(mutations):
        for change in mutation.get("set", []):
            key_path = change.get("path") if isinstance(change, dict) else None
            if not isinstance(key_path, list) or not all(isinstance(key, str) for key in key_path):
                errors.append(f"mutation[{index}] set path must be a list of strings")
                continue
            set_nested(plan, key_path, change.get("value"))
    return errors


def apply_run_mutations(run_dir: Path, mutations: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    allowed_artifacts = {"packet.json", "policy.json", "writer.json", "judge.json", "draft/manifest.json"}
    for index, mutation in enumerate(mutations):
        artifact = mutation.get("artifact")
        if artifact not in allowed_artifacts:
            errors.append(
                f"mutation[{index}] artifact must be packet.json, policy.json, writer.json, judge.json, or draft/manifest.json",
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


def run_apply_plan_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    plan = apply_plan_fixture_base()
    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]

    errors = apply_plan_mutations(plan, mutations)
    if errors:
        return errors

    result = subprocess.run(
        [sys.executable, "scripts/wiki_validate_apply_plan.py", "-"],
        input=json.dumps(plan),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return ["apply plan validator unexpectedly passed"]

    output = result.stderr.strip() or result.stdout.strip()
    expected_errors = [str(error) for error in fixture.get("expected_errors", [])]
    missing_errors = [expected for expected in expected_errors if expected not in output]
    return [f"missing expected error: {error}" for error in missing_errors]


def apply_plan_fixture_cases() -> list[str]:
    if not APPLY_PLAN_FIXTURE_DIR.exists():
        return [f"missing apply plan fixture dir: {APPLY_PLAN_FIXTURE_DIR}"]
    fixture_paths = sorted(APPLY_PLAN_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        return [f"no apply plan fixtures found in {APPLY_PLAN_FIXTURE_DIR}"]

    errors: list[str] = []
    for path in fixture_paths:
        fixture_errors = run_apply_plan_fixture(path)
        if fixture_errors:
            errors.extend(f"{path.stem}: {error}" for error in fixture_errors)
    return errors


def compare_list_field(plan: dict[str, Any], fixture: dict[str, Any], field: str, fixture_field: str) -> list[str]:
    if fixture_field not in fixture:
        return []
    expected = fixture[fixture_field]
    actual = plan.get(field)
    if actual != expected:
        return [f"{field}: expected {expected!r}, got {actual!r}"]
    return []


def run_positive_apply_plan_fixture(path: Path) -> list[str]:
    fixture = load_json(path)
    run_id = str(fixture.get("run_id") or f"eval-{fixture.get('id', path.stem)}")
    source_path = str(fixture["source_path"])
    run_dir = create_run(run_id, source_path=source_path)

    mutations = fixture.get("mutations", [])
    if not isinstance(mutations, list):
        return ["mutations must be a list"]
    expected_touched_files = fixture.get("expected_touched_files")
    if expected_touched_files is not None:
        if not isinstance(expected_touched_files, list) or not all(
            isinstance(path, str) for path in expected_touched_files
        ):
            return ["expected_touched_files must be a list of strings"]
        set_expected_touched_files(run_dir, expected_touched_files)
    errors = apply_run_mutations(run_dir, mutations)
    if errors:
        return errors

    expected_exit_code = int(fixture.get("expected_exit_code", 0))
    result = run_command(
        [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
        allowed={expected_exit_code},
    )
    try:
        plan = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [f"apply plan output must be JSON: {exc}"]

    validator = subprocess.run(
        [sys.executable, "scripts/wiki_validate_apply_plan.py", "-"],
        input=result.stdout,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if validator.returncode != 0:
        return [validator.stderr.strip() or validator.stdout.strip()]

    errors = []
    if plan.get("status") != fixture.get("expected_status"):
        errors.append(f"status: expected {fixture.get('expected_status')!r}, got {plan.get('status')!r}")
    if plan.get("required_approval") != fixture.get("expected_required_approval"):
        errors.append(
            f"required_approval: expected {fixture.get('expected_required_approval')!r}, got {plan.get('required_approval')!r}",
        )
    if plan.get("writes_wiki") != fixture.get("expected_writes_wiki"):
        errors.append(f"writes_wiki: expected {fixture.get('expected_writes_wiki')!r}, got {plan.get('writes_wiki')!r}")
    errors.extend(compare_list_field(plan, fixture, "target_files", "expected_target_files"))
    errors.extend(compare_list_field(plan, fixture, "blockers", "expected_blockers"))
    errors.extend(compare_list_field(plan, fixture, "review_reasons", "expected_review_reasons"))

    expected_ops = fixture.get("expected_operation_ops")
    if expected_ops is not None:
        operations = plan.get("operations", [])
        actual_ops = [operation.get("op") for operation in operations if isinstance(operation, dict)]
        if actual_ops != expected_ops:
            errors.append(f"operation ops: expected {expected_ops!r}, got {actual_ops!r}")
    return errors


def positive_apply_plan_fixture_cases() -> list[str]:
    if not APPLY_PLAN_VALID_FIXTURE_DIR.exists():
        return [f"missing positive apply plan fixture dir: {APPLY_PLAN_VALID_FIXTURE_DIR}"]
    fixture_paths = sorted(APPLY_PLAN_VALID_FIXTURE_DIR.glob("*.json"))
    if not fixture_paths:
        return [f"no positive apply plan fixtures found in {APPLY_PLAN_VALID_FIXTURE_DIR}"]

    errors: list[str] = []
    for path in fixture_paths:
        fixture_errors = run_positive_apply_plan_fixture(path)
        if fixture_errors:
            errors.extend(f"{path.stem}: {error}" for error in fixture_errors)
    return errors


def set_expected_touched_files(run_dir: Path, paths: list[str]) -> None:
    mutate_json(run_dir / "packet.json", {"expected_touched_files": paths})
    manifest = load_json(run_dir / "draft" / "manifest.json")
    manifest["operations"] = [
        {
            "op": "create",
            "target_path": path,
            "draft_path": str(run_dir / "draft" / "README.md"),
            "status": "stub",
        }
        for path in paths
    ]
    write_json(run_dir / "draft" / "manifest.json", manifest)


def expect_apply(
    run_dir: Path,
    allowed: set[int],
    required_text: str,
    approved: bool = True,
) -> list[str]:
    command = [sys.executable, "scripts/wiki_apply.py", str(run_dir)]
    if approved:
        command.append("--approved")
    result = run_command(command, allowed=allowed)
    output = result.stdout + result.stderr
    if required_text not in output:
        return [f"expected apply output to contain: {required_text}"]
    return []


def expect_apply_plan(
    run_dir: Path,
    allowed: set[int],
    expected_status: str,
    expected_target: str | None = None,
) -> list[str]:
    result = run_command(
        [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
        allowed=allowed,
    )
    try:
        plan = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return [f"apply plan output must be JSON: {exc}"]

    errors: list[str] = []
    if plan.get("apply_plan_version") != "wiki-apply-plan.v1":
        errors.append("apply plan version is invalid")
    if plan.get("status") != expected_status:
        errors.append(f"apply plan status: expected {expected_status!r}, got {plan.get('status')!r}")
    if plan.get("required_approval") is not True:
        errors.append("apply plan must require approval")
    if plan.get("writes_wiki") is not False:
        errors.append("apply plan must declare writes_wiki=false")
    if not isinstance(plan.get("operations"), list):
        errors.append("apply plan operations must be a list")
    if expected_target is not None and expected_target not in plan.get("target_files", []):
        errors.append(f"apply plan target_files must include {expected_target}")
    validator = subprocess.run(
        [sys.executable, "scripts/wiki_validate_apply_plan.py", "-"],
        input=result.stdout,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if validator.returncode != 0:
        errors.append(validator.stderr.strip() or validator.stdout.strip())
    return errors


def valid_review_case() -> list[str]:
    errors: list[str] = []
    run_dir = create_run("eval-apply-valid-review")

    approval_result = run_command(
        [sys.executable, "scripts/wiki_apply.py", str(run_dir)],
        allowed={3},
    )
    if "APPROVAL REQUIRED" not in approval_result.stdout:
        errors.append("apply boundary should require approval by default")

    approved_result = run_command(
        [sys.executable, "scripts/wiki_apply.py", str(run_dir), "--approved"],
    )
    if "PASS wiki-apply-boundary" not in approved_result.stdout:
        errors.append("approved apply boundary should pass")

    return errors


def apply_plan_ready_case() -> list[str]:
    run_dir = create_run("eval-apply-plan-ready")
    errors = expect_apply_plan(
        run_dir,
        allowed={0},
        expected_status="ready_for_approval",
    )
    if errors:
        return errors

    result = run_command(
        [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
    )
    plan = json.loads(result.stdout)
    operations = plan.get("operations", [])
    if not operations or operations[0].get("op") != "no_op":
        return ["apply plan should preserve no_op manifest operations"]
    if plan.get("target_files") != []:
        return ["apply plan no_op target_files should be empty"]
    return []


def apply_plan_blocked_case() -> list[str]:
    run_dir = create_run("eval-apply-plan-blocked")
    mutate_json(run_dir / "policy.json", {"status": "reject"})
    mutate_json(run_dir / "judge.json", {"policy_status": "reject"})
    errors = expect_apply_plan(run_dir, allowed={2}, expected_status="blocked")
    if errors:
        return errors

    result = run_command(
        [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
        allowed={2},
    )
    plan = json.loads(result.stdout)
    if "policy status is reject" not in plan.get("blockers", []):
        return ["apply plan blockers must include policy reject"]
    return []


def policy_reject_case() -> list[str]:
    run_dir = create_run("eval-apply-policy-reject")
    mutate_json(run_dir / "policy.json", {"status": "reject"})
    mutate_json(run_dir / "judge.json", {"policy_status": "reject"})
    return expect_apply(run_dir, allowed={2}, required_text="policy status is reject")


def raw_touch_case() -> list[str]:
    run_dir = create_run("eval-apply-raw-touch")
    set_expected_touched_files(run_dir, ["raw/videos/example.md"])
    return expect_apply(
        run_dir,
        allowed={2},
        required_text="target_path must be under wiki/",
    )


def writer_writes_wiki_case() -> list[str]:
    run_dir = create_run("eval-apply-writer-writes-wiki")
    mutate_json(run_dir / "writer.json", {"writes_wiki": True})
    return expect_apply(run_dir, allowed={2}, required_text="writer must declare writes_wiki=false")


def judge_reject_case() -> list[str]:
    run_dir = create_run("eval-apply-judge-reject")
    mutate_json(run_dir / "judge.json", {"decision": "reject"})
    return expect_apply(run_dir, allowed={2}, required_text="judge decision is reject")


def dirty_touched_file_case() -> list[str]:
    run_dir = create_run("eval-apply-dirty-touched-file")
    target = Path("wiki/sources/pewdiepie-did-it-again.md")
    original = target.read_text(encoding="utf-8")
    try:
        set_expected_touched_files(run_dir, [str(target)])
        target.write_text(original + "\n", encoding="utf-8")
        return expect_apply(
            run_dir,
            allowed={2},
            required_text="working tree is dirty in expected touched files",
        )
    finally:
        target.write_text(original, encoding="utf-8")


def main() -> int:
    ensure_eval_sources()
    write_existing_source_page()
    before = git_status_wiki()
    cases = [
        ("apply-plan-schema", validate_apply_plan_schema_file),
        ("valid-review", valid_review_case),
        ("apply-plan-ready", apply_plan_ready_case),
        ("apply-plan-blocked", apply_plan_blocked_case),
        ("apply-plan-positive-fixtures", positive_apply_plan_fixture_cases),
        ("apply-plan-fixtures", apply_plan_fixture_cases),
        ("policy-reject", policy_reject_case),
        ("raw-touch", raw_touch_case),
        ("writer-writes-wiki", writer_writes_wiki_case),
        ("judge-reject", judge_reject_case),
        ("dirty-touched-file", dirty_touched_file_case),
    ]

    errors: list[str] = []
    for name, case in cases:
        try:
            case_errors = case()
        except Exception as exc:
            case_errors = [str(exc)]
        if case_errors:
            errors.append(name)
            errors.extend(f"  - {error}" for error in case_errors)

    after = git_status_wiki()
    if before != after:
        errors.append("wiki/ git status changed during apply boundary eval")
    remove_existing_source_page()

    if errors:
        print("FAIL wiki-apply-boundary")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-apply-boundary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
