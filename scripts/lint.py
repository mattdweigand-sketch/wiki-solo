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
orphans, uncited pages) and surfaces them for a human or agent to adjudicate.
Tier 2 never fails the run unless --strict is passed.

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
import sys
from itertools import combinations
from pathlib import Path

WIKI_ROOT = Path("wiki")
ADJUDICATIONS_PATH = Path("scripts/lint-adjudications.json")

META_PAGES = {
    "index", "log", "overview", "glossary", "primer",
    "sourcing-queue", "contradictions", "design-notes", "SCHEMA", "synthesis",
    "domain",
}
META_DIRS = set()  # all wiki/ subfolders are entity types, style/ included

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
    "style": "style",
}
ROOT_ALLOWED_FILES = {
    ".gitignore", "AGENTS.md", "CLAUDE.md", "CONTEXT.md", "README.md",
    "REFERENCES.md", "SETUP.md", "CONTRIBUTING.md", "LICENSE",
}
ROOT_ALLOWED_DIRS = {
    ".claude", ".codex", ".github", ".git", "archive", "deliverables", "raw",
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

LINK_RE = re.compile(r"\[\[(?:[^/\]|]+/)?([^\]|]+?)(?:\|[^\]]+)?\]\]")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "into", "your", "you",
    "are", "for", "not", "but", "what", "when", "where", "which", "they",
    "them", "then", "than", "have", "has", "had", "was", "were", "will",
    "would", "can", "could", "should", "its", "it's", "their", "these",
    "those", "there", "here", "page", "pages", "wiki", "type", "tags",
}


def get_entity_pages():
    pages = []
    for p in WIKI_ROOT.rglob("*.md"):
        parts = p.relative_to(WIKI_ROOT).parts
        if len(parts) == 1 and p.stem not in META_PAGES:
            pages.append(p)
        elif len(parts) == 2 and parts[0] not in META_DIRS:
            pages.append(p)
    return sorted(pages)


def split_frontmatter(text):
    """Return (frontmatter_dict_of_toplevel_keys, body_text). Empty dict if none."""
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


def authored_body(body):
    """Body up to the first generated/link section, for content checks."""
    cut = len(body)
    for marker in ("## Referenced by", "## Related pages", "## Related Pages"):
        i = body.find(marker)
        if i != -1:
            cut = min(cut, i)
    return body[:cut]


# A generated "## Referenced by" section runs to the next ## heading or EOF.
REFERENCED_BY_SECTION_RE = re.compile(r"## Referenced by\n.*?(?=\n## |\Z)", re.DOTALL)


def strip_referenced_by(text):
    """Drop the auto-generated inbound-link section; what remains is authored.

    Unlike authored_body(), this keeps the hand-curated "## Related pages"
    section, so it is the right base for outbound link-graph checks.
    """
    return REFERENCED_BY_SECTION_RE.sub("", text)


def tokens(text):
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    text = re.sub(r"[`*#|>_\-\[\]()]", " ", text)
    out = set()
    for w in re.findall(r"[a-z][a-z0-9']+", text.lower()):
        if len(w) >= 4 and w not in STOPWORDS:
            out.add(w)
    return out


# --------------------------- Tier 1 ---------------------------

def check_folder_structure():
    """Repo-level structure rules that should never require judgment."""
    fails = []

    raw_allowed_dirs = set()
    raw_readme = Path("raw/README.md")
    if raw_readme.exists():
        raw_allowed_dirs = set(re.findall(
            r"\|\s*`([a-z0-9]+(?:-[a-z0-9]+)*)/`\s*\|",
            raw_readme.read_text(encoding="utf-8"),
        ))

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
        for p in sorted(raw_root.iterdir()):
            name = p.name
            rel = str(p)
            if p.is_dir():
                if not KEBAB_RE.match(name):
                    fails.append(("raw-structure", rel, "raw/ folder is not kebab-case"))
                if name not in raw_allowed_dirs:
                    fails.append(("raw-structure", rel, "raw/ folder missing from raw/README.md subfolder map"))
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


