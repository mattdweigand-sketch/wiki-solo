#!/usr/bin/env python3
"""Regression eval for stale_text_sweep.py.

Guards the read-only stale-text sweep helper: zero-hit and multi-hit behavior,
log-proof JSON arrays, and no content edits to searched files.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
SCRIPT = REPO_ROOT / "scripts" / "stale_text_sweep.py"

from eval_lib import Results  # noqa: E402
from lint import validate_stale_sweep_proof  # noqa: E402


def run_helper(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def proof_line(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("Stale-text sweep:"):
            return line
    return ""


def proof_array(line: str, field: str) -> list[str] | None:
    match = re.search(rf"{field}=(\[.*?\])(?:;|$)", line)
    if not match:
        return None
    parsed = json.loads(match.group(1))
    return parsed if isinstance(parsed, list) else None


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


results = Results()
with tempfile.TemporaryDirectory(prefix="wiki-stale-sweep-eval-") as td:
    root = Path(td)
    wiki = root / "wiki"
    wiki.mkdir()
    (wiki / "alpha.md").write_text("Alpha page has no target phrase.\n")

    before = snapshot(wiki)
    proc = run_helper(root, "--phrase", "missing phrase", "--root", "wiki")
    after = snapshot(wiki)
    proof = proof_line(proc.stdout)
    results.record(
        "zero-hit-case",
        proc.returncode == 0
        and "Command: rg -n -i -- 'missing phrase' wiki" in proc.stdout
        and "Total hits: 0" in proc.stdout
        and "  none" in proc.stdout
        and "hit_count=0" in proof,
        "stdout: " + proc.stdout.replace("\n", " | "),
    )
    results.record(
        "zero-hit-read-only",
        before == after,
        f"before={before!r} after={after!r}",
    )

with tempfile.TemporaryDirectory(prefix="wiki-stale-sweep-eval-") as td:
    root = Path(td)
    wiki = root / "wiki"
    nested = wiki / "nested"
    nested.mkdir(parents=True)
    (wiki / "alpha.md").write_text(
        "Old claim appears once.\nNo match here.\nold claim appears twice.\n"
    )
    (nested / "beta.md").write_text("OLD CLAIM also appears here.\n")

    before = snapshot(wiki)
    proc = run_helper(
        root,
        "--phrase", "old claim",
        "--root", "wiki",
        "--pages-fixed", "wiki/alpha.md",
        "--historical-no-change-hit", "wiki/nested/beta.md:1",
    )
    after = snapshot(wiki)
    proof = proof_line(proc.stdout)
    commands = proof_array(proof, "commands")
    pages_fixed = proof_array(proof, "pages_fixed")
    historical = proof_array(proof, "historical_no_change_hits")

    results.record(
        "multi-hit-case",
        proc.returncode == 0
        and "Total hits: 3" in proc.stdout
        and "  wiki/alpha.md: 2" in proc.stdout
        and "  wiki/nested/beta.md: 1" in proc.stdout
        and "hit_count=3" in proof,
        "stdout: " + proc.stdout.replace("\n", " | "),
    )
    results.record(
        "proof-arrays-valid-json",
        validate_stale_sweep_proof(proof) is None
        and commands == ["rg -n -i -- 'old claim' wiki"]
        and pages_fixed == ["wiki/alpha.md"]
        and historical == ["wiki/nested/beta.md:1"],
        "proof: " + proof,
    )
    results.record(
        "multi-hit-read-only",
        before == after,
        f"before={before!r} after={after!r}",
    )

sys.exit(results.finish())
