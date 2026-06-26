#!/usr/bin/env python3
"""Regression eval for rebuild_referenced_by.py.

Guards the two invariants of the generated inbound-link graph:

1. Only authored links count. A one-way authored link must never become a
   two-way edge by way of a previously generated "## Referenced by" block
   (the fixture seeds a poisoned block and expects it cleaned).
2. Idempotency. A second rebuild over already-correct pages is a byte-level
   no-op.

Runs against the fixture mini-wiki in scripts/fixtures/wiki-rebuild/, copied
into a system temp directory. Writes nothing inside the repo.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from eval_lib import Results

REPO_ROOT = Path(__file__).resolve().parents[1]
REBUILD_SCRIPT = REPO_ROOT / "scripts" / "rebuild_referenced_by.py"
FIXTURE_WIKI = REPO_ROOT / "scripts" / "fixtures" / "wiki-rebuild" / "wiki"

SECTION_RE = re.compile(r"## Referenced by\n.*?(?=\n## |\Z)", re.DOTALL)


def read_tree(root: Path) -> dict:
    return {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*.md"))
    }


def referenced_by_section(text: str) -> str:
    m = SECTION_RE.search(text)
    return m.group(0) if m else ""


def main() -> int:
    results = Results()
    check = results.record

    tmp = Path(tempfile.mkdtemp(prefix="wiki-rebuild-eval-"))
    try:
        shutil.copytree(FIXTURE_WIKI, tmp / "wiki")
        run = lambda: subprocess.run(
            [sys.executable, str(REBUILD_SCRIPT)],
            cwd=tmp,
            capture_output=True,
            text=True,
        )

        first = run()
        check("first-rebuild-exits-zero", first.returncode == 0, first.stderr.strip())
        after_first = read_tree(tmp / "wiki")

        alpha = after_first.get("concepts/alpha.md", "")
        beta = after_first.get("concepts/beta.md", "")
        delta = after_first.get("concepts/delta.md", "")
        gamma = after_first.get("sources/gamma.md", "")

        alpha_sec = referenced_by_section(alpha)
        check(
            "phantom-edge-removed",
            "[[beta]]" not in alpha_sec,
            "alpha's seeded poisoned block survived: one-way link became two-way",
        )
        check(
            "authored-inbound-kept",
            "[[gamma]]" in alpha_sec and "[[delta]]" in alpha_sec,
            f"alpha section: {alpha_sec!r}",
        )
        check(
            "stale-section-refreshed",
            "[[alpha]]" in referenced_by_section(beta),
            "beta's stale 'no inbound' block was not refreshed",
        )
        check(
            "no-inbound-marker",
            "_No inbound links yet._" in referenced_by_section(gamma),
            f"gamma section: {referenced_by_section(gamma)!r}",
        )
        check(
            "insertion-before-related",
            "## Referenced by" in gamma
            and gamma.index("## Referenced by") < gamma.index("## Related pages"),
            "gamma's new section was not inserted before Related pages",
        )
        check(
            "byte0-related-prepended",
            delta.startswith("## Referenced by"),
            "delta (file starting with '## Related pages') was not prepended",
        )

        second = run()
        check("second-rebuild-exits-zero", second.returncode == 0, second.stderr.strip())
        after_second = read_tree(tmp / "wiki")
        changed = sorted(
            k for k in after_first if after_first[k] != after_second.get(k)
        )
        check(
            "idempotent-second-pass",
            after_first == after_second,
            f"files changed on second rebuild: {changed}",
        )

        # last (it mutates state): a hand edit that duplicated the generated
        # section must collapse back to exactly one
        alpha_path = tmp / "wiki" / "concepts" / "alpha.md"
        alpha_path.write_text(
            alpha_path.read_text() + "\n## Referenced by\n\nstale duplicate\n"
        )
        dup_run = run()
        collapsed = alpha_path.read_text()
        check(
            "duplicate-sections-collapsed",
            dup_run.returncode == 0 and collapsed.count("## Referenced by") == 1,
            f"{collapsed.count('## Referenced by')} sections remain after rebuild",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return results.finish()


if __name__ == "__main__":
    sys.exit(main())
