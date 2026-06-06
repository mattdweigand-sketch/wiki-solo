#!/usr/bin/env python3
"""
Rebuild "## Referenced by" sections across all wiki entity pages.
For each entity page, greps all other pages for [[slug]] mentions,
groups by directory, and inserts/replaces the section before "## Related pages".
"""
import re
from pathlib import Path
from collections import defaultdict

WIKI_ROOT = Path("wiki")
META_PAGES = {
    "index", "log", "overview", "glossary", "primer", "domain",
    "sourcing-queue", "contradictions", "design-notes", "schema",
}
META_DIRS = {"style"}


def get_entity_pages():
    pages = []
    for p in WIKI_ROOT.rglob("*.md"):
        parts = p.relative_to(WIKI_ROOT).parts
        if len(parts) == 1:
            if p.stem not in META_PAGES:
                pages.append(p)
        elif len(parts) == 2:
            if parts[0] not in META_DIRS:
                pages.append(p)
    return sorted(pages)


def find_references(slug, all_pages, target_path):
    """Return dict of {directory_label: [link_text, ...]} for pages mentioning [[slug]] or [[dir/slug]]."""
    # Match bare [[slug]], path-qualified [[dir/slug]], or aliased [[dir/slug|text]]
    pattern = re.compile(
        r'\[\[(?:[^/\]|]+/)?' + re.escape(slug) + r'(?:\|[^\]]+)?\]\]'
    )
    refs = defaultdict(list)
    for p in all_pages:
        if p == target_path:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if pattern.search(text):
            parts = p.relative_to(WIKI_ROOT).parts
            dir_label = parts[0] if len(parts) > 1 else "wiki root"
            refs[dir_label].append(f"[[{p.stem}]]")
    return refs


def build_referenced_by_block(refs):
    if not refs:
        return "## Referenced by\n\n_No inbound links yet._\n"
    lines = ["## Referenced by\n"]
    for dir_label in sorted(refs):
        links = ", ".join(sorted(refs[dir_label]))
        lines.append(f"\n**{dir_label}/**  {links}\n")
    return "\n".join(lines) + "\n"


def update_page(path, new_block):
    text = path.read_text(encoding="utf-8")

    # Replace existing "## Referenced by" section (up to next ## heading or EOF)
    referenced_by_re = re.compile(
        r'## Referenced by\n.*?(?=\n## |\Z)', re.DOTALL
    )
    if referenced_by_re.search(text):
        new_text = referenced_by_re.sub(new_block.rstrip('\n'), text, count=1)
    else:
        # Insert before "## Related pages" if it exists, else append
        related_re = re.compile(r'(?=\n## Related pages)', re.MULTILINE)
        if related_re.search(text):
            new_text = related_re.sub('\n\n' + new_block.rstrip('\n'), text, count=1)
        else:
            new_text = text.rstrip('\n') + '\n\n' + new_block.rstrip('\n') + '\n'

    path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    all_pages = get_entity_pages()
    print(f"Found {len(all_pages)} entity pages.")
    for page in all_pages:
        slug = page.stem
        refs = find_references(slug, all_pages, page)
        block = build_referenced_by_block(refs)
        update_page(page, block)
        inbound = sum(len(v) for v in refs.values())
        print(f"  {page}  ({inbound} inbound links)")
    print(f"\nDone. Processed {len(all_pages)} pages.")
