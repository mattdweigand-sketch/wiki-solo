#!/usr/bin/env python3
"""Regression eval for sync_codex_skills.py --remove-global safety (WP-5 #2).

--remove-global must delete ONLY global ~/.codex/skills/wiki-* installs that are
byte-identical to the repo source, and must report (not delete) any divergent
global copy, so a customized global wrapper is never destroyed silently. This
suite proves both halves against a fully isolated temp CODEX_HOME:

  - one global skill copied byte-identical from the repo source, and
  - one global skill copied then mutated so it differs from the source.

Then it runs the script with CODEX_HOME pointed at the temp dir (never the real
~/.codex) and asserts:

  1. --remove-global --dry-run names the identical install as a removal target,
     reports the divergent install as skipped, and deletes NOTHING.
  2. --remove-global (no dry-run) removes ONLY the identical install and leaves
     the divergent one in place.

Regression caught: if --remove-global is reverted to delete every existing
global wiki-* directory (the unsafe behavior), the divergent install disappears
and assertions below fail. Stdlib-only; isolated to the temp dir.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
SCRIPT = REPO_ROOT / "scripts" / "sync_codex_skills.py"
SOURCE_ROOT = REPO_ROOT / ".codex" / "skills"

from eval_lib import Results  # noqa: E402  (after sys.path insert)

# Two real tracked wiki-* skills; one will be installed identical, one divergent.
IDENTICAL_SKILL = "wiki-lint"
DIVERGENT_SKILL = "wiki-eval"

results = Results()


def run_remove(codex_home: Path, *extra: str) -> subprocess.CompletedProcess:
    """Run sync_codex_skills.py --remove-global with CODEX_HOME isolated.

    A copy of the current environment is used so PATH etc. survive, but
    CODEX_HOME is overridden to the temp dir so the real ~/.codex is never read
    or written.
    """
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--remove-global", *extra],
        text=True, capture_output=True, env=env, check=False,
    )


with tempfile.TemporaryDirectory(prefix="wiki-codex-remove-eval-") as td:
    codex_home = Path(td) / ".codex"
    target_root = codex_home / "skills"
    target_root.mkdir(parents=True)

    identical_target = target_root / IDENTICAL_SKILL
    divergent_target = target_root / DIVERGENT_SKILL

    # Byte-identical install: a straight copytree of the repo source tree.
    shutil.copytree(SOURCE_ROOT / IDENTICAL_SKILL, identical_target)
    # Divergent install: copy then append a byte so it no longer matches source.
    shutil.copytree(SOURCE_ROOT / DIVERGENT_SKILL, divergent_target)
    divergent_skill_md = divergent_target / "SKILL.md"
    divergent_skill_md.write_text(
        divergent_skill_md.read_text(encoding="utf-8") + "\nlocal customization\n",
        encoding="utf-8",
    )

    # --- 1. dry run: reports both, deletes nothing ---
    dry = run_remove(codex_home, "--dry-run")
    dry_out = dry.stdout + dry.stderr
    results.record(
        "dry-run-targets-identical",
        str(identical_target) in dry_out and "would remove" in dry_out.lower(),
        f"exit {dry.returncode}; out: {dry_out!r}",
    )
    results.record(
        "dry-run-reports-divergent-skipped",
        str(divergent_target) in dry_out and "divergent" in dry_out.lower(),
        f"exit {dry.returncode}; out: {dry_out!r}",
    )
    results.record(
        "dry-run-deletes-nothing",
        identical_target.exists() and divergent_target.exists(),
        "dry run must not delete either install",
    )

    # --- 2. real run: removes ONLY the identical install ---
    real = run_remove(codex_home)
    real_out = real.stdout + real.stderr
    results.record(
        "real-run-removes-identical",
        not identical_target.exists(),
        f"identical install should be removed; out: {real_out!r}",
    )
    results.record(
        "real-run-keeps-divergent",
        divergent_target.exists(),
        f"divergent install must be left in place; out: {real_out!r}",
    )
    results.record(
        "real-run-reports-divergent-skip",
        str(divergent_target) in real_out and "divergent" in real_out.lower(),
        f"out: {real_out!r}",
    )
    # The divergent file content must be untouched (not silently reconciled).
    results.record(
        "real-run-divergent-content-untouched",
        divergent_target.exists()
        and "local customization" in (divergent_target / "SKILL.md").read_text(encoding="utf-8"),
        "divergent SKILL.md content changed",
    )

sys.exit(results.finish())
