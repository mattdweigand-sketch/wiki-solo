#!/usr/bin/env python3
"""Check provider contract readiness with the current no-write stub providers."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from wiki_eval_run import validate_judge_contract, validate_writer_contract


RUNS_ROOT = Path("tmp/wiki-runs")
PROVIDER_NAMES = {"stub"}
SEMANTIC_ARTIFACTS = ["evidence.json", "classifier.json", "contradictions.json", "links.json"]
RUN_ARTIFACTS = ["writer.json", "judge.json", "draft/manifest.json", "apply-plan.json"]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Check wiki provider contract readiness.")
    p.add_argument("source_path", help="Path to a raw source artifact.")
    p.add_argument("--run-id", default="")
    p.add_argument("--runs-root", default=str(RUNS_ROOT))
    p.add_argument("--semantic-provider", choices=sorted(PROVIDER_NAMES), default="stub")
    p.add_argument("--writer-provider", choices=sorted(PROVIDER_NAMES), default="stub")
    p.add_argument("--judge-provider", choices=sorted(PROVIDER_NAMES), default="stub")
    p.add_argument("--overwrite", action="store_true")
    return p


def slug(text: str) -> str:
    value = text.lower()
    value = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "provider-readiness"


def default_run_id(source_path: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{slug(Path(source_path).stem)}-provider-readiness"


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


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def git_status_wiki() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no", "wiki"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def validate_provider_artifacts(
    run_dir: Path,
    semantic_provider: str,
    writer_provider: str,
    judge_provider: str,
) -> list[str]:
    errors: list[str] = []
    for artifact in SEMANTIC_ARTIFACTS + RUN_ARTIFACTS:
        path = run_dir / artifact
        if not path.exists():
            errors.append(f"missing provider artifact: {path}")

    if errors:
        return errors

    classifier = load_json(run_dir / "classifier.json")
    evidence = load_json(run_dir / "evidence.json")
    contradictions = load_json(run_dir / "contradictions.json")
    links = load_json(run_dir / "links.json")
    writer = load_json(run_dir / "writer.json")
    judge = load_json(run_dir / "judge.json")
    packet = load_json(run_dir / "packet.json")
    manifest = load_json(run_dir / "draft" / "manifest.json")
    apply_plan = load_json(run_dir / "apply-plan.json")

    provider_checks = [
        ("classifier", classifier.get("provider"), semantic_provider),
        ("evidence", evidence.get("provider"), semantic_provider),
        ("contradictions", contradictions.get("provider"), semantic_provider),
        ("links", links.get("provider"), semantic_provider),
        ("writer", writer.get("provider"), writer_provider),
        ("judge", judge.get("provider"), judge_provider),
    ]
    for name, actual, expected in provider_checks:
        if actual != expected:
            errors.append(f"{name} provider: expected {expected!r}, got {actual!r}")

    no_write_checks = [
        ("classifier", classifier.get("writes_wiki")),
        ("evidence", evidence.get("writes_wiki")),
        ("contradictions", contradictions.get("writes_wiki")),
        ("links", links.get("writes_wiki")),
        ("writer", writer.get("writes_wiki")),
        ("judge", judge.get("writes_wiki")),
        ("draft manifest", manifest.get("writes_wiki")),
        ("apply plan", apply_plan.get("writes_wiki")),
    ]
    for name, value in no_write_checks:
        if value is not False:
            errors.append(f"{name} must declare writes_wiki=false")

    review_checks = [
        ("classifier", classifier.get("human_review_required")),
        ("evidence", evidence.get("human_review_required")),
        ("contradictions", contradictions.get("human_review_required")),
        ("links", links.get("human_review_required")),
        ("judge", judge.get("human_review_required")),
    ]
    for name, value in review_checks:
        if value is not True:
            errors.append(f"{name} must require human review")

    errors.extend(validate_writer_contract(writer, packet, run_dir))
    errors.extend(
        validate_judge_contract(
            judge,
            writer,
            packet,
            expected_policy_status=None,
            expected_judge_decision=None,
        )
    )

    return errors


def main() -> int:
    args = parser().parse_args()
    run_id = args.run_id or default_run_id(args.source_path)
    run_dir = Path(args.runs_root) / run_id

    if run_dir.exists():
        if not args.overwrite:
            print(f"wiki_provider_readiness error: {run_dir} exists; pass --overwrite", file=sys.stderr)
            return 1
        shutil.rmtree(run_dir)

    before = git_status_wiki()
    try:
        run_command(
            [
                sys.executable,
                "scripts/wiki_run.py",
                args.source_path,
                "--run-id",
                run_id,
                "--runs-root",
                args.runs_root,
            ],
        )
        run_command(
            [
                sys.executable,
                "scripts/wiki_semantic.py",
                str(run_dir),
                "--provider",
                args.semantic_provider,
                "--overwrite",
            ],
        )
        run_command(
            [
                sys.executable,
                "scripts/wiki_writer.py",
                str(run_dir / "packet.json"),
                "--provider",
                args.writer_provider,
                "--overwrite",
            ],
        )
        run_command(
            [
                sys.executable,
                "scripts/wiki_judge.py",
                str(run_dir),
                "--provider",
                args.judge_provider,
                "--overwrite",
            ],
        )
        run_command([sys.executable, "scripts/wiki_validate_semantic.py", str(run_dir)])
        run_command([sys.executable, "scripts/wiki_validate_run.py", str(run_dir)])
        apply_plan = run_command(
            [sys.executable, "scripts/wiki_apply_plan.py", str(run_dir)],
            allowed={0, 2},
        )
        (run_dir / "apply-plan.json").write_text(apply_plan.stdout, encoding="utf-8")
        run_command([sys.executable, "scripts/wiki_validate_apply_plan.py", str(run_dir / "apply-plan.json")])
    except Exception as exc:
        print(f"FAIL wiki-provider-readiness")
        print(f"  - {exc}")
        return 1

    errors = validate_provider_artifacts(
        run_dir,
        semantic_provider=args.semantic_provider,
        writer_provider=args.writer_provider,
        judge_provider=args.judge_provider,
    )

    after = git_status_wiki()
    if before != after:
        errors.append("wiki/ git status changed during provider readiness check")

    if errors:
        print("FAIL wiki-provider-readiness")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("PASS wiki-provider-readiness")
    print(f"Run directory: {run_dir}")
    print(f"Semantic provider: {args.semantic_provider}")
    print(f"Writer provider: {args.writer_provider}")
    print(f"Judge provider: {args.judge_provider}")
    print("No durable files were written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
