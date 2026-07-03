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

from _wiki_parse import (
    LINK_RE,
    REFERENCED_BY_SECTION_RE,
    get_entity_pages,
    mask_code_spans,
    strip_code_spans,
    strip_referenced_by,
)

WIKI_ROOT = Path("wiki")

if not WIKI_ROOT.exists():
    print(
        "Error: 'wiki/' directory not found. Run this script from the repo root.\n"
        f"  Current directory: {Path.cwd()}",
        file=sys.stderr,
    )
    sys.exit(1)


def load_authored_texts(all_pages):
    """Read every page once and return {path: authored link-scan text}: the
    generated "## Referenced by" sections are stripped so they never feed back
    into the graph, and code spans are blanked so a [[link]] written as a syntax
    example inside code is not counted as a real inbound reference (the same
    rule lint's dangling and outbound scans apply via _wiki_parse).

    Composition order matters: code spans are blanked FIRST, so a fenced
    "## Referenced by" example cannot start a section strip that would eat its
    own closing fence and the authored links after it."""
    texts = {}
    for p in all_pages:
        try:
            texts[p] = strip_referenced_by(strip_code_spans(p.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"Warning: skipping unreadable page as a link source: {p} ({exc})",
                  file=sys.stderr)
            continue
    return texts


def find_references(slug, authored_texts, target_path):
    """Return {directory_label: [link_text, ...]} for pages whose authored text mentions [[slug]].

    Uses the shared LINK_RE to extract every wikilink slug (bare [[slug]],
    path-qualified [[dir/slug]], or aliased [[dir/slug|text]]) so the link-graph
    grammar matches lint.py exactly."""
    refs = defaultdict(list)
    for p, text in authored_texts.items():
        if p == target_path:
            continue
        if slug in LINK_RE.findall(text):
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
    # All section LOCATION happens on the length-preserving code mask, so a
    # fenced "## Referenced by" example documenting the convention is never
    # mistaken for the real generated section (nor a fenced "## Related pages"
    # for the insertion anchor); spans map 1:1 back onto the raw text.
    masked = mask_code_spans(text)

    matches = list(REFERENCED_BY_SECTION_RE.finditer(masked))
    if matches:
        # Replace the first "## Referenced by" section (up to next ## heading
        # or EOF) and drop any duplicates a hand edit may have introduced.
        parts, last = [], 0
        for i, m in enumerate(matches):
            parts.append(text[last:m.start()])
            if i == 0:
                parts.append(new_block.rstrip('\n'))
            last = m.end()
        parts.append(text[last:])
        new_text = "".join(parts)
        # When the replaced section reaches EOF the match swallowed the final
        # newline; restore it so the first pass converges byte-identically
        # with the append path.
        if not new_text.endswith("\n"):
            new_text += "\n"
    elif text.startswith(("## Related pages", "## Related Pages")):
        # Page begins with the Related section at byte 0: prepend, don't append.
        # Single newline joint matches the replace path's fixed point above.
        new_text = new_block.rstrip('\n') + '\n' + text
    else:
        # Insert before "## Related pages" / "## Related Pages" if present, else append
        related_re = re.compile(r'\n## Related [Pp]ages')
        anchor = related_re.search(masked)
        if anchor:
            i = anchor.start()
            new_text = text[:i] + '\n\n' + new_block.rstrip('\n') + text[i:]
        else:
            new_text = text.rstrip('\n') + '\n\n' + new_block.rstrip('\n') + '\n'

    path.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    all_pages = get_entity_pages(WIKI_ROOT)
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
