#!/usr/bin/env python3
"""List wiki pages whose dated prediction or decision is due for outcome review.

A page opts into the grading loop by adding `review_by: YYYY-MM-DD` to its
frontmatter. This surfaces every page whose review_by is on or before today, so
the highest-stakes predictions and decisions get graded against what actually
happened instead of standing on self-assessed confidence forever.

The script is deterministic and surfaces only: recording the realized outcome
and adjusting confidence is a human judgment, performed via
workflows/maintenance/review.md, which then advances or clears review_by so the
page leaves this list until its next checkpoint. Lint validates the date format;
this report is informational and always exits 0.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from _wiki_parse import frontmatter_block


REVIEW_BY_RE = re.compile(r"^review_by:\s*(\S+)\s*$", re.M)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def entity_pages(root: Path):
    return sorted(p for p in root.rglob("*.md")
                  if len(p.relative_to(root).parts) == 2)


def collect(root: Path, today: date):
    due, bad = [], []
    for p in entity_pages(root):
        try:
            fm = frontmatter_block(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        m = REVIEW_BY_RE.search(fm)
        if not m:
            continue
        rel = str(p.relative_to(root))
        val = m.group(1)
        if not DATE_RE.match(val):
            bad.append((rel, val))
            continue
        try:
            review_by = date.fromisoformat(val)
        except ValueError:  # shape-valid but impossible date, e.g. 2026-13-99
            bad.append((rel, val))
            continue
        if review_by <= today:
            due.append(((today - review_by).days, rel, val))
    due.sort(reverse=True)
    return due, bad


def main() -> int:
    ap = argparse.ArgumentParser(description="List pages due for outcome review.")
    ap.add_argument("--root", default="wiki", help="Wiki root to scan.")
    ap.add_argument("--today", default=None, help="Override today (YYYY-MM-DD), for tests.")
    args = ap.parse_args()
    today = date.fromisoformat(args.today) if args.today else date.today()

    due, bad = collect(Path(args.root), today)
    print(f"Outcome review due as of {today.isoformat()}: {len(due)} page(s)")
    for overdue, rel, val in due:
        print(f"  {rel}  (review_by {val}, {overdue} day(s) overdue)")
    if bad:
        print(f"Invalid review_by values (lint also flags these): {len(bad)}")
        for rel, val in bad:
            print(f"  {rel}: '{val}'")
    return 0  # informational: a review backlog is not a failure


if __name__ == "__main__":
    sys.exit(main())
