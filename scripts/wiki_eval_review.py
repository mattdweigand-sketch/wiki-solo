#!/usr/bin/env python3
"""Regression eval for review_due.py, plus the live review-due status.

Guards that the review loop surfaces an overdue page, skips a not-yet-due one,
and ignores pages with no review_by, so the date logic cannot go vacuous. Then
prints the live status. Exits non-zero only if the regression fails; a live
review backlog is informational.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
SCRIPT = REPO_ROOT / "scripts" / "review_due.py"

from eval_lib import Results, page  # noqa: E402  (after sys.path insert)


results = Results()
with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "wiki"
    (root / "concepts").mkdir(parents=True)
    (root / "concepts" / "overdue.md").write_text(page(extra="review_by: 2026-05-01\n"))
    (root / "concepts" / "future.md").write_text(page(extra="review_by: 2026-12-01\n"))
    (root / "concepts" / "none.md").write_text(page())
    # Shape-valid but impossible date: must be flagged 'Invalid review_by' and NOT
    # counted as due (guards the bad-collection branch, review_due.py:55-62).
    (root / "concepts" / "bad.md").write_text(page(extra="review_by: 2026-13-99\n"))
    # review_by exactly == today: the boundary is inclusive (review_by <= today),
    # so this page IS surfaced (guards review_due.py:63).
    (root / "concepts" / "today.md").write_text(page(extra="review_by: 2026-06-16\n"))
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--today", "2026-06-16"],
        text=True, capture_output=True,
    )
    out = proc.stdout
    checks = [
        ("surfaces-overdue", proc.returncode == 0 and "concepts/overdue.md" in out),
        ("skips-future", "concepts/future.md" not in out),
        ("ignores-no-review-by", "concepts/none.md" not in out),
        ("counts-two-due", "due as of 2026-06-16: 2 page" in out),
        ("flags-invalid-review-by",
         "Invalid review_by values" in out and "concepts/bad.md" in out),
        ("invalid-not-counted-due", "concepts/bad.md: " in out
         and "concepts/bad.md  (review_by" not in out),
        ("surfaces-review-by-today", "concepts/today.md" in out),
    ]
    for name, ok in checks:
        results.record(name, ok, "stdout: " + out.replace("\n", " | "))

print()
print("-- live review-due --")
subprocess.run([sys.executable, str(SCRIPT)], check=False)

sys.exit(results.finish())
