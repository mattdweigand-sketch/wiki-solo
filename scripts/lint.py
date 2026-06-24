#!/usr/bin/env python3
"""
Lint the wiki against its own rules, split by enforcement tier.

Tier 1 (deterministic, machine-checkable): hard failures. A rule here is true
or false with no judgment. The script decides, and a Tier-1 failure exits
non-zero so it can gate a commit. Examples: frontmatter keys, type/folder
match, dangling [[links]], index coverage. (Em dashes are allowed in the wiki
corpus by decision, so they are not checked.)

Tier 2 (expert-checkable): ranked candidates, not verdicts. The script computes
signals a maintainer cannot eyeball across hundreds of pages (near-duplicates,
orphans, uncited pages, outcome-review enrollment) and surfaces them for a human
or agent to adjudicate. Tier 2 never fails the run unless --strict is passed.

Tier 3 (genuine judgment: contradictions, "missing cross-refs that should
exist", inconsistent terminology) is deliberately NOT attempted here. It stays
in the prose lint workflow, because a script cannot decide it.

Vendor-neutral: stdlib only, no dependencies. Run from the repo root:
    python3 scripts/lint.py            # report both tiers, fail on Tier 1
    python3 scripts/lint.py --strict   # also fail on Tier 2 candidates
    python3 scripts/lint.py --tier1    # Tier 1 only
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

from _wiki_parse import (
    LINK_RE,
    META_DIRS,
    META_PAGES,
    dangling_slugs,
    frontmatter_block,
    get_entity_pages,
    split_frontmatter,
    strip_code_spans,
    strip_referenced_by,
)

WIKI_ROOT = Path("wiki")
ADJUDICATIONS_PATH = Path("scripts/lint-adjudications.json")

# META_PAGES and META_DIRS are shared with rebuild_referenced_by.py via
# _wiki_parse, so the corpus enumeration cannot drift between linter and rebuild.

# folder name -> expected frontmatter type value
FOLDER_TYPE = {
    "sources": "source",
    "products": "product",
    "features": "feature",
    "personas": "persona",
    "customers": "customer",
    "competitors": "competitor",
    "concepts": "concept",
    "initiatives": "initiative",
    "decisions": "decision",
    "metrics": "metric",
    "people": "person",
    "analyses": "analysis",
}
ROOT_ALLOWED_FILES = {
    ".gitignore", "AGENTS.md", "CLAUDE.md", "CONTEXT.md", "LICENSE",
    "README.md", "REFERENCES.md", "SETUP.md",
}
ROOT_ALLOWED_DIRS = {
    ".claude", ".codex", ".github", ".git", "deliverables", "raw",
    "scripts", "tmp", "wiki", "workflows",
}
WIKI_ALLOWED_FILES = {f"{name}.md" for name in META_PAGES}
WIKI_ALLOWED_DIRS = set(FOLDER_TYPE)
RAW_ALLOWED_FILES = {".gitkeep", "README.md"}
VALID_CONFIDENCE = {"high", "medium", "low", "contested"}
VALID_SOURCE_TYPE = {
    "help-doc", "slack-thread", "call-transcript", "exec-memo", "deck",
    "crm-export", "strategy-doc", "release-note", "press", "analyst-report",
    "competitor-collateral", "sales-battlecard", "product-spec", "board-doc",
    "synthesis", "other",
}
BASE_KEYS = {"title", "type", "created", "updated", "sources", "tags", "confidence"}
RELATED_LABELS = {"Supports", "Contradicts", "Depends on", "Derived from", "Part of", "Related"}

MARKDOWN_MD_LINK_RE = re.compile(r"\]\(([^)]+?\.md(?:[?#][^)]*)?)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Entity classes required to enroll in the review_by outcome-review loop. The
# template makes decisions mandatory because they carry choices that should be
# revisited; analyses stay opt-in because many are reusable models rather than
# dated predictions.
REVIEW_BY_REQUIRED_FOLDERS = ("decisions",)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "into", "your", "you",
    "are", "for", "not", "but", "what", "when", "where", "which", "they",
    "them", "then", "than", "have", "has", "had", "was", "were", "will",
    "would", "can", "could", "should", "its", "it's", "their", "these",
    "those", "there", "here", "page", "pages", "wiki", "type", "tags",
}


def block_list_has_items(fm_text, key):
    """True if a YAML key carries a real value: an inline scalar/list, or at
    least one indented '- item' before the next top-level key. split_frontmatter
    flattens block lists to '', so the required-keys check alone cannot tell a
    populated agent_use_cases from a bare 'agent_use_cases:' header."""
    lines = fm_text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}:\s*(.*)$", line)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline and inline != "[]":
            return True
        for nxt in lines[i + 1:]:
            if re.match(r"^\s+-\s+\S", nxt):
                return True
            if re.match(r"^\S", nxt):  # next top-level key
                break
        return False
    return False


def authored_body(body):
    """Body up to the first generated/link section, for content checks."""
    cut = len(body)
    for marker in ("## Referenced by", "## Related pages", "## Related Pages"):
        i = body.find(marker)
        if i != -1:
            cut = min(cut, i)
    return body[:cut]


def tokens(text):
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    text = re.sub(r"[`*#|>_\-\[\]()]", " ", text)
    out = set()
    for w in re.findall(r"[a-z][a-z0-9']+", text.lower()):
        if len(w) >= 4 and w not in STOPWORDS:
            out.add(w)
    return out


# Tokens in a sources: value that are not provenance slugs to existence-check:
# raw/ paths are checked separately, and free-text provenance (experience,
# web research, deliverable, an explicit URL) is prose, not a page reference.
SOURCE_NONSLUG_PREFIX_RE = re.compile(r"^(experience|web|deliverable|source)\b", re.I)


def source_items(fm_block):
    """Split each sources: line in a frontmatter block into its list items,
    respecting quotes so a comma inside a quoted phrase does not split it."""
    items = []
    for line in fm_block.splitlines():
        m = re.match(r"^\s*sources?:\s*(.*)$", line)
        if not m:
            continue
        val = m.group(1).strip()
        if val.startswith("["):
            val = val[1:]
        if val.endswith("]"):
            val = val[:-1]
        cur, quote = "", None
        raw_items = []
        for ch in val:
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
        for it in raw_items:
            it = it.strip().strip("\"'").strip()
            if it:
                items.append(it)
    return items


# --------------------------- Tier 1 ---------------------------

def check_folder_structure():
    """Repo-level structure rules that should never require judgment."""
    fails = []

    for p in sorted(Path(".").rglob(".DS_Store")):
        if ".git" in p.parts:
            continue
        fails.append(("os-metadata", str(p), "remove Finder metadata file"))

    for p in sorted(Path(".").iterdir()):
        name = p.name
        if p.is_dir():
            if name not in ROOT_ALLOWED_DIRS:
                fails.append(("repo-structure", name, "unexpected top-level directory"))
        elif p.is_file():
            if name not in ROOT_ALLOWED_FILES:
                fails.append(("repo-structure", name, "unexpected top-level file"))
        else:
            fails.append(("repo-structure", name, "unexpected top-level entry type"))

    if WIKI_ROOT.exists():
        for p in sorted(WIKI_ROOT.iterdir()):
            name = p.name
            rel = str(p)
            if p.is_dir():
                if name not in WIKI_ALLOWED_DIRS:
                    fails.append(("wiki-structure", rel, "unexpected wiki/ folder"))
            elif p.is_file():
                if name not in WIKI_ALLOWED_FILES:
                    fails.append(("wiki-structure", rel, "unexpected wiki/ root file"))
                elif p.suffix != ".md":
                    fails.append(("wiki-structure", rel, "wiki/ root files must be Markdown"))
            else:
                fails.append(("wiki-structure", rel, "unexpected wiki/ entry type"))

    raw_root = Path("raw")
    if raw_root.exists():
        # raw/ bucket taxonomy lives in a tracked non-raw file so the allowlist
        # survives raw/ being gitignored and never committed. Loaded only when a
        # raw/ tree exists, so environments without one (e.g. lint fixtures) do
        # not require it. None => taxonomy unavailable, skip the per-folder check.
        raw_allowed_dirs = None
        raw_buckets_path = Path("scripts/raw-buckets.json")
        if not raw_buckets_path.exists():
            fails.append(("raw-buckets", str(raw_buckets_path),
                          "raw bucket taxonomy file is missing"))
        else:
            try:
                buckets = json.loads(raw_buckets_path.read_text(encoding="utf-8")).get("buckets")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                buckets = None
                fails.append(("raw-buckets", str(raw_buckets_path), f"unreadable JSON: {e}"))
            if isinstance(buckets, dict):
                raw_allowed_dirs = set(buckets)
            elif buckets is not None:
                fails.append(("raw-buckets", str(raw_buckets_path),
                              "must contain a 'buckets' object"))

        for p in sorted(raw_root.iterdir()):
            name = p.name
            rel = str(p)
            if p.is_dir():
                if not KEBAB_RE.match(name):
                    fails.append(("raw-structure", rel, "raw/ folder is not kebab-case"))
                if raw_allowed_dirs is not None and name not in raw_allowed_dirs:
                    fails.append(("raw-structure", rel, "raw/ folder missing from scripts/raw-buckets.json"))
            elif p.is_file():
                if name not in RAW_ALLOWED_FILES:
                    fails.append(("raw-structure", rel, "loose raw/ file; place source artifacts in a typed subfolder"))
            else:
                fails.append(("raw-structure", rel, "unexpected raw/ entry type"))

    deliverables_root = Path("deliverables")
    if deliverables_root.exists():
        for p in sorted(deliverables_root.iterdir()):
            rel = str(p)
            if p.is_dir():
                if not KEBAB_RE.match(p.name):
                    fails.append(("deliverables-structure", rel, "deliverables/ subfolder is not kebab-case"))
            else:
                fails.append(("deliverables-structure", rel, "loose deliverable; move it into a clearly labeled subfolder"))

    # tmp/ is intentionally disposable scratch space. Lint does not govern
    # its contents; the maintenance workflow may empty it at the end of a run.
    return fails

def check_no_tracked_raw():
    """raw/ source artifacts must not be committed; raw/.gitkeep and
    raw/README.md are tracked template exceptions. Fail Tier-1 on any other
    tracked raw/ path. No-ops when git is unavailable or this is not a work tree,
    so lint still runs outside a git context (e.g. eval fixtures copied to a temp
    dir)."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "raw"],
            capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []  # git not available; skip the guard
    if out.returncode != 0:
        return []  # not a git work tree; skip the guard
    fails = []
    allowed = {"raw/.gitkeep", "raw/README.md"}
    for path in out.stdout.decode("utf-8", "replace").split("\0"):
        if path and path not in allowed:
            fails.append(("raw-tracked", path,
                          "source artifact tracked in git; raw/ artifacts are "
                          "gitignored by default (only raw/.gitkeep and "
                          "raw/README.md are tracked)"))
    return fails


