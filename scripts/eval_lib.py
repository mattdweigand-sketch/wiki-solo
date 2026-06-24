#!/usr/bin/env python3
"""Shared boilerplate for the wiki_eval_*.py regression suites.

Every suite records named PASS/FAIL checks, prints a uniform
``Summary: N passed, M failed`` line, and exits 1 when anything failed. They also
repeatedly hand-roll the same wiki-page fixture frontmatter. This module owns
exactly that boilerplate so the suites cannot drift on result accounting or on
the minimal valid-page shape, while each suite keeps its own assertions local.

Intentionally NOT centralized here: per-suite ``run_case`` helpers (they differ
in how they invoke a script and which markers they assert) and the page bodies a
specific check needs. Suites that do not migrate cleanly keep their own helpers.
"""

from __future__ import annotations


class Results:
    """Collects (name, ok) check results and renders the standard summary.

    Usage:
        r = Results()
        r.record("some-check", condition, "detail shown only on failure")
        ...
        sys.exit(r.finish())

    ``record`` prints ``PASS <name>`` or ``FAIL <name>`` (plus the detail line on
    failure) immediately, matching the prior per-file behavior. ``finish`` prints
    the blank line + ``Summary: N passed, M failed`` and returns the exit code
    (1 if any check failed, else 0).
    """

    def __init__(self) -> None:
        self._results: list[tuple[str, bool]] = []

    def record(self, name: str, ok: bool, detail: str = "") -> None:
        self._results.append((name, bool(ok)))
        if ok:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}")
            if detail:
                print(f"  {detail}")

    @property
    def failed(self) -> list[str]:
        return [name for name, ok in self._results if not ok]

    def finish(self) -> int:
        failed = self.failed
        print()
        print(f"Summary: {len(self._results) - len(failed)} passed, {len(failed)} failed")
        return 1 if failed else 0


def frontmatter(
    *,
    title: str = "t",
    type: str = "concept",
    created: str = "2026-01-01",
    updated: str = "2026-01-01",
    sources: str = "[]",
    tags: str = "x",
    confidence: str = "medium",
    extra: str = "",
) -> str:
    """Render a minimal, lint-shaped YAML frontmatter block (with fences).

    ``tags`` is the inline comma-separated body of the ``tags: [...]`` list.
    ``extra`` is appended verbatim before the closing fence, for suite-specific
    keys such as ``review_by:`` or ``agent_use_cases:`` lines.
    """
    return (
        "---\n"
        f"title: {title}\n"
        f"type: {type}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"sources: {sources}\n"
        f"tags: [{tags}]\n"
        f"confidence: {confidence}\n"
        f"{extra}"
        "---\n"
    )


def page(*, body: str = "body\n", **frontmatter_kwargs: str) -> str:
    """A full fixture page: frontmatter (see ``frontmatter``) plus a body."""
    return frontmatter(**frontmatter_kwargs) + body
