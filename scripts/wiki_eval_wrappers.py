#!/usr/bin/env python3
"""Regression eval for check_wrapper_parity.py.

Negative controls: a minimal parity-clean fixture tree is seeded with each
problem class the checker claims to catch (missing skill, extra wiki-* wrapper,
two-script-ref wrapper, numbered-step wrapper, dangling workflows/*.md
reference) and each must fail with the corresponding message, so the checker
cannot silently go vacuous. Positive controls: the clean fixture and the live
tracked wrapper surfaces both pass.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from check_wrapper_parity import EXPECTED_SKILLS, wrapper_parity_problems
from eval_lib import Results

results = Results()


def build_clean_tree(root: Path) -> None:
    """A minimal parity-clean wrapper tree: every EXPECTED_SKILLS name on both
    surfaces, one script hint at most, no numbered steps, one real workflow ref."""
    (root / "workflows" / "maintenance").mkdir(parents=True)
    (root / "workflows" / "maintenance" / "lint.md").write_text(
        "# fixture workflow\n", encoding="utf-8")
    commands = root / ".claude" / "commands"
    commands.mkdir(parents=True)
    for name in EXPECTED_SKILLS:
        body = (f"# {name}\n\nThin pointer: follow "
                "workflows/maintenance/lint.md in this repo.\n")
        (commands / f"{name}.md").write_text(body, encoding="utf-8")
        skill = root / ".codex" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(body, encoding="utf-8")


def case(name, mutate, expect_fragment):
    """Build the clean tree, apply `mutate(root)`, and assert on the problems:
    expect_fragment=None asserts a clean run; otherwise some problem line must
    contain the fragment."""
    with tempfile.TemporaryDirectory(prefix="wiki-parity-eval-") as td:
        root = Path(td)
        build_clean_tree(root)
        if mutate:
            mutate(root)
        problems = wrapper_parity_problems(repo_root=root)
        if expect_fragment is None:
            ok = not problems
            detail = "unexpected problems: " + "; ".join(problems)
        else:
            ok = any(expect_fragment in p for p in problems)
            detail = f"expected {expect_fragment!r} in problems: {problems!r}"
        results.record(name, ok, detail)


case("clean-fixture-passes", None, None)
case("missing-skill-fires",
     lambda r: shutil.rmtree(r / ".codex" / "skills" / "wiki-lint"),
     "missing wrapper for wiki-lint")
case("missing-wrapper-file-fires",
     lambda r: (r / ".codex" / "skills" / "wiki-lint" / "SKILL.md").unlink(),
     "missing wrapper file")
case("extra-wrapper-fires",
     lambda r: (r / ".claude" / "commands" / "wiki-extra.md").write_text(
         "# stray\n", encoding="utf-8"),
     "unexpected wiki-* wrapper wiki-extra")
case("two-script-refs-fire",
     lambda r: (r / ".claude" / "commands" / "wiki-lint.md").write_text(
         "# wiki-lint\n\nRun scripts/lint.py and then scripts/wiki_eval.py.\n",
         encoding="utf-8"),
     "scripts/*.py references")
case("numbered-steps-fire",
     lambda r: (r / ".codex" / "skills" / "wiki-eval" / "SKILL.md").write_text(
         "# wiki-eval\n\n1. do the first thing\n2. do the second thing\n",
         encoding="utf-8"),
     "numbered-step list")
case("dangling-workflow-ref-fires",
     lambda r: (r / ".claude" / "commands" / "wiki-export.md").write_text(
         "# wiki-export\n\nFollow workflows/maintenance/does-not-exist.md.\n",
         encoding="utf-8"),
     "workflow path workflows/maintenance/does-not-exist.md does not exist")

# Positive control on the real repo: the live tracked surfaces are in parity.
live_problems = wrapper_parity_problems()
results.record("live-surfaces-pass", not live_problems,
               "problems: " + "; ".join(live_problems))

sys.exit(results.finish())