# Stray agent tool-call artifacts that leak into a page when an ingest Write/Edit
# call's own closing/opening tags get pasted into the content. </content> and
# </invoke> are closing tags matched exactly; <parameter ... > is an opening tag
# matched by prefix (it carries attributes). Each is matched only as a standalone
# line (the whole stripped line is the artifact), so a legitimate prose mention
# of a tag inside a sentence does not fire. This has recurred (a prior cleanup is
# logged in wiki/log.md), so it gets a deterministic guard.
STRAY_TAG_EXACT = {"</content>", "</invoke>"}


def check_stray_tool_tags():
    """Fail Tier-1 on stray agent tool-call tag lines committed into wiki/ pages.

    Scans every wiki/ Markdown file, meta pages included, because ingest writes
    touch both entity and meta pages. A line fires only when its stripped form
    equals </content> or </invoke>, or starts with <parameter; a sentence that
    merely mentions the tag does not."""
    fails = []
    if not WIKI_ROOT.exists():
        return fails
    for p in sorted(WIKI_ROOT.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # the per-page UTF-8 check reports encoding failures
        rel = str(p.relative_to(WIKI_ROOT))
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped in STRAY_TAG_EXACT or stripped.startswith("<parameter"):
                fails.append(("stray-tag", rel,
                              f"line {i}: stray tool-call artifact '{stripped}'"))
    return fails


def normalize_markdown_target(href):
    href = href.strip()
    if "://" in href or href.startswith("mailto:"):
        return None
    href = href.split("#", 1)[0].split("?", 1)[0]
    return href if href else None


def check_markdown_md_links():
    """Fail Tier-1 on stale ordinary Markdown links to .md files.

    Wikilinks are checked separately by slug. This covers direct links such as
    [index](index.md), [schema](wiki/SCHEMA.md), or [setup](../SETUP.md) from
    every wiki Markdown page, including meta pages.
    """
    fails = []
    if not WIKI_ROOT.exists():
        return fails
    repo_root = Path(".")
    for p in sorted(WIKI_ROOT.rglob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(p.relative_to(WIKI_ROOT))
        for href in MARKDOWN_MD_LINK_RE.findall(strip_code_spans(text)):
            target = normalize_markdown_target(href)
            if target is None:
                continue
            if target.startswith("/"):
                candidate = repo_root / target.lstrip("/")
            elif target.startswith("wiki/"):
                candidate = repo_root / target
            else:
                candidate = p.parent / target
            if not candidate.exists():
                fails.append(("markdown-link", rel, f"{href!r} points to missing file"))
    return fails


def read_adjudications():
    """Parse and shape-validate the adjudication file.

    Returns (raw_dict, error). raw is {} when the file is absent or invalid;
    error is a human-readable string only when the file exists but is bad,
    so Tier-1 can fail loudly instead of suppression silently turning off.
    """
    if not ADJUDICATIONS_PATH.exists():
        return {}, None
    try:
        raw = json.loads(ADJUDICATIONS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {}, f"unreadable JSON: {e}"
    if not isinstance(raw, dict):
        return {}, "top level must be a JSON object"
    for key in ("accepted_orphans", "hub_pages", "reviewed_confidence_low"):
        for e in raw.get(key, []):
            if not isinstance(e, dict) or not isinstance(e.get("page"), str):
                return {}, f"every '{key}' entry needs a string 'page' field"
    for key in ("skipped_crossref_pairs", "reviewed_near_duplicates"):
        for e in raw.get(key, []):
            pair = e.get("pair") if isinstance(e, dict) else None
            if not (isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(x, str) for x in pair)):
                return {}, f"every '{key}' entry needs a two-item string 'pair' field"
    for e in raw.get("reviewed_quotes", []):
        if not (isinstance(e, dict) and isinstance(e.get("page"), str)
                and isinstance(e.get("quote"), str)):
            return {}, "every 'reviewed_quotes' entry needs string 'page' and 'quote' fields"
    return raw, None


# --------------------------- Tier 1: per-page check registry ---------------------------
#
# Each per-page check below is a small, self-contained function a maintainer can
# read in isolation. It receives one PageContext and returns a list of fail
# tuples (check, page_relpath, detail), the same shape the loop appends. The
# registry TIER1_PAGE_CHECKS lists them in evaluation order; tier1() iterates the
# entity pages and, for each, runs every check in order. This preserves the exact
# emit order of the previous inlined loop (page-outer, check-inner), so the
# grouped/sorted report is byte-for-byte identical.


class PageContext:
    """Everything a Tier-1 per-page check needs about one entity page.

    Built once per page in the tier1() loop and passed to each registered check,
    so the checks share parsing work (read, split_frontmatter, frontmatter_block)
    instead of each re-deriving it."""

    __slots__ = ("path", "rel", "stem", "folder", "text", "fm", "fm_block",
                 "valid_slugs", "source_slugs")

    def __init__(self, path, text, valid_slugs, source_slugs):
        self.path = path
        self.rel = str(path.relative_to(WIKI_ROOT))
        self.stem = path.stem
        self.folder = path.parent.name if path.parent != WIKI_ROOT else None
        self.text = text
        self.fm, _ = split_frontmatter(text)
        self.fm_block = frontmatter_block(text)
        self.valid_slugs = valid_slugs
        self.source_slugs = source_slugs


def check_filename(ctx):
    """Filenames are kebab-case with no date prefix (chronology lives in log.md)."""
    fails = []
    if not KEBAB_RE.match(ctx.stem):
        fails.append(("filename", ctx.rel, "not kebab-case"))
    if DATE_PREFIX_RE.match(ctx.stem):
        fails.append(("filename", ctx.rel, "has date prefix"))
    return fails


def check_entity_folder(ctx):
    """Every entity page sits in a known entity-type folder."""
    if ctx.folder is not None and ctx.folder not in FOLDER_TYPE:
        return [("entity-folder", ctx.rel, f"unknown folder '{ctx.folder}'")]
    return []


def check_required_keys(ctx):
    """Required frontmatter keys are present, and agent_use_cases (non-sources)
    carries real list items rather than a bare header."""
    fails = []
    required = set(BASE_KEYS)
    if ctx.folder == "sources":
        required.add("source_type")
    if ctx.folder != "sources":
        required.add("agent_use_cases")
    missing = sorted(required - set(ctx.fm))
    if missing:
        fails.append(("frontmatter", ctx.rel, "missing keys: " + ", ".join(missing)))

    # agent_use_cases must carry list items, not just the bare key. Use the
    # shared ctx.fm_block (frontmatter_block) the context already computed rather
    # than re-splitting ctx.text, so this check cannot diverge from it.
    if "agent_use_cases" in required and "agent_use_cases" in ctx.fm:
        if not block_list_has_items(ctx.fm_block, "agent_use_cases"):
            fails.append(("frontmatter", ctx.rel, "agent_use_cases has no list items"))
    return fails


def check_type_matches_folder(ctx):
    """frontmatter type matches the folder it lives in."""
    expected = FOLDER_TYPE.get(ctx.folder)
    if "type" in ctx.fm and expected and ctx.fm["type"] != expected:
        return [("type", ctx.rel, f"type '{ctx.fm['type']}' != folder type '{expected}'")]
    return []


def check_confidence_value(ctx):
    """confidence is one of the allowed values."""
    if ctx.fm.get("confidence") and ctx.fm["confidence"] not in VALID_CONFIDENCE:
        return [("confidence", ctx.rel, f"invalid value '{ctx.fm['confidence']}'")]
    return []


def check_source_type_placement(ctx):
    """source_type is a valid value on sources, and absent elsewhere."""
    if ctx.folder == "sources":
        st = ctx.fm.get("source_type")
        if st and st not in VALID_SOURCE_TYPE:
            return [("source-type", ctx.rel, f"invalid value '{st}'")]
        return []
    if "source_type" in ctx.fm:
        return [("source-type", ctx.rel, "source_type set on non-source page")]
    return []


def check_dates(ctx):
    """created/updated/review_by are real YYYY-MM-DD calendar dates.

    review_by is optional; it opts a page into the review loop. Validating the
    value is a real calendar date (not just digit-shaped) keeps lint and
    review_due.py in agreement on what is valid."""
    fails = []
    for k in ("created", "updated", "review_by"):
        v = ctx.fm.get(k)
        if not v:
            continue
        if not DATE_RE.match(v):
            fails.append(("date", ctx.rel, f"{k} '{v}' is not YYYY-MM-DD"))
            continue
        try:
            date.fromisoformat(v)
        except ValueError:
            fails.append(("date", ctx.rel, f"{k} '{v}' is not a real calendar date"))
    return fails


def check_source_refs(ctx):
    """Provenance refs in the sources: value must resolve. The scan is scoped to
    the sources line(s), not the whole frontmatter block, so a raw/ token inside
    a title or tag is not treated as a ref (code:lint#4). raw/ paths must exist
    on disk; a bare kebab slug must name a wiki/sources/ page, catching a typo'd
    citation that would otherwise read as cited."""
    fails = []
    if not ctx.fm_block:
        return fails
    for item in source_items(ctx.fm_block):
        for raw_ref in re.findall(r"raw/[^\s,\]\"']+", item):
            if not Path(raw_ref).exists():
                fails.append(("source-ref", ctx.rel, f"'{raw_ref}' does not exist"))
        if (item.startswith("raw/")
                or SOURCE_NONSLUG_PREFIX_RE.match(item)
                or "://" in item or item.startswith("http")):
            continue
        if KEBAB_RE.match(item) and item not in ctx.source_slugs:
            fails.append(("source-ref", ctx.rel,
                          f"source '{item}' matches no wiki/sources/ page"))
    return fails


def check_dangling_links(ctx):
    """Wikilinks resolve to a real page. Code spans are stripped (a [[link]]
    inside a code example is not a failure); the shared dangling_slugs helper
    keeps this in lockstep with the Tier-2 meta-page dangling check."""
    return [("dangling-link", ctx.rel, f"[[{slug}]] resolves to nothing")
            for slug in dangling_slugs(ctx.text, ctx.valid_slugs)]


def check_related_labels(ctx):
    """Related-pages relationship labels come from the fixed vocabulary. A bullet
    may be untyped ("- [[page]]"), but a "Label:" prefix on a bullet that carries
    a [[link]] must be one of the six labels defined in AGENTS.md. A plain prose
    bullet ("- Note: ...", a page-to-create) is permitted by SCHEMA and is not an
    attempted typed label."""
    fails = []
    rp = re.search(r"## Related [Pp]ages\n(.*?)(?=\n## |\Z)", ctx.text, re.DOTALL)
    if rp:
        for line in rp.group(1).splitlines():
            lm = re.match(r"^-\s+([A-Za-z][A-Za-z ]*?):\s", line)
            if lm and "[[" in line and lm.group(1) not in RELATED_LABELS:
                fails.append(("related-label", ctx.rel,
                              f"'{lm.group(1)}:' is not an allowed relationship label"))
    return fails


def check_confidence_restate(ctx):
    """low/contested confidence is restated in the body (SCHEMA rule); contested
    pages also need a Disagreement section.

    NOTE: this is a keyword-presence proxy, not a semantic guarantee. It only
    verifies the word "confidence" appears in the authored body; it cannot tell a
    genuine caveat restatement from an incidental mention. True "did the page
    restate its uncertainty" is a judgment call that belongs in the Tier-3 prose
    review, so Tier-1 keeps the cheap proxy."""
    fails = []
    conf = ctx.fm.get("confidence")
    if conf in ("low", "contested"):
        _, body = split_frontmatter(ctx.text)
        ab = authored_body(body)
        if not re.search(r"confidence", ab, re.I):
            fails.append(("confidence-restate", ctx.rel,
                          f"confidence '{conf}' not restated in body"))
        if conf == "contested" and "## Disagreement" not in ab:
            fails.append(("confidence-restate", ctx.rel,
                          "contested page lacks a Disagreement section"))
    return fails


# Per-page Tier-1 checks, in evaluation order. tier1() runs each in turn for
# every entity page whose frontmatter parsed. To add a check, write a small
# check_*(ctx) -> fails function above and list it here.
TIER1_PAGE_CHECKS = (
    check_filename,
    check_entity_folder,
    check_required_keys,
    check_type_matches_folder,
    check_confidence_value,
    check_source_type_placement,
    check_dates,
    check_source_refs,
    check_dangling_links,
    check_related_labels,
    check_confidence_restate,
)


def tier1(entity_pages, valid_slugs, index_targets):
    fails = []  # (check, page_relpath, detail)
    fails.extend(check_folder_structure())
    fails.extend(check_no_tracked_raw())
    fails.extend(check_stray_tool_tags())
    fails.extend(check_markdown_md_links())

    def rel(p):
        return str(p.relative_to(WIKI_ROOT))

    # wikilinks resolve by bare stem, so two pages sharing one is an
    # ambiguous link target and a miscounted inbound graph
    by_stem = {}
    for p in entity_pages:
        by_stem.setdefault(p.stem, []).append(p)
    # source-page slugs, for resolving bare-slug provenance refs
    source_slugs = {p.stem for p in entity_pages if p.parent.name == "sources"}

    # meta-page dangling links are a hard failure too: a broken [[link]] in
    # index/overview/glossary/synthesis is as deterministic as one on an entity
    # page, so it gates the commit rather than only surfacing for review.
    for hit in meta_dangling_links(valid_slugs):
        fails.append(("meta-dangling-link", hit, "resolves to nothing"))
    for stem, ps in sorted(by_stem.items()):
        if len(ps) > 1:
            others = ", ".join(rel(q) for q in ps)
            for p in ps:
                fails.append(("duplicate-stem", rel(p), f"stem '{stem}' is shared by: {others}"))

    entity_relpaths = set()
    for p in entity_pages:
        r = rel(p)
        entity_relpaths.add(r)
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            fails.append(("encoding", r, f"not valid UTF-8: {e}"))
            continue

        ctx = PageContext(p, text, valid_slugs, source_slugs)

        # filename and entity-folder checks run even without parseable
        # frontmatter (they read the path, not the frontmatter dict).
        fails.extend(check_filename(ctx))
        fails.extend(check_entity_folder(ctx))

        if ctx.fm is None:
            fails.append(("frontmatter", r, "missing or malformed frontmatter"))
            continue

        # frontmatter-dependent per-page checks, in registry order. The two
        # path-only checks above already ran, so skip them here.
        for check in TIER1_PAGE_CHECKS[2:]:
            fails.extend(check(ctx))

    # index coverage (only for paths that name an entity folder)
    for r in sorted(entity_relpaths - index_targets):
        fails.append(("index-missing", r, "no row in index.md"))
    for t in sorted(index_targets - entity_relpaths):
        if "/" in t and t.split("/")[0] in FOLDER_TYPE:
            fails.append(("index-stale", t, "index.md row points to missing page"))

    # the adjudication file must parse and every entry must reference an
    # existing page; otherwise suppression silently turns off or a rename
    # silently detaches the settled judgment.
    raw, adj_err = read_adjudications()
    if adj_err:
        fails.append(("adjudication-file", str(ADJUDICATIONS_PATH), adj_err))
    else:
        referenced = []
        for key in ("accepted_orphans", "hub_pages", "reviewed_confidence_low",
                    "reviewed_quotes"):
            referenced += [e["page"] for e in raw.get(key, [])]
        for key in ("skipped_crossref_pairs", "reviewed_near_duplicates"):
            for e in raw.get(key, []):
                referenced += e["pair"]
        for page in sorted(set(referenced)):
            if page not in entity_relpaths:
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"entry references missing page '{page}'"))
    seen = set()
    deduped = []
    for f in fails:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


