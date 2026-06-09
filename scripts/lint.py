#!/usr/bin/env python3
"""
Lint the wiki against its own rules, split by enforcement tier.

Tier 1 (deterministic, machine-checkable): hard failures. A rule here is true
or false with no judgment. The script decides, and a Tier-1 failure exits
non-zero so it can gate a commit. Examples: frontmatter keys, type/folder
match, dangling [[links]], index coverage, and typed-link reciprocity (if a
feature links to its product, the product must link back). Reciprocity is the
deterministic slice of "missing cross-references": symmetry is machine-checkable,
but completeness (did the product link to ALL its features?) needs judgment and
stays in Tier 3.

Tier 2 (expert-checkable): ranked candidates, not verdicts. The script computes
signals a maintainer cannot eyeball across hundreds of pages (near-duplicates,
orphans, uncited pages, confidence-upgrade candidates) and surfaces them for a
human or agent to adjudicate. Tier 2 never fails the run unless --strict.

Tier 3 (genuine judgment: contradictions, stale claims, terminology drift,
concepts mentioned without their own page, confidence downgrades) is
deliberately NOT attempted here. It stays in the prose lint workflow under
workflows/maintenance/docs/lint-criteria.md, because a script cannot decide it.

Vendor-neutral: stdlib only, no dependencies. Run from the repo root:
    python3 scripts/lint.py            # report both tiers, fail on Tier 1
    python3 scripts/lint.py --strict   # also fail on Tier 2 candidates
    python3 scripts/lint.py --tier1    # Tier 1 only
"""
import argparse
import re
import sys
from itertools import combinations
from pathlib import Path

WIKI_ROOT = Path("wiki")

# Depth-1 infrastructure pages: config and indexes, not citable entities.
# The maintenance scratchpads (contradictions, sourcing-queue, design-notes)
# and the schema live under workflows/ or wiki/SCHEMA.md, so they are not present here.
META_PAGES = {
    "index", "log", "overview", "glossary", "primer", "domain", "SCHEMA",
    "contradictions", "sourcing-queue", "design-notes",
}
META_DIRS = {"style"}

# folder name -> expected frontmatter type value
FOLDER_TYPE = {
    "sources": "source", "products": "product", "features": "feature",
    "personas": "persona", "customers": "customer", "competitors": "competitor",
    "concepts": "concept", "initiatives": "initiative", "decisions": "decision",
    "metrics": "metric", "people": "person", "analyses": "analysis",
    "style": "style",
}
VALID_CONFIDENCE = {"high", "medium", "low", "contested"}
VALID_SOURCE_TYPE = {
    "help-doc", "slack-thread", "call-transcript", "exec-memo", "deck",
    "crm-export", "strategy-doc", "release-note", "press", "analyst-report",
    "competitor-collateral", "sales-battlecard", "product-spec", "board-doc",
    "synthesis", "other",
}
BASE_KEYS = {"title", "type", "created", "updated", "sources", "tags", "confidence"}

# Structural type-pairs where a link in one direction must be reciprocated.
# Thin generic reciprocity code, parameterized by this data table. Only genuine
# containment pairs belong here: products and features are mutually owned, so a
# one-way link is an error. Many-to-one and citation relationships (a product is
# used by many customers; an analysis cites many entities) are deliberately
# excluded — forcing the "one" side to curate-link every "many" is noise, and the
# auto-generated "## Referenced by" section already gives that discoverability.
# Extend per-org once the taxonomy is configured.
RECIPROCAL_PAIRS = {frozenset({"products", "features"})}

LINK_RE = re.compile(r"\[\[(?:[^/\]|]+/)?([^\]|]+?)(?:\|[^\]]+)?\]\]")
REFERENCED_BY_RE = re.compile(r"## Referenced by\n.*?(?=\n## |\Z)", re.DOTALL)
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
    """Return (frontmatter_dict_of_toplevel_keys, body_text). None if none."""
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


def curated_links(text):
    """Outbound [[links]] from authored + Related-pages content, excluding the
    auto-generated Referenced-by section. Reciprocity must be expressed in
    curated links, not satisfied by the auto-backlink the tool writes."""
    return set(LINK_RE.findall(REFERENCED_BY_RE.sub("", text)))


def tokens(text):
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    text = re.sub(r"[`*#|>_\-\[\]()]", " ", text)
    out = set()
    for w in re.findall(r"[a-z][a-z0-9']+", text.lower()):
        if len(w) >= 4 and w not in STOPWORDS:
            out.add(w)
    return out


