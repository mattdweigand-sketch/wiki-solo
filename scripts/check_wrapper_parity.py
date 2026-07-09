#!/usr/bin/env python3
"""Verify the two tracked wrapper surfaces stay thin and in parity.

The live convenience surfaces are .claude/commands/wiki-*.md and
.codex/skills/wiki-*/SKILL.md. Both must cover the same EXPECTED_SKILLS names,
and every wrapper must stay a thin pointer: at most one scripts/*.py command
hint, no numbered-step procedure (canonical behavior lives in workflows/, per
the wrapper contract in workflows/maintenance/eval.md), and every
workflows/*.md path it names must exist. For shortcuts with a single canonical
task workflow, the wrapper must also name that workflow so a command cannot
silently route to the wrong existing file.

Run directly, or via the wrapper-parity suite in scripts/wiki_eval.py (which
also runs seeded negative cases from scripts/wiki_eval_wrappers.py):
    python3 scripts/check_wrapper_parity.py

(This replaces sync_codex_skills.py. The old --check/--remove-global modes
existed to clean up pre-repo-local global installs under ~/.codex/skills; that
one-time migration is complete and the machinery was retired 2026-07-01.)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = (
    "wiki-capture",
    "wiki-eval",
    "wiki-export",
    "wiki-ingest",
    "wiki-lint",
    "wiki-promote",
    "wiki-swarm",
    "wiki-synthesize",
)

EXPECTED_WORKFLOW_REFS = {
    "wiki-capture": ("workflows/maintenance/capture.md",),
    "wiki-eval": ("workflows/maintenance/eval.md",),
    "wiki-export": ("workflows/maintenance/export.md",),
    "wiki-ingest": ("workflows/ingest/CONTEXT.md",),
    "wiki-lint": ("workflows/maintenance/lint.md",),
    "wiki-promote": ("workflows/maintenance/artifact-promotion.md",),
    "wiki-synthesize": ("workflows/maintenance/synthesize.md",),
}

# The two live tracked wrapper surfaces, relative to the repo root so the
# checker can run against fixture trees too. Each must cover the same
# EXPECTED_SKILLS names. .claude/commands holds one .md per skill; .codex/skills
# holds one <skill>/SKILL.md per skill.
WRAPPER_SURFACES = (
    ("claude-commands", Path(".claude") / "commands", "{name}.md"),
    ("codex-skills", Path(".codex") / "skills", "{name}/SKILL.md"),
)

# Thin-wrapper rule (workflows/maintenance/eval.md): a wrapper may carry at most
# one canonical command hint and no multi-step procedure. A second scripts/*.py
# reference or a numbered-step list means procedure has leaked into the wrapper.
SCRIPT_REF_RE = re.compile(r"scripts/[A-Za-z0-9_./-]*\.py")
NUMBERED_STEP_RE = re.compile(r"^\s*[0-9]+\.\s")
# A wrapper is a pointer, so what it points at must exist, and common shortcuts
# must point at their canonical task workflow rather than another existing task.
WORKFLOW_REF_RE = re.compile(r"workflows/[A-Za-z0-9_./-]*\.md")


def wrapper_parity_problems(repo_root: Path = REPO_ROOT) -> list[str]:
    """Check the live tracked wrapper surfaces stay thin and mutually consistent.

    Returns a list of human-readable problems (empty when all surfaces are in
    sync). Catches:
      - a surface that does not cover all EXPECTED_SKILLS names (drop/add drift),
      - a surface that carries an extra wiki-* wrapper not in EXPECTED_SKILLS,
      - a wrapper body with more than one scripts/*.py reference or a
        numbered-step list (procedure leaking into a thin pointer),
      - a wrapper body naming a workflows/*.md path that does not exist
        (a pointer at nothing).
      - a wrapper body missing the canonical workflow route for its wiki-*
        shortcut (a pointer at the wrong existing workflow).
    """
    problems: list[str] = []
    expected = set(EXPECTED_SKILLS)

    for label, rel_root, pattern in WRAPPER_SURFACES:
        root = repo_root / rel_root
        if not root.exists():
            problems.append(f"{label}: wrapper surface missing: {root}")
            continue

        if pattern.endswith("/SKILL.md"):
            present = {p.name for p in root.iterdir() if p.is_dir() and p.name.startswith("wiki-")}
        else:
            present = {p.stem for p in root.glob("wiki-*.md")}

        for missing in sorted(expected - present):
            problems.append(f"{label}: missing wrapper for {missing}")
        for extra in sorted(present - expected):
            problems.append(f"{label}: unexpected wiki-* wrapper {extra}")

        for name in sorted(expected & present):
            wrapper = root / pattern.format(name=name)
            if not wrapper.exists():
                problems.append(f"{label}: missing wrapper file {wrapper}")
                continue
            text = wrapper.read_text(encoding="utf-8")
            script_refs = SCRIPT_REF_RE.findall(text)
            if len(script_refs) > 1:
                problems.append(
                    f"{label}/{name}: {len(script_refs)} scripts/*.py references "
                    f"(thin wrappers allow at most one canonical command hint): "
                    f"{', '.join(sorted(set(script_refs)))}"
                )
            step_lines = [
                line for line in text.splitlines() if NUMBERED_STEP_RE.match(line)
            ]
            if step_lines:
                problems.append(
                    f"{label}/{name}: wrapper contains a numbered-step list "
                    f"(procedure belongs only in workflows/): {step_lines[0].strip()!r}"
                )
            for ref in sorted(set(WORKFLOW_REF_RE.findall(text))):
                if not (repo_root / ref).is_file():
                    problems.append(
                        f"{label}/{name}: workflow path {ref} does not exist"
                    )
            for ref in EXPECTED_WORKFLOW_REFS.get(name, ()):
                if ref not in text:
                    problems.append(
                        f"{label}/{name}: missing required workflow route {ref}"
                    )

    return problems


def main() -> int:
    argparse.ArgumentParser(
        description="Verify the .claude/commands and .codex/skills wrapper "
        "surfaces cover the same wiki-* names and stay thin.",
    ).parse_args()
    problems = wrapper_parity_problems()
    if problems:
        print("Wrapper-parity problems found:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("Wrapper surfaces are in parity and thin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