def tier1(entity_pages, valid_slugs, index_targets):
    fails = []  # (check, page_relpath, detail)
    fails.extend(check_folder_structure())

    def rel(p):
        return str(p.relative_to(WIKI_ROOT))

    # wikilinks resolve by bare stem, so two pages sharing one is an
    # ambiguous link target and a miscounted inbound graph
    by_stem = {}
    for p in entity_pages:
        by_stem.setdefault(p.stem, []).append(p)
    for stem, ps in sorted(by_stem.items()):
        if len(ps) > 1:
            others = ", ".join(rel(q) for q in ps)
            for p in ps:
                fails.append(("duplicate-stem", rel(p), f"stem '{stem}' is shared by: {others}"))

    entity_relpaths = set()
    for p in entity_pages:
        r = rel(p)
        entity_relpaths.add(r)
        folder = p.parent.name if p.parent != WIKI_ROOT else None
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            fails.append(("encoding", r, f"not valid UTF-8: {e}"))
            continue

        # filename
        if not KEBAB_RE.match(p.stem):
            fails.append(("filename", r, "not kebab-case"))
        if DATE_PREFIX_RE.match(p.stem):
            fails.append(("filename", r, "has date prefix"))

        # entity folder must be known
        if folder is not None and folder not in FOLDER_TYPE:
            fails.append(("entity-folder", r, f"unknown folder '{folder}'"))

        # frontmatter
        fm, _ = split_frontmatter(text)
        if fm is None:
            fails.append(("frontmatter", r, "missing or malformed frontmatter"))
            continue

        required = set(BASE_KEYS)
        if folder == "sources":
            required.add("source_type")
        if folder not in ("sources", "style"):
            required.add("agent_use_cases")
        missing = sorted(required - set(fm))
        if missing:
            fails.append(("frontmatter", r, "missing keys: " + ", ".join(missing)))

        # type matches folder
        expected = FOLDER_TYPE.get(folder)
        if "type" in fm and expected and fm["type"] != expected:
            fails.append(("type", r, f"type '{fm['type']}' != folder type '{expected}'"))

        # confidence value
        if fm.get("confidence") and fm["confidence"] not in VALID_CONFIDENCE:
            fails.append(("confidence", r, f"invalid value '{fm['confidence']}'"))

        # source_type placement
        if folder == "sources":
            st = fm.get("source_type")
            if st and st not in VALID_SOURCE_TYPE:
                fails.append(("source-type", r, f"invalid value '{st}'"))
        elif "source_type" in fm:
            fails.append(("source-type", r, "source_type set on non-source page"))

        # date formats
        for k in ("created", "updated"):
            if fm.get(k) and not DATE_RE.match(fm[k]):
                fails.append(("date", r, f"{k} '{fm[k]}' is not YYYY-MM-DD"))

        # raw/ provenance refs in frontmatter must resolve (scan the raw
        # frontmatter block: list-style sources don't survive the key parse)
        fm_block = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if fm_block:
            for raw_ref in re.findall(r"raw/[^\s,\]\"']+", fm_block.group(1)):
                if not Path(raw_ref).exists():
                    fails.append(("source-ref", r, f"'{raw_ref}' does not exist"))

        # dangling wikilinks
        for slug in LINK_RE.findall(text):
            if slug not in valid_slugs:
                fails.append(("dangling-link", r, f"[[{slug}]] resolves to nothing"))

        # Related-pages relationship labels come from the fixed vocabulary.
        # A bullet may be untyped ("- [[page]]"), but a "Label:" prefix must
        # be one of the six labels defined in AGENTS.md.
        rp = re.search(r"## Related [Pp]ages\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
        if rp:
            for line in rp.group(1).splitlines():
                lm = re.match(r"^-\s+([A-Za-z][A-Za-z ]*?):\s", line)
                if lm and lm.group(1) not in RELATED_LABELS:
                    fails.append(("related-label", r, f"'{lm.group(1)}:' is not an allowed relationship label"))

        # low/contested confidence is restated in the body (SCHEMA rule);
        # contested pages also need a Disagreement section.
        conf = fm.get("confidence")
        if conf in ("low", "contested"):
            _, body = split_frontmatter(text)
            ab = authored_body(body)
            if not re.search(r"confidence", ab, re.I):
                fails.append(("confidence-restate", r, f"confidence '{conf}' not restated in body"))
            if conf == "contested" and "## Disagreement" not in ab:
                fails.append(("confidence-restate", r, "contested page lacks a Disagreement section"))

    # index coverage (only for paths that name an entity folder)
    for r in sorted(entity_relpaths - index_targets):
        fails.append(("index-missing", r, "no row in index.md"))
    for t in sorted(index_targets - entity_relpaths):
        if "/" in t and t.split("/")[0] in FOLDER_TYPE:
            fails.append(("index-stale", t, "index.md row points to missing page"))

    # the adjudication file must parse and every entry must reference an
    # existing entity page; otherwise suppression silently turns off or a
    # rename silently detaches the settled judgment.
    raw, adj_err = read_adjudications()
    if adj_err:
        fails.append(("adjudication-file", str(ADJUDICATIONS_PATH), adj_err))
    else:
        referenced = []
        for key in ("accepted_orphans", "hub_pages", "reviewed_confidence_low"):
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
                cited_text = cited.read_text(encoding="utf-8")
                haystacks.append(normalize_quote(cited_text))
                fm_block = re.match(r"^---\n(.*?)\n---", cited_text, re.DOTALL)
                if fm_block:
                    for raw_ref in re.findall(r"raw/[^\s,\]\"']+", fm_block.group(1)):
                        rp = Path(raw_ref)
                        if rp.exists():
                            try:
                                haystacks.append(normalize_quote(
                                    rp.read_text(encoding="utf-8")))
                            except UnicodeDecodeError:
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


def tier2(entity_pages, adjudicated=None):
    pages = [p for p in entity_pages if p.parent.name not in META_DIRS]
    data = {}
    inbound = {p: 0 for p in pages}
    outbound = {}
    for p in pages:
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # tier1 reports the encoding failure; skip for candidate signals
            text = ""
        fm, body = split_frontmatter(text)
        ab = authored_body(body)
        data[p] = {
            "fm": fm or {},
            "tokens": tokens(ab),
            "words": len(re.findall(r"\w+", ab)),
            "body_links": bool(LINK_RE.search(ab)),
        }
        # Outbound links must be authored; generated "Referenced by" blocks
        # would echo inbound links back and fabricate a bidirectional graph.
        outbound[p] = set(LINK_RE.findall(strip_referenced_by(text)))

    stems = {p.stem: p for p in pages}
    for p in pages:
        for slug in outbound[p]:
            if slug in stems and stems[slug] is not p:
                inbound[stems[slug]] += 1

    adj = adjudicated or {
        "orphans": set(), "hubs": set(), "pairs": set(),
        "confidence": set(), "duplicates": set(), "quotes": set(),
    }
    out = {}
    suppressed = 0

    out["quote_mismatch"], q_suppressed = quote_mismatches(pages, adj["quotes"])
    suppressed += q_suppressed

    orphans = [str(p.relative_to(WIKI_ROOT)) for p in pages if inbound[p] == 0]
    suppressed += sum(1 for o in orphans if o in adj["orphans"])
    out["orphans"] = sorted(o for o in orphans if o not in adj["orphans"])

    # Compare derived pages only; a source page mirroring its own concept or
    # analysis is expected overlap, not a duplicate.
    derived = [p for p in pages if p.parent.name != "sources"]
    dups = []
    for a, b in combinations(derived, 2):
        ta, tb = data[a]["tokens"], data[b]["tokens"]
        if not ta or not tb:
            continue
        j = len(ta & tb) / len(ta | tb)
        if j >= 0.35:
            ra, rb = str(a.relative_to(WIKI_ROOT)), str(b.relative_to(WIKI_ROOT))
            if frozenset((ra, rb)) in adj["duplicates"]:
                suppressed += 1
                continue
            dups.append((j, ra, rb))
    out["near_duplicate"] = sorted(dups, reverse=True)[:15]

    uncited = []
    for p in pages:
        if p.parent.name == "sources":
            continue
        srcs = data[p]["fm"].get("sources", "")
        empty_sources = srcs in ("", "[]")
        if empty_sources and not data[p]["body_links"]:
            uncited.append(str(p.relative_to(WIKI_ROOT)))
    out["uncited"] = sorted(uncited)

    out["thin"] = sorted(
        f"{p.relative_to(WIKI_ROOT)} ({data[p]['words']}w)"
        for p in pages if data[p]["words"] < 80
    )

    upgrade = []
    for p in pages:
        if p.parent.name == "sources":
            continue
        fm = data[p]["fm"]
        if fm.get("confidence") == "low" and inbound[p] >= 2:
            if str(p.relative_to(WIKI_ROOT)) in adj["confidence"]:
                suppressed += 1
                continue
            upgrade.append(f"{p.relative_to(WIKI_ROOT)} ({inbound[p]} inbound)")
    out["confidence_upgrade"] = sorted(upgrade)

    # SCHEMA requires an "Open questions / gaps" section on non-source pages;
    # optional on sources, where confidence already flags preview-only material.
    missing_oq = []
    for p in pages:
        if p.parent.name == "sources":
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # tier1 reports the encoding failure
        if not re.search(r"^##+ Open [Qq]uestions", text, re.M):
            missing_oq.append(str(p.relative_to(WIKI_ROOT)))
    out["missing_open_questions"] = sorted(missing_oq)

    # Score co-citation by normalized overlap (Jaccard of outbound link sets),
    # not absolute shared count: an absolute count grows with page size, so
    # link-rich pages dominate regardless of relationship strength. The 0.5
    # bar means the pair's link profiles mostly coincide; the floor of 3
    # shared links keeps trivially small pages out. Above-bar only, so an
    # empty list is achievable and means "nothing worth reviewing".
    cocite = []
    for a, b in combinations(pages, 2):
        shared = outbound[a] & outbound[b]
        shared.discard(a.stem)
        shared.discard(b.stem)
        if len(shared) < 3 or b.stem in outbound[a] or a.stem in outbound[b]:
            continue
        union = (outbound[a] | outbound[b]) - {a.stem, b.stem}
        score = len(shared) / len(union) if union else 0.0
        if score < 0.5:
            continue
        ra, rb = str(a.relative_to(WIKI_ROOT)), str(b.relative_to(WIKI_ROOT))
        if ra in adj["hubs"] or rb in adj["hubs"] or frozenset((ra, rb)) in adj["pairs"]:
            suppressed += 1
            continue
        cocite.append((score, len(shared), ra, rb))
    out["missing_related"] = sorted(cocite, reverse=True)

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

    entity_pages = get_entity_pages()
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
        t2 = tier2(entity_pages, load_adjudications())
        suppressed = t2.pop("_suppressed", 0)
        print("TIER 2  (review; ranked candidates, judgment decides)")
        labels = {
            "quote_mismatch": "quote mismatches (quoted text not verbatim in cited source)",
            "orphans": "orphans (no inbound links)",
            "near_duplicate": "near-duplicate pairs (prefer updating over creating)",
            "uncited": "uncited (no sources, no body links)",
            "thin": "thin pages (<80 words)",
            "confidence_upgrade": "confidence:low with >=2 inbound (upgrade?)",
            "missing_open_questions": "non-source pages missing Open questions / gaps section",
            "missing_related": "missing cross-refs (link profiles >=50% overlapping, not linked)",
        }
        total2 = 0
        for key, label in labels.items():
            items = t2[key]
            total2 += len(items)
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