# A quoted span followed by an inline source citation, e.g.
#   "exact words from the source" (source: [[some-page]])
# Straight or curly double quotes; the citation may name several pages.
# This stays deterministic and adjacency-gated on purpose: deciding whether a
# non-adjacent quoted phrase is an attributed source quote, the author's own
# framing, or a rhetorical/example line is a judgment call, which the wiki keeps
# in the /wiki-lint evidence-review prose (Tier 3), not in this script.
QUOTED_CITATION_RE = re.compile(
    r'["“]([^"“”]{20,}?)["”]\s*\((?:own[^)]*?, )?source[sd]?:?\s*([^)]*\[\[[^)]*)\)',
    re.IGNORECASE,
)


def normalize_quote(text):
    """Lowercase, straighten curly quotes, collapse whitespace and punctuation
    that survives transcription differences, so verbatim matching is honest
    but not brittle."""
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("—", " ").replace("–", " ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def quote_fragments(quote):
    """Split a quote on ellipses and bracketed edits; fragments of 6+ words
    must each appear in the source for the quote to count as verbatim."""
    parts = re.split(r"\.\.\.|…|\[[^\]]*\]", quote)
    frags = [normalize_quote(p) for p in parts]
    return [f for f in frags if len(f.split()) >= 6]


def quote_mismatches(entity_pages, adjudicated_quotes):
    """Tier-2 candidates: quoted text attributed to a source that does not
    appear verbatim in the cited wiki page or its raw files. Deterministic
    string matching only; whether a non-match is a defect (vs. labeled own
    framing) is adjudicated by the lint workflow, not decided here."""
    by_stem = {p.stem: p for p in entity_pages}
    out, suppressed = [], 0
    for p in entity_pages:
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # tier1 reports it
        rel = str(p.relative_to(WIKI_ROOT))
        _, body = split_frontmatter(text)
        for m in QUOTED_CITATION_RE.finditer(authored_body(body)):
            quote_raw, cite_blob = m.group(1), m.group(2)
            frags = quote_fragments(quote_raw)
            if not frags:
                continue  # too short to judge deterministically
            if "own framing" in m.group(0).lower() or "own interview framing" in m.group(0).lower():
                continue  # explicitly labeled as not a source quote
            # gather cited pages' text plus their raw files
            haystacks = []
            for slug in LINK_RE.findall(cite_blob):
                cited = by_stem.get(slug)
                if cited is None:
                    continue  # dangling link; tier1 reports it
                try:
                    cited_text = cited.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue  # non-UTF8 cited page; tier1 reports it
                haystacks.append(normalize_quote(cited_text))
                cited_fm = frontmatter_block(cited_text)
                if cited_fm:
                    for raw_ref in re.findall(r"raw/[^\s,\]\"']+", cited_fm):
                        rp = Path(raw_ref)
                        if rp.is_file():
                            try:
                                haystacks.append(normalize_quote(
                                    rp.read_text(encoding="utf-8")))
                            except (OSError, UnicodeDecodeError):
                                pass
            if not haystacks:
                continue
            found = all(any(f in h for h in haystacks) for f in frags)
            if found:
                continue
            key = (rel, normalize_quote(quote_raw)[:80])
            if key in adjudicated_quotes:
                suppressed += 1
                continue
            preview = quote_raw[:70] + ("..." if len(quote_raw) > 70 else "")
            out.append(f'{rel}: "{preview}" not found in cited source(s)')
    return sorted(out), suppressed


# --------------------------- Tier 2 ---------------------------

def load_adjudications():
    """Settled Tier-2 judgments, held as data so lint stops re-surfacing them.

    Returns a dict of plain sets/pair-sets; empty when the file is absent so
    lint stays fully operable without it.
    """
    empty = {
        "orphans": set(), "hubs": set(), "pairs": set(),
        "confidence": set(), "duplicates": set(), "quotes": set(),
    }
    raw, err = read_adjudications()
    if not raw:
        # absent file or invalid file: suppress nothing; tier1 reports the error
        return empty
    return {
        "orphans": {e["page"] for e in raw.get("accepted_orphans", [])},
        "hubs": {e["page"] for e in raw.get("hub_pages", [])},
        "pairs": {frozenset(e["pair"]) for e in raw.get("skipped_crossref_pairs", [])},
        "confidence": {e["page"] for e in raw.get("reviewed_confidence_low", [])},
        "duplicates": {frozenset(e["pair"]) for e in raw.get("reviewed_near_duplicates", [])},
        "quotes": {(e["page"], normalize_quote(e["quote"])[:80])
                   for e in raw.get("reviewed_quotes", [])},
    }


def meta_dangling_links(valid_slugs):
    """Dangling [[links]] in wiki/ meta pages. The Tier-1 dangling check covers
    entity pages, so this extends the same guarantee to meta pages, which would
    otherwise rot unseen. Excludes code-span examples, folder pointers
    ([[name/]]), and log.md (an append-only history that deliberately preserves
    de-linked references as prose). Uses the shared dangling_slugs helper so the
    entity-page and meta-page scans cannot drift."""
    out = []
    for name in sorted(META_PAGES):
        if name == "log":
            continue
        p = WIKI_ROOT / f"{name}.md"
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for slug in dangling_slugs(text, valid_slugs):
            out.append(f"{name}.md: [[{slug}]]")
    return sorted(set(out))


# --------------------------- Tier 2: candidate-signal registry ---------------------------
#
# Tier-2 surfaces ranked review candidates, never hard failures. Each signal
# below is a small function over a shared Tier2Context: it returns
# (items, suppressed_delta), where items is the ranked candidate list and
# suppressed_delta counts how many candidates were dropped because they are
# adjudicated. tier2() builds the shared context once, then runs each registered
# signal in order, so the report order and counts are byte-for-byte identical to
# the previous inlined version.


class Tier2Context:
    """Shared per-page state every Tier-2 signal reads.

    Computed once in tier2() (page text, tokens, word counts, the inbound and
    outbound link graphs, and the adjudication sets), so the individual signal
    functions stay small and never re-walk the corpus."""

    __slots__ = ("pages", "data", "inbound", "outbound", "adj")

    def __init__(self, pages, valid_slugs, adjudicated):
        self.pages = pages
        self.data = {}
        self.inbound = {p: 0 for p in pages}
        self.outbound = {}
        for p in pages:
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # tier1 reports the encoding failure; skip for candidate signals
                text = ""
            fm, body = split_frontmatter(text)
            ab = authored_body(body)
            self.data[p] = {
                "fm": fm or {},
                "tokens": tokens(ab),
                "words": len(re.findall(r"\w+", ab)),
                "body_links": bool(LINK_RE.search(ab)),
            }
            # Outbound links must be authored; generated "Referenced by" blocks
            # would echo inbound links back and fabricate a bidirectional graph.
            self.outbound[p] = set(LINK_RE.findall(strip_referenced_by(text)))

        stems = {p.stem: p for p in pages}
        for p in pages:
            for slug in self.outbound[p]:
                if slug in stems and stems[slug] is not p:
                    self.inbound[stems[slug]] += 1

        # adjudicated is always supplied by the sole caller (tier2 <- main, which
        # passes load_adjudications()); load_adjudications already returns the
        # empty template when the file is absent, so no fallback is needed here.
        self.adj = adjudicated


def signal_quote_mismatch(ctx):
    """Quoted text attributed to a source that is not verbatim in the cited page."""
    return quote_mismatches(ctx.pages, ctx.adj["quotes"])


def signal_orphans(ctx):
    """Pages with no inbound links."""
    orphans = [str(p.relative_to(WIKI_ROOT)) for p in ctx.pages if ctx.inbound[p] == 0]
    suppressed = sum(1 for o in orphans if o in ctx.adj["orphans"])
    return sorted(o for o in orphans if o not in ctx.adj["orphans"]), suppressed


def signal_near_duplicate(ctx):
    """Derived-page pairs whose token sets overlap heavily (Jaccard >= 0.35).

    Compares derived pages only; a source page mirroring its own concept or
    analysis is expected overlap, not a duplicate."""
    derived = [p for p in ctx.pages if p.parent.name != "sources"]
    dups, suppressed = [], 0
    for a, b in combinations(derived, 2):
        ta, tb = ctx.data[a]["tokens"], ctx.data[b]["tokens"]
        if not ta or not tb:
            continue
        j = len(ta & tb) / len(ta | tb)
        if j >= 0.35:
            ra, rb = str(a.relative_to(WIKI_ROOT)), str(b.relative_to(WIKI_ROOT))
            if frozenset((ra, rb)) in ctx.adj["duplicates"]:
                suppressed += 1
                continue
            dups.append((j, ra, rb))
    return sorted(dups, reverse=True)[:15], suppressed


def signal_uncited(ctx):
    """Non-source pages with no sources and no body links."""
    uncited = []
    for p in ctx.pages:
        if p.parent.name == "sources":
            continue
        srcs = ctx.data[p]["fm"].get("sources", "")
        empty_sources = srcs in ("", "[]")
        if empty_sources and not ctx.data[p]["body_links"]:
            uncited.append(str(p.relative_to(WIKI_ROOT)))
    return sorted(uncited), 0


def signal_thin(ctx):
    """Pages under 80 authored words."""
    return sorted(
        f"{p.relative_to(WIKI_ROOT)} ({ctx.data[p]['words']}w)"
        for p in ctx.pages if ctx.data[p]["words"] < 80
    ), 0


def signal_confidence_upgrade(ctx):
    """confidence:low pages with >=2 inbound links (candidates to upgrade)."""
    upgrade, suppressed = [], 0
    for p in ctx.pages:
        if p.parent.name == "sources":
            continue
        fm = ctx.data[p]["fm"]
        if fm.get("confidence") == "low" and ctx.inbound[p] >= 2:
            if str(p.relative_to(WIKI_ROOT)) in ctx.adj["confidence"]:
                suppressed += 1
                continue
            upgrade.append(f"{p.relative_to(WIKI_ROOT)} ({ctx.inbound[p]} inbound)")
    return sorted(upgrade), suppressed


def signal_missing_open_questions(ctx):
    """Non-source pages missing an Open questions / gaps section.

    SCHEMA requires it on non-source pages; it is optional on sources, where
    confidence already flags preview-only material."""
    missing_oq = []
    for p in ctx.pages:
        if p.parent.name == "sources":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # tier1 reports the encoding failure
        if not re.search(r"^##+ Open [Qq]uestions", text, re.M):
            missing_oq.append(str(p.relative_to(WIKI_ROOT)))
    return sorted(missing_oq), 0


def signal_missing_related(ctx):
    """Page pairs whose outbound link profiles overlap heavily but are not linked.

    Scores co-citation by normalized overlap (Jaccard of outbound link sets), not
    absolute shared count: an absolute count grows with page size, so link-rich
    pages dominate regardless of relationship strength. The 0.5 bar means the
    pair's link profiles mostly coincide; the floor of 3 shared links keeps
    trivially small pages out. Above-bar only, so an empty list is achievable and
    means "nothing worth reviewing"."""
    cocite, suppressed = [], 0
    for a, b in combinations(ctx.pages, 2):
        shared = ctx.outbound[a] & ctx.outbound[b]
        shared.discard(a.stem)
        shared.discard(b.stem)
        if len(shared) < 3 or b.stem in ctx.outbound[a] or a.stem in ctx.outbound[b]:
            continue
        union = (ctx.outbound[a] | ctx.outbound[b]) - {a.stem, b.stem}
        score = len(shared) / len(union) if union else 0.0
        if score < 0.5:
            continue
        ra, rb = str(a.relative_to(WIKI_ROOT)), str(b.relative_to(WIKI_ROOT))
        if ra in ctx.adj["hubs"] or rb in ctx.adj["hubs"] or frozenset((ra, rb)) in ctx.adj["pairs"]:
            suppressed += 1
            continue
        cocite.append((score, len(shared), ra, rb))
    return sorted(cocite, reverse=True), suppressed


def signal_review_by_missing(ctx):
    """Decisions with no `review_by` date (outcome-review enrollment).

    Surfaces the classes that should carry a dated review checkpoint but do not.
    Tier-2 and non-blocking: enrollment is a judgment call, and analyses stay
    opt-in (see REVIEW_BY_REQUIRED_FOLDERS)."""
    out = []
    for p in ctx.pages:
        if p.parent.name not in REVIEW_BY_REQUIRED_FOLDERS:
            continue
        if not ctx.data[p]["fm"].get("review_by"):
            out.append(str(p.relative_to(WIKI_ROOT)))
    return sorted(out), 0


# Tier-2 signals as (output key, report label, signal fn), in report order.
# tier2() runs each over the shared context and records its (items,
# suppressed_delta) under the key; main() reports them in this order using the
# label. Key, order, and label live in one tuple so adding/removing/reordering a
# signal is a single edit and the computation and report cannot drift. To add a
# signal, write a small signal_*(ctx) -> (items, suppressed) function and add a
# row here. (Meta-page dangling links moved to Tier-1 as a hard failure and are
# no longer surfaced here.)
TIER2_SIGNALS = (
    ("quote_mismatch", "quote mismatches (quoted text not verbatim in cited source)", signal_quote_mismatch),
    ("orphans", "orphans (no inbound links)", signal_orphans),
    ("near_duplicate", "near-duplicate pairs (prefer updating over creating)", signal_near_duplicate),
    ("uncited", "uncited (no sources, no body links)", signal_uncited),
    ("thin", "thin pages (<80 words)", signal_thin),
    ("confidence_upgrade", "confidence:low with >=2 inbound (upgrade?)", signal_confidence_upgrade),
    ("missing_open_questions", "non-source pages missing Open questions / gaps section", signal_missing_open_questions),
    ("missing_related", "missing cross-refs (link profiles >=50% overlapping, not linked)", signal_missing_related),
    ("review_by_missing", "decisions with no review_by (enroll in the outcome-review loop or leave for now)", signal_review_by_missing),
)


def tier2(entity_pages, valid_slugs, adjudicated):
    pages = [p for p in entity_pages if p.parent.name not in META_DIRS]
    ctx = Tier2Context(pages, valid_slugs, adjudicated)

    out = {}
    suppressed = 0
    for key, _label, signal in TIER2_SIGNALS:
        items, delta = signal(ctx)
        out[key] = items
        suppressed += delta

    out["_suppressed"] = suppressed
    return out


# --------------------------- reporting ---------------------------

def parse_index_targets():
    idx = WIKI_ROOT / "index.md"
    if not idx.exists():
        return set()
    text = idx.read_text(encoding="utf-8")
    return {m for m in re.findall(r"\]\(([^)]+?\.md)\)", text)}


def main():
    ap = argparse.ArgumentParser(description="Lint the wiki by enforcement tier.")
    ap.add_argument("--strict", action="store_true", help="fail on Tier-2 candidates too")
    ap.add_argument("--tier1", action="store_true", help="run Tier 1 only")
    args = ap.parse_args()

    if not WIKI_ROOT.exists():
        print(f"Error: 'wiki/' not found. Run from the repo root. cwd={Path.cwd()}",
              file=sys.stderr)
        return 2

    entity_pages = get_entity_pages(WIKI_ROOT)
    valid_slugs = {p.stem for p in entity_pages} | META_PAGES
    index_targets = parse_index_targets()

    print(f"Wiki lint: {len(entity_pages)} entity pages\n")

    t1 = tier1(entity_pages, valid_slugs, index_targets)
    print("TIER 1  (deterministic; must fix)")
    if not t1:
        print("  all checks passed")
    else:
        by_check = {}
        for check, page, detail in t1:
            by_check.setdefault(check, []).append((page, detail))
        for check in sorted(by_check):
            rows = by_check[check]
            print(f"  [{check}]  {len(rows)}")
            for page, detail in rows[:25]:
                print(f"      {page}: {detail}")
            if len(rows) > 25:
                print(f"      ... and {len(rows) - 25} more")
    print()

    t2 = None
    suppressed = 0
    if not args.tier1:
        t2 = tier2(entity_pages, valid_slugs, load_adjudications())
        suppressed = t2.pop("_suppressed", 0)
        print("TIER 2  (review; ranked candidates, judgment decides)")
        for key, label, _signal in TIER2_SIGNALS:
            items = t2[key]
            print(f"  {label}: {len(items)}")
            for it in items:
                if key == "near_duplicate":
                    j, a, b = it
                    print(f"      {a}  ~  {b}  (jaccard {j:.2f})")
                elif key == "missing_related":
                    score, n, a, b = it
                    print(f"      {a}  +  {b}  (overlap {score:.2f}, {n} shared)")
                else:
                    print(f"      {it}")
        if suppressed:
            print(f"  (adjudicated, suppressed via {ADJUDICATIONS_PATH}: {suppressed})")
        print()

    n1 = len(t1)
    print(f"Summary: {n1} Tier-1 failure(s)" +
          ("" if args.tier1 else f"; {sum(len(v) for v in t2.values())} Tier-2 candidate(s)"))

    if n1:
        return 1
    if args.strict and t2 and any(t2.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
