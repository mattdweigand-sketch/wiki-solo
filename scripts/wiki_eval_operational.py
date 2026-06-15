#!/usr/bin/env python3
"""Regression evals for operational helper scripts.

These checks keep backup, shortcut, duplicate-skill cleanup, and ledger
validation behavior from depending on ad hoc manual runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import export_wiki


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC = REPO_ROOT / "scripts" / "sync_codex_skills.py"
PROMOTE = REPO_ROOT / "scripts" / "wiki_promote.py"
CAPTURE_LEDGER = REPO_ROOT / "scripts" / "capture-runs.jsonl"
SYNTHESIS_LEDGER = REPO_ROOT / "scripts" / "synthesis-runs.jsonl"
SYNTHESIS_GATE = REPO_ROOT / "scripts" / "synthesis_gate.py"
VALIDATE_CAPTURE = REPO_ROOT / "scripts" / "validate_capture_runs.py"
VALIDATE_SYNTHESIS = REPO_ROOT / "scripts" / "validate_synthesis_runs.py"

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    if ok:
        print(f"PASS {name}")
    else:
        print(f"FAIL {name}")
        if detail:
            print("  " + detail.replace("\n", " | "))


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)


def schema_line(path: Path) -> str:
    return path.read_text(encoding="utf-8").splitlines()[0] + "\n"


def test_export_contract() -> None:
    files = export_wiki.export_files(REPO_ROOT)
    names = [path.relative_to(REPO_ROOT).as_posix() for path in files]
    errors = export_wiki.validate_names(names)
    check("export-current-tree-has-required-coverage", not errors, "\n".join(errors))
    check("export-excludes-agents-runtime", export_wiki.should_exclude(".agents/skills/wiki-export/SKILL.md"))
    check("export-current-tree-does-not-include-agents", not any(name.startswith(".agents/") for name in names))

    proc = run([sys.executable, str(REPO_ROOT / "scripts" / "export_wiki.py"), "--dry-run", "--date", "2026-06-15"], cwd=REPO_ROOT)
    check(
        "export-dry-run-verifies-coverage",
        proc.returncode == 0 and "Required export coverage: yes" in proc.stdout,
        proc.stdout + proc.stderr,
    )


def test_sync_codex_skills() -> None:
    with tempfile.TemporaryDirectory(prefix="wiki-sync-eval-") as td:
        home = Path(td)
        skills = home / "skills"
        skills.mkdir()
        shutil.copytree(REPO_ROOT / ".codex" / "skills" / "wiki-export", skills / "wiki-export")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(home)

        check_proc = run([sys.executable, str(SYNC), "--check"], cwd=REPO_ROOT, env=env)
        remove_proc = run([sys.executable, str(SYNC), "--remove-global"], cwd=REPO_ROOT, env=env)
        check(
            "sync-removes-identical-global-duplicate",
            check_proc.returncode == 1 and remove_proc.returncode == 0 and not (skills / "wiki-export").exists(),
            check_proc.stdout + check_proc.stderr + remove_proc.stdout + remove_proc.stderr,
        )

    with tempfile.TemporaryDirectory(prefix="wiki-sync-eval-") as td:
        home = Path(td)
        skills = home / "skills"
        skills.mkdir()
        shutil.copytree(REPO_ROOT / ".codex" / "skills" / "wiki-ingest", skills / "wiki-ingest")
        (skills / "wiki-ingest" / "local.txt").write_text("local change\n", encoding="utf-8")
        env = os.environ.copy()
        env["CODEX_HOME"] = str(home)

        remove_proc = run([sys.executable, str(SYNC), "--remove-global"], cwd=REPO_ROOT, env=env)
        check(
            "sync-refuses-divergent-global-skill",
            remove_proc.returncode == 1 and (skills / "wiki-ingest" / "local.txt").exists(),
            remove_proc.stdout + remove_proc.stderr,
        )


def test_promote_and_capture_validator() -> None:
    with tempfile.TemporaryDirectory(prefix="wiki-promote-eval-") as td:
        ledger = Path(td) / "capture-runs.jsonl"
        ledger.write_text(schema_line(CAPTURE_LEDGER), encoding="utf-8")
        base = [
            sys.executable,
            str(PROMOTE),
            "eval reusable artifact",
            "--trigger",
            "reusable_distinction",
            "--primary-home",
            "wiki/concepts/eval-artifact.md",
            "--pages-touched",
            "wiki/concepts/eval-artifact.md",
            "--approval-ledger",
            str(ledger),
        ]

        audit = run(base, cwd=REPO_ROOT)
        check(
            "promote-audit-is-read-only",
            audit.returncode == 0 and "Mode: audit-only" in audit.stdout and "Writes files: false" in audit.stdout
            and len(ledger.read_text(encoding="utf-8").splitlines()) == 1,
            audit.stdout + audit.stderr,
        )

        unapproved = run([*base, "--apply"], cwd=REPO_ROOT)
        check(
            "promote-apply-requires-approval",
            unapproved.returncode == 2 and "APPROVAL REQUIRED" in unapproved.stdout
            and len(ledger.read_text(encoding="utf-8").splitlines()) == 1,
            unapproved.stdout + unapproved.stderr,
        )

        approved = run([*base, "--apply", "--approved"], cwd=REPO_ROOT)
        validated = run([sys.executable, str(VALIDATE_CAPTURE), str(ledger)], cwd=REPO_ROOT)
        check(
            "promote-approved-ledger-validates",
            approved.returncode == 0 and validated.returncode == 0 and "1 approved record" in validated.stdout,
            approved.stdout + approved.stderr + validated.stdout + validated.stderr,
        )

        bad = Path(td) / "bad-capture-runs.jsonl"
        record = json.loads(ledger.read_text(encoding="utf-8").splitlines()[1])
        record["run_id"] = "0000000000000000"
        bad.write_text(schema_line(CAPTURE_LEDGER) + json.dumps(record) + "\n", encoding="utf-8")
        bad_result = run([sys.executable, str(VALIDATE_CAPTURE), str(bad)], cwd=REPO_ROOT)
        check("capture-validator-rejects-bad-approved-record", bad_result.returncode == 1, bad_result.stdout + bad_result.stderr)


def test_synthesis_validator() -> None:
    with tempfile.TemporaryDirectory(prefix="wiki-synthesis-eval-") as td:
        ledger = Path(td) / "synthesis-runs.jsonl"
        ledger.write_text(schema_line(SYNTHESIS_LEDGER), encoding="utf-8")
        gate = run(
            [
                sys.executable,
                str(SYNTHESIS_GATE),
                "--artifact",
                "eval synthesis",
                "--drafts",
                "wiki/primer.md eval row",
                "--pages-touched",
                "wiki/primer.md,wiki/synthesis.md,wiki/log.md",
                "--approval-ledger",
                str(ledger),
                "--approved",
            ],
            cwd=REPO_ROOT,
        )
        validated = run([sys.executable, str(VALIDATE_SYNTHESIS), str(ledger)], cwd=REPO_ROOT)
        check(
            "synthesis-approved-ledger-validates",
            gate.returncode == 0 and validated.returncode == 0 and "1 approved record" in validated.stdout,
            gate.stdout + gate.stderr + validated.stdout + validated.stderr,
        )

        bad = Path(td) / "bad-synthesis-runs.jsonl"
        lines = ledger.read_text(encoding="utf-8").splitlines()
        schema = lines[0]
        record = json.loads(lines[1])
        record["ledger_update_required"] = False
        bad.write_text(schema + "\n" + json.dumps(record) + "\n", encoding="utf-8")
        bad_result = run([sys.executable, str(VALIDATE_SYNTHESIS), str(bad)], cwd=REPO_ROOT)
        check("synthesis-validator-rejects-bad-approved-record", bad_result.returncode == 1, bad_result.stdout + bad_result.stderr)


test_export_contract()
test_sync_codex_skills()
test_promote_and_capture_validator()
test_synthesis_validator()

print()
failed = [name for name, ok in results if not ok]
print(f"Summary: {len(results) - len(failed)} passed, {len(failed)} failed")
sys.exit(1 if failed else 0)