# --------------------------- Tier 1 ---------------------------

def tier1(entity_pages, valid_slugs, index_targets):
    fails = []  # (check, page_relpath, detail)

    def rel(p):
        return str(p.relative_to(WIKI_ROOT))

    entity_relpaths = set()
    page_folder = {}   # stem -> folder name (or None for root pages)
    page_curated = {}  # stem -> set of curated outbound link slugs
    page_rel = {}      # stem -> relpath
    for p in entity_pages:
        r = rel(p)
        entity_relpaths.add(r)
        folder = p.parent.name if p.parent != WIKI_ROOT else None
        text = p.read_text(encoding="utf-8")
        page_folder[p.stem] = folder
        page_curated[p.stem] = curated_links(text)
        page_rel[p.stem] = r

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

        # dangling wikilinks
        for slug in LINK_RE.findall(text):
            if slug not in valid_slugs:
                fails.append(("dangling-link", r, f"[[{slug}]] resolves to nothing"))

    # typed-link reciprocity (deterministic slice of missing cross-refs)
    for stem in sorted(page_curated):
        fa = page_folder.get(stem)
        for b in sorted(page_curated[stem]):
            fb = page_folder.get(b)
            if fb is None:
                continue  # dangling or root-page target; handled elsewhere
            if frozenset({fa, fb}) in RECIPROCAL_PAIRS and stem not in page_curated.get(b, set()):
                fails.append(("reciprocity", page_rel[stem],
                              f"links to [[{b}]] ({fb}) but [[{b}]] does not link back"))

    # index coverage (only for paths that name an entity folder)
    for r in sorted(entity_relpaths - index_targets):
        fails.append(("index-missing", r, "no row in index.md"))
    for t in sorted(index_targets - entity_relpaths):
        if "/" in t and t.split("/")[0] in FOLDER_TYPE:
            fails.append(("index-stale", t, "index.md row points to missing page"))

    seen = set()
    deduped = []
    for f in fails:
        if f not in seen:
            seen.add(f)
            deduped.append(f)
    return deduped


# --------------------------- Tier 2 ---------------------------

def tier2(entity_pages):
    pages = [p for p in entity_pages if p.parent.name not in META_DIRS]
    data = {}
    inbound = {p: 0 for p in pages}
    outbound = {}
    for p in pages:
        text = p.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        ab = authored_body(body)
        data[p] = {
            "fm": fm or {},
            "tokens": tokens(ab),
            "words": len(re.findall(r"\w+", ab)),
            "body_links": bool(LINK_RE.search(ab)),
        }
        outbound[p] = set(LINK_RE.findall(text))

    stems = {p.stem: p for p in pages}
    for p in pages:
        for slug in outbound[p]:
            if slug in stems and stems[slug] is not p:
                inbound[stems[slug]] += 1

    out = {}

    out["orphans"] = sorted(
        (str(p.relative_to(WIKI_ROOT)) for p in pages if inbound[p] == 0)
    )

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
            dups.append((j, str(a.relative_to(WIKI_ROOT)), str(b.relative_to(WIKI_ROOT))))
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
            upgrade.append(f"{p.relative_to(WIKI_ROOT)} ({inbound[p]} inbound)")
    out["confidence_upgrade"] = sorted(upgrade)

    cocite = []
    for a, b in combinations(pages, 2):
        shared = outbound[a] & outbound[b]
        shared.discard(a.stem)
        shared.discard(b.stem)
        if len(shared) >= 3 and b.stem not in outbound[a] and a.stem not in outbound[b]:
            cocite.append((len(shared),
                           str(a.relative_to(WIKI_ROOT)),
                           str(b.relative_to(WIKI_ROOT))))
    out["missing_related"] = sorted(cocite, reverse=True)[:10]

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
    if not args.tier1:
        t2 = tier2(entity_pages)
        print("TIER 2  (review; ranked candidates, judgment decides)")
        labels = {
            "orphans": "orphans (no inbound links)",
            "near_duplicate": "near-duplicate pairs (prefer updating over creating)",
            "uncited": "uncited (no sources, no body links)",
            "thin": "thin pages (<80 words)",
            "confidence_upgrade": "confidence:low with >=2 inbound (upgrade?)",
            "missing_related": "missing cross-refs (>=3 shared links, not linked)",
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
                    n, a, b = it
                    print(f"      {a}  +  {b}  ({n} shared)")
                else:
                    print(f"      {it}")
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
