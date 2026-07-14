#!/usr/bin/env python3
"""Rebuild generated ``## Referenced by`` sections for wiki entity pages.

The rebuild is deliberately planned from one immutable UTF-8 snapshot. Every
page is read and transformed before the first write, so unreadable input or a
failed transformation cannot leave a predictable partial rebuild. Generated
sections and code spans never feed the reverse link graph back into itself.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from _wiki_parse import LINK_RE, authored_link_view, get_entity_pages, section_spans


WIKI_ROOT = Path("wiki")


class RebuildError(RuntimeError):
    """A controlled read, transform, or write failure."""


def load_page_texts(all_pages: list[Path]) -> dict[Path, str]:
    """Read every target exactly once as UTF-8, before any page is written."""
    snapshot: dict[Path, str] = {}
    for page in all_pages:
        try:
            snapshot[page] = page.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RebuildError(f"cannot read {page} as UTF-8: {exc}") from exc
    return snapshot


def authored_texts(snapshot: dict[Path, str]) -> dict[Path, str]:
    """Return pure link-scan views with code and generated regions masked."""
    return {page: authored_link_view(text) for page, text in snapshot.items()}


def build_reverse_index(
    scan_texts: dict[Path, str], wiki_root: Path = WIKI_ROOT
) -> dict[str, dict[str, list[Path]]]:
    """Build ``slug -> directory label -> source pages`` in one pure pass."""
    index: dict[str, dict[str, list[Path]]] = {}
    for page, text in scan_texts.items():
        parts = page.relative_to(wiki_root).parts
        directory_label = parts[0] if len(parts) > 1 else "wiki root"
        for slug in set(LINK_RE.findall(text)):
            index.setdefault(slug, {}).setdefault(directory_label, []).append(page)
    return index


def find_references(
    slug: str,
    reverse_index: dict[str, dict[str, list[Path]]],
    target_path: Path,
) -> dict[str, list[str]]:
    """Renderable inbound references, excluding a target's self-reference."""
    refs: defaultdict[str, list[str]] = defaultdict(list)
    for directory_label, pages in reverse_index.get(slug, {}).items():
        for page in pages:
            if page != target_path:
                refs[directory_label].append(f"[[{page.stem}]]")
    return {label: links for label, links in refs.items() if links}


def build_referenced_by_block(refs: dict[str, list[str]]) -> str:
    """Render one canonical generated section."""
    if not refs:
        return "## Referenced by\n\n_No inbound links yet._\n"
    lines = ["## Referenced by\n"]
    for directory_label in sorted(refs):
        links = ", ".join(sorted(refs[directory_label]))
        lines.append(f"\n**{directory_label}/**  {links}\n")
    return "\n".join(lines) + "\n"


def render_page(authored_page: str, new_block: str) -> str:
    """Purely replace, collapse, or insert the generated section in one page."""
    generated = section_spans(authored_page, "Referenced by")
    if generated:
        parts: list[str] = []
        last = 0
        for index, (start, end) in enumerate(generated):
            parts.append(authored_page[last:start])
            if index == 0:
                parts.append(new_block.rstrip("\n") + "\n")
            last = end
        parts.append(authored_page[last:])
        rendered = "".join(parts)
        if not rendered.endswith("\n"):
            rendered += "\n"
        return rendered

    related = section_spans(authored_page, "Related pages")
    related_start = related[0][0] if related else None
    if related_start == 0:
        return new_block.rstrip("\n") + "\n" + authored_page
    if related_start is not None:
        prefix = authored_page[:related_start].rstrip("\n")
        return (
            prefix
            + "\n\n"
            + new_block.rstrip("\n")
            + "\n"
            + authored_page[related_start:]
        )
    return authored_page.rstrip("\n") + "\n\n" + new_block.rstrip("\n") + "\n"


def build_plan(
    snapshot: dict[Path, str], wiki_root: Path = WIKI_ROOT
) -> tuple[dict[Path, str], dict[Path, int]]:
    """Compute changed outputs and inbound counts from the original snapshot."""
    reverse_index = build_reverse_index(authored_texts(snapshot), wiki_root)
    changed: dict[Path, str] = {}
    inbound_counts: dict[Path, int] = {}
    for page, original in snapshot.items():
        refs = find_references(page.stem, reverse_index, page)
        inbound_counts[page] = sum(len(links) for links in refs.values())
        rendered = render_page(original, build_referenced_by_block(refs))
        if rendered != original:
            changed[page] = rendered
    return changed, inbound_counts


def apply_plan(changed_only: dict[Path, str]) -> None:
    """Write only changed outputs after the complete plan has succeeded."""
    for page, text in changed_only.items():
        try:
            page.write_text(text, encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise RebuildError(f"cannot write {page}: {exc}") from exc


def main() -> int:
    if not WIKI_ROOT.exists():
        print(
            "Error: 'wiki/' directory not found. Run this script from the repo root.\n"
            f"  Current directory: {Path.cwd()}",
            file=sys.stderr,
        )
        return 1

    all_pages = get_entity_pages(WIKI_ROOT)
    print(f"Found {len(all_pages)} entity pages.")
    try:
        snapshot = load_page_texts(all_pages)
        changed, inbound_counts = build_plan(snapshot)
        apply_plan(changed)
    except (RebuildError, ValueError) as exc:
        print(f"Error: backlink rebuild failed: {exc}", file=sys.stderr)
        return 1

    for page in all_pages:
        print(f"  {page}  ({inbound_counts[page]} inbound links)")
    print(f"\nDone. Processed {len(all_pages)} pages; changed {len(changed)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
