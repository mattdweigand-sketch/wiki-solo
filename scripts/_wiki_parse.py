#!/usr/bin/env python3
"""Shared markdown/frontmatter parsing primitives for the wiki scripts.

Single source of truth for the small parse helpers that several scripts used to
reimplement independently (lint.py, review_due.py, rebuild_referenced_by.py).
Keeping them here means the wikilink regex, the code-span stripping, the
frontmatter split, and the dangling-slug resolution cannot silently drift apart
across callers.

Vendor-neutral: stdlib only, no dependencies. Importable as a sibling module by
any scripts/*.py run from the repo root (the script's own directory is on
sys.path[0], exactly as ledger_common is imported).
"""

from __future__ import annotations

import re

# A wikilink slug, ignoring an optional folder prefix and an optional alias:
#   [[slug]], [[dir/slug]], [[dir/slug|alias]]  -> captures "slug".
LINK_RE = re.compile(r"\[\[(?:[^/\]|]+/)?([^\]|]+?)(?:\|[^\]]+)?\]\]")

# Code spans. Order of application matters: fenced blocks first, then inline.
INLINE_CODE_RE = re.compile(r"`[^`]*`")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

# Root-level wiki pages that are catalogs/indexes, not entity pages: never link
# targets and never counted as link sources. Shared so the dangling-link scan,
# the index-coverage check, and the referenced-by rebuild enumerate the corpus
# identically and cannot drift on what counts as a meta page.
META_PAGES = {
    "index", "log", "overview", "glossary", "primer",
    "sourcing-queue", "contradictions", "design-notes", "SCHEMA", "synthesis",
    "domain",
}
META_DIRS = set()

# A generated "## Referenced by" section runs to the next ## heading or EOF.
REFERENCED_BY_SECTION_RE = re.compile(r"## Referenced by\n.*?(?=\n## |\Z)", re.DOTALL)

# A wiki/log.md entry header: "## [YYYY-MM-DD] ..." or "## YYYY-MM-DD ...",
# followed by end-of-line, " | description", or a word. Single source of truth
# shared by rotate_log.py (which cuts the log only at these headers) and lint.py
# (which fails any other "## " line in log.md, so a nonconforming header cannot
# be silently merged into the previous entry's archive block at rotation).
LOG_ENTRY_HEADER_RE = re.compile(
    r"^## (?:(?:\[(?P<bracketed>\d{4}-\d{2}-\d{2})\])|"
    r"(?P<plain>\d{4}-\d{2}-\d{2}))"
    r"(?:$| \| (?:(?P<piped>[A-Za-z][\w-]*).*|.+)| (?P<worded>[A-Za-z][\w-]*).*)$"
)


def parse_log_entry_date(line):
    """The entry date if `line` is a recognized log entry header, else None."""
    match = LOG_ENTRY_HEADER_RE.match(line.rstrip("\n"))
    if not match:
        return None
    return match.group("bracketed") or match.group("plain")


def parse_log_entry_type(line):
    """The lowercased entry-type token from a recognized log entry header, or
    None when the line is not a header or carries no leading type token.
    Handles both live forms — "## [YYYY-MM-DD] type | ..." and
    "## YYYY-MM-DD | type | ..." — through the same LOG_ENTRY_HEADER_RE that
    recognizes headers, so recognition and type extraction cannot drift."""
    match = LOG_ENTRY_HEADER_RE.match(line.rstrip("\n"))
    if not match:
        return None
    token = match.group("piped") or match.group("worded")
    return token.lower() if token else None


def split_frontmatter(text):
    """Return (frontmatter_dict_of_toplevel_keys, body_text). Empty dict if none.

    Returns (None, text) when there is no parseable leading --- fence block.
    Block-style list values are flattened to '' (the key is present with an
    empty scalar); use frontmatter_block() when you need the raw block text.
    """
    if not text.startswith("---"):
        return None, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    fm_block, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_block.splitlines():
        km = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2).strip()
    return fm, body


def frontmatter_block(text):
    """Return the raw frontmatter block (text between the leading --- fences),
    or '' if there is none. Unlike split_frontmatter, this preserves block-style
    list values that the key parser flattens, so checks that scan raw lines
    (raw/ refs, source slugs, tags) see the real content."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    return m.group(1) if m else ""


def strip_code_spans(text):
    """Blank out fenced and inline code so a [[link]] written as a syntax
    example inside code is not mistaken for a real wikilink. Order matters:
    strip fenced blocks first, then inline spans, so the two dangling scans
    (entity pages and meta pages) stay in lockstep."""
    text = FENCED_CODE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    return text


def mask_code_spans(text):
    """Like strip_code_spans, but length-preserving: every code character is
    replaced with a NUL so offsets in the masked text map 1:1 onto the raw
    text. Use this when a regex must LOCATE something (a section span to
    rewrite) rather than merely count matches, so a fenced example can be
    skipped without shifting positions."""
    def mask(m):
        return "\x00" * len(m.group(0))
    masked = FENCED_CODE_RE.sub(mask, text)
    masked = INLINE_CODE_RE.sub(mask, masked)
    return masked


def dangling_slugs(text, valid_slugs):
    """Wikilink slugs in `text` that resolve to nothing, after stripping code
    spans and skipping folder-pointer links ([[name/]]). Single source of truth
    for both the Tier-1 entity-page scan and the Tier-2 meta-page scan, so the
    two cannot drift on what counts as a dangling link."""
    out = []
    for slug in LINK_RE.findall(strip_code_spans(text)):
        if slug.endswith("/") or slug in valid_slugs:
            continue
        out.append(slug)
    return out


def get_entity_pages(wiki_root):
    """All entity pages under `wiki_root`: top-level pages that are not meta
    pages, plus every page one level deep (every wiki/ subfolder is an
    entity-type folder). Sorted, so the link-graph scans in lint.py,
    review_due.py, and rebuild_referenced_by.py enumerate the corpus identically
    and cannot drift on what counts as an entity page."""
    pages = []
    for p in wiki_root.rglob("*.md"):
        parts = p.relative_to(wiki_root).parts
        if len(parts) == 1 and p.stem not in META_PAGES:
            pages.append(p)
        elif len(parts) == 2 and parts[0] not in META_DIRS:
            pages.append(p)
    return sorted(pages)


def strip_referenced_by(text):
    """Remove the auto-generated "## Referenced by" section so it never counts as
    an authored link. Shared by lint.py (its outbound link-graph reads only
    authored links) and rebuild_referenced_by.py (it must not feed generated
    output back into the graph), so the two cannot drift on what is generated."""
    return REFERENCED_BY_SECTION_RE.sub("", text)


def split_quoted_csv(value):
    """Split a simple inline YAML scalar or [list] value into item strings,
    respecting quotes so a comma inside a quoted phrase does not split it.
    Single source of truth for the frontmatter inline-list grammar (sources:
    and tags: parsing in lint.py)."""
    if not value:
        return []
    value = value.strip()
    if value.startswith("["):
        value = value[1:]
    if value.endswith("]"):
        value = value[:-1]
    cur, quote = "", None
    raw_items = []
    for ch in value:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur += ch
        elif ch == ",":
            raw_items.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        raw_items.append(cur)
    items = []
    for it in raw_items:
        it = it.strip().strip("\"'").strip()
        if it:
            items.append(it)
    return items
