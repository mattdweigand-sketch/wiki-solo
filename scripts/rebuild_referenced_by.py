#!/usr/bin/env python3
"""
Rebuild "## Referenced by" sections across all wiki entity pages.

For each entity page, scans every other entity page for [[slug]] mentions,
groups the inbound links by directory, and inserts/replaces a
"## Referenced by" section immediately before "## Related pages".

Vendor-neutral: stdlib only, no dependencies. Run from the repo root:
    python3 scripts/rebuild_referenced_by.py

Idempotent: re-running rewrites the generated sections in place and converges
on the first pass. Previously generated "## Referenced by" blocks are stripped
before scanning, so only authored links (body prose and "## Related pages")
count as references; generated output never feeds back into the graph. Meta
pages (index, log, glossary, etc.) are never targets and are not counted as
link sources, so the catalog/index does not create noise.
"""
import re
import sys
from pathlib import Path
from collections import defaultdict

WIKI_ROOT = Path("wiki")

if not WIKI_ROOT.exists():
    print(
        "Error: 'wiki/' directory not found. Run this script from the repo root.\n"
        f"  Current directory: {Path.cwd()}",
        file=sys.stderr,
    )
    sys.exit(1)

META_PAGES = {
    "index", "log", "overview", "glossary", "primer",
    "sourcing-queue", "contradictions", "design-notes", "SCHEMA", "synthesis",
    "domain",
}
META_DIRS = set()  # all wiki/ subfolders are entity types, style/ included


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


# A generated "## Referenced by" section runs to the next ## heading or EOF.
REFERENCED_BY_SECTION_RE = re.compile(r'## Referenced by\n.*?(?=\n## |\Z)', re.DOTALL)


def strip_referenced_by(text):
    """Remove generated "## Referenced by" sections so they never count as authored links."""
    return REFERENCED_BY_SECTION_RE.sub("", text)


def load_authored_texts(all_pages):
    """Read every page once and return {path: text-with-generated-sections-stripped}."""
    texts = {}
    for p in all_pages:
        try:
            texts[p] = strip_referenced_by(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return texts


def find_references(slug, authored_texts, target_path):
    """Return {directory_label: [link_text, ...]} for pages whose authored text mentions [[slug]]."""
    # Match bare [[slug]], path-qualified [[dir/slug]], or aliased [[dir/slug|text]]
    pattern = re.compile(
        r'\[\[(?:[^/\]|]+/)?' + re.escape(slug) + r'(?:\|[^\]]+)?\]\]'
    )
    refs = defaultdict(list)
    for p, text in authored_texts.items():
        if p == target_path:
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

    # Replace the first "## Referenced by" section (up to next ## heading or
    # EOF) and drop any duplicates a hand edit may have introduced.
    if REFERENCED_BY_SECTION_RE.search(text):
        replaced = [False]

        def _sub(m):
            if replaced[0]:
                return ""
            replaced[0] = True
            return new_block.rstrip('\n')

        new_text = REFERENCED_BY_SECTION_RE.sub(_sub, text)
    elif text.startswith(("## Related pages", "## Related Pages")):
        # Page begins with the Related section at byte 0: prepend, don't append.
        # Single newline joint matches the replace path's fixed point above.
        new_text = new_block.rstrip('\n') + '\n' + text
    else:
        # Insert before "## Related pages" / "## Related Pages" if present, else append
        related_re = re.compile(r'(?=\n## Related [Pp]ages)', re.MULTILINE)
        if related_re.search(text):
            new_text = related_re.sub('\n\n' + new_block.rstrip('\n'), text, count=1)
        else:
            new_text = text.rstrip('\n') + '\n\n' + new_block.rstrip('\n') + '\n'

    path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    all_pages = get_entity_pages()
    print(f"Found {len(all_pages)} entity pages.")
    # Authored texts are snapshotted once up front; pages mutated during the
    # loop can't feed their regenerated sections back into later scans.
    authored_texts = load_authored_texts(all_pages)
    for page in all_pages:
        slug = page.stem
        refs = find_references(slug, authored_texts, page)
        block = build_referenced_by_block(refs)
        update_page(page, block)
        inbound = sum(len(v) for v in refs.values())
        print(f"  {page}  ({inbound} inbound links)")
    print(f"\nDone. Processed {len(all_pages)} pages.")
