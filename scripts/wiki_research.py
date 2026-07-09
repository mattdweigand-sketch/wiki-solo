#!/usr/bin/env python3
"""Deterministic guardrails for the wiki-research deep-research overlay.

The script does not spawn agents or synthesize answers. It owns the checkable
policy around explicit invocation, read-only helper lanes, provenance closure,
the claim-ledger grammar, quote anchoring, and packet shape so the prose
workflow can stay thin and inspectable. Judgment (citation relevance, page
ownership of a fact, paraphrase smuggling) belongs to the citation-auditor and
reviewer lanes named in workflows/research/wiki-research.md; this validator
enforces only what is deterministic.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from _wiki_parse import frontmatter_block, split_frontmatter
from lint import KEBAB_RE, SOURCE_NONSLUG_PREFIX_RE, source_items

DEFAULT_ROOT = Path(__file__).resolve().parents[1]

TRIGGER_PHRASES = (
    "/wiki-research",
    "wiki-research",
    "deep research the wiki",
)

LEGACY_TRIGGER_PHRASES = (
    "/wiki-swarm",
    "wiki-swarm",
    "swarm the wiki answer",
)

LEGACY_TOMBSTONE = "wiki-swarm was renamed to wiki-research; re-invoke as /wiki-research"

NON_TRIGGER_EXAMPLES = (
    "be thorough",
    "use agents",
    "high-stakes wording",
    "standalone research language",
)

CLAIM_STATUSES = ("raw-verified", "wiki-backed", "raw-only", "inference")
CLAIM_FIELD_KEYS = ("wiki", "raw", "from", "status", "quote")
MAX_QUOTE_WORDS = 15

HIGH_STAKES_CATEGORIES = ("legal", "medical", "financial", "insurance", "property")
HIGH_STAKES_WIKI_NATIVE_TYPES = ("decision", "goal", "learning", "concept")

RAW_WAIVER_MARKERS = (
    "no raw provenance exists",
    "orientation question",
    "user waived raw confirmation",
)

MAX_RAW_FILES = 10

CITATION_AUDIT_MARKERS = ("citation audit", "citation-audit", "citations audited")

SCOPE_RETENTION_DIMENSIONS = (
    "material caveats",
    "status qualifiers",
    "exclusions",
    "adverse facts",
)

PAGE_RELEVANCE_TAGS = (
    "project timeline",
    "operating state",
    "condition caveat",
    "contradiction",
    "open follow-up",
    "source register",
    "cost/economics",
    "evidence gap",
)

SCOPE_RETENTION_OUTPUT_TARGETS = (
    "Claim ledger",
    "Contradictions or stale areas",
    "Answer",
    "What not to say",
    "Raw-only findings",
)

SCOPE_RETENTION_REVIEW_MARKERS = (
    "scope retention",
    "scope-retention",
    "retained caveats",
    "material caveats",
    "status qualifiers",
    "adverse facts",
)

CURRENT_STATE_OWNERS = Path("scripts") / "current-state-owners.json"


@dataclass(frozen=True)
class Lane:
    name: str
    responsibility: str
    allowed_outputs: tuple[str, ...]
    read_only: bool = True
    may_edit_files: bool = False
    may_run_durable_writes: bool = False
    may_send_external_output: bool = False
    may_decide_final_synthesis: bool = False


LANES = (
    Lane(
        name="planner",
        responsibility=(
            "Restate the question, intended output, source scope, stakes classification, "
            "raw-verification plan (closure files or waiver), scope-retention risks, "
            "and stop conditions."
        ),
        allowed_outputs=(
            "question",
            "output shape",
            "scope",
            "stakes classification",
            "raw-verification plan",
            "scope-retention risks",
            "stop conditions",
        ),
    ),
    Lane(
        name="page-scout",
        responsibility="Use wiki/index.md and wiki/primer.md to identify and narrow candidate pages.",
        allowed_outputs=("candidate pages", "consulted page list", "page relevance tags", "scope notes"),
    ),
    Lane(
        name="evidence-extractor",
        responsibility=(
            "Build the claim ledger with wiki citations, quotes, material caveats, "
            "status qualifiers, and exclusions from consulted pages; claims start "
            "wiki-backed or raw-only."
        ),
        allowed_outputs=("claim ledger", "cited facts", "quotes", "material caveats", "status qualifiers"),
    ),
    Lane(
        name="raw-verifier",
        responsibility=(
            f"Default-on: confirm ledger claims against up to {MAX_RAW_FILES} closure-named "
            "raw files with reproducible extraction, upgrade confirmed claims to "
            "raw-verified with a locator, record extraction limits, and report raw-only "
            "findings; otherwise state the waiver."
        ),
        allowed_outputs=(
            "raw files checked",
            "extraction methods",
            "extraction limits",
            "raw-verified upgrades",
            "raw-only findings",
            "waiver",
        ),
    ),
    Lane(
        name="contradiction-staleness-checker",
        responsibility="Check relevant contradictions and stale/current-state claims.",
        allowed_outputs=("contradictions", "stale areas", "open conflicts"),
    ),
    Lane(
        name="synthesizer",
        responsibility=(
            "Draft the answer from the ledger using claim-ID references, separating "
            "source-backed facts from inference and carrying forward material caveats."
        ),
        allowed_outputs=("answer draft", "claim-id references", "retained caveats", "support notes"),
    ),
    Lane(
        name="citation-auditor",
        responsibility=(
            "Judgment checks the validator cannot see: each citation supports its claim "
            "as written, each factual answer sentence maps to a referenced claim, and "
            "each high-stakes wiki-backed claim cites the page that owns the fact."
        ),
        allowed_outputs=("citation audit results", "downgrade recommendations", "unsupported-sentence findings"),
    ),
    Lane(
        name="reviewer",
        responsibility=(
            "Check citation coverage, waiver legitimacy, raw coverage, raw-only "
            "smuggling into the answer, unsupported leaps, missed pages, "
            "scope-retention gaps, stale claims, and durable-write routing."
        ),
        allowed_outputs=("review notes", "scope-retention gaps", "waiver review", "gaps", "recommended route"),
    ),
)

PACKET_SECTIONS = (
    "Verdict",
    "Question",
    "Stakes",
    "Source scope",
    "Pages consulted",
    "Lane results",
    "Claim ledger",
    "Contradictions or stale areas",
    "Raw sources checked",
    "Raw extraction limits",
    "Raw coverage",
    "Raw-only findings",
    "Answer",
    "What not to say",
    "Checks actually run",
    "Durable-write status",
    "Promotion audit",
)

VALID_VERDICTS = ("NORMAL RESEARCH", "DEEP RESEARCH", "SPLIT LANES", "STOP")
RESEARCH_VERDICTS = ("DEEP RESEARCH", "SPLIT LANES")
SECTION_RE = re.compile(r"^([A-Z][A-Za-z -]+):\s*(.*)$")
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
PATH_PAGE_RE = re.compile(r"(?:wiki/)?(?:[a-z0-9-]+/)*([a-z0-9-]+)\.md")
RAW_PATH_RE = re.compile(r"\braw/[^\s),;\]]+")
CLAIM_LINE_RE = re.compile(r"^C(\d+)\.\s*(.*)$")
CLAIM_FIELD_SPLIT_RE = re.compile(r"\|\s*(wiki|raw|from|status|quote):")
CLAIM_REF_RE = re.compile(r"\[C(\d+)\]")
FROM_ID_RE = re.compile(r"\bC(\d+)\b")
VIA_RE = re.compile(r"\bvia\b", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^([-*+]|\d+\.)\s")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s\-:|]+\|$")
FENCED_CODE_RE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
RAW_COVERAGE_RE = re.compile(
    r"(\d+)\s+raw-verified\s*/\s*(\d+)\s+wiki-backed\s*/\s*(\d+)\s+raw-only\s*/"
    r"\s*(\d+)\s+inference\s+of\s+(\d+)\s+claims\s*;\s*waiver:\s*(.+)",
    re.IGNORECASE,
)
REQUIRED_CONSULTED_PAGES = {
    "index": ("[[index]]", "wiki/index.md"),
    "primer": ("[[primer]]", "wiki/primer.md"),
}
RAW_ONLY_QUALIFIED_NONE_MARKERS = (
    "none - no raw-only findings",
    "no raw-only findings",
    "not triggered - no raw verification performed",
)
RAW_ONLY_REINGEST_MARKERS = (
    "re-ingest",
    "update source page",
    "sourcing-queue",
)
CONTRADICTION_PAGE_MARKERS = ("[[contradictions]]", "wiki/contradictions.md", "contradictions.md")
CONTRADICTION_GENERIC_MARKERS = (
    "current",
    "current-state",
    "open priorities",
    "post-close",
    "property",
    "status",
    "maintenance",
    "stale",
    "contradiction",
)
CONTRADICTION_DISMISSAL_MARKERS = (
    "none found",
    "not applicable",
    "no contradiction",
    "no contradictions",
)
CONTRADICTION_QUALIFIED_CLEAR_MARKERS = (
    "no relevant",
    "no material",
    "not relevant",
)
CITATION_INTEGRITY_FAILURE_MARKERS = (
    "citation may not support",
    "may not support",
    "could be unrelated",
    "unrelated citation",
    "citation is unrelated",
    "unsupported citation",
)
DURABLE_CLAIM_MARKERS = (
    "filed analysis",
    "analysis filed",
    "filed as wiki/analyses",
    "saved analysis",
    "saved to wiki/analyses",
    "wrote analysis",
    "wrote wiki/analyses",
    "durable write completed",
)
DURABLE_APPROVAL_PROOF_MARKERS = (
    "capture-runs.jsonl",
    "approval record",
    "approved capture record",
)
DURABLE_VALIDATION_PROOF_MARKERS = (
    "validate_capture_runs.py",
    "validate capture runs",
)
DURABLE_DESTINATION_MARKERS = (
    "primary home",
    "primary_home",
    "wiki/analyses/",
)
NEGATORS = (
    "no",
    "not",
    "never",
    "without",
    "did not",
    "didn't",
    "must not",
    "may not",
    "should not",
    "cannot",
    "can't",
)


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def has_marker(text: str, markers: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    return any(normalize(marker) in normalized for marker in markers)


def first_marker(text: str, markers: tuple[str, ...]) -> str | None:
    normalized = normalize(text)
    for marker in markers:
        if normalize(marker) in normalized:
            return marker
    return None


def canonical_page_name(raw: str) -> str:
    target = raw.split("|", 1)[0].strip()
    target = target.rstrip("/")
    if "/" in target:
        target = target.rsplit("/", 1)[-1]
    if target.endswith(".md"):
        target = target[:-3]
    return normalize(target)


def wikilinks(text: str) -> set[str]:
    return {canonical_page_name(match.group(1)) for match in WIKILINK_RE.finditer(text)}


def raw_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in RAW_PATH_RE.finditer(text):
        paths.append(match.group(0).rstrip(".,:"))
    return paths


def page_mentions(text: str) -> set[str]:
    mentions = set(wikilinks(text))
    raw_spans = [match.span() for match in RAW_PATH_RE.finditer(text)]
    for match in PATH_PAGE_RE.finditer(text):
        if any(match.start() >= start and match.end() <= end for start, end in raw_spans):
            continue
        mentions.add(normalize(match.group(1)))
    return mentions


def owner_registry_entries(root: Path) -> tuple[str, ...]:
    """Entries of scripts/current-state-owners.json as wiki-relative paths."""
    registry_path = root / CURRENT_STATE_OWNERS
    if not registry_path.is_file():
        return ()
    try:
        entries = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ()
    return tuple(entry for entry in entries if isinstance(entry, str))


def current_state_entity_markers(root: Path) -> tuple[str, ...]:
    """Entity markers derived from the current-state owner registry: each
    owned page's slug and its first-three-token prefix, in hyphen and space
    forms. Life-specific names stay in the data registry; only this
    derivation rule lives in code."""
    markers: dict[str, None] = {}
    for entry in owner_registry_entries(root):
        slug = Path(entry).stem.lower()
        prefix = "-".join(slug.split("-")[:3])
        for candidate in (slug, prefix):
            if candidate:
                markers.setdefault(candidate)
                markers.setdefault(candidate.replace("-", " "))
    return tuple(markers)


def contradiction_required_markers(root: Path) -> tuple[str, ...]:
    return CONTRADICTION_GENERIC_MARKERS + current_state_entity_markers(root)


def stakes_markers(root: Path) -> tuple[str, ...]:
    return HIGH_STAKES_CATEGORIES + current_state_entity_markers(root)


def wiki_corpus(root: Path) -> dict[str, list[Path]] | None:
    """Map of normalized page slug -> page paths under root/wiki, or None when
    the corpus directory is missing entirely."""
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        return None
    corpus: dict[str, list[Path]] = {}
    for page in wiki_dir.rglob("*.md"):
        corpus.setdefault(normalize(page.stem), []).append(page)
    return corpus


# --- Provenance closure -------------------------------------------------------


def is_contained_raw_path(ref: str, root: Path) -> bool:
    """True when `ref` is a repo-relative path that stays inside root/raw after
    full resolution: no absolute paths, no .. traversal, no symlink escapes."""
    path = Path(ref)
    if path.is_absolute() or ".." in path.parts:
        return False
    try:
        resolved = (root / path).resolve()
        raw_root = (root / "raw").resolve()
    except OSError:
        return False
    return raw_root in resolved.parents


RAW_CONTAINMENT_RULE = "must stay inside raw/ (no absolute paths, traversal, or symlink escapes)"


@dataclass
class Closure:
    """Raw paths reachable from a page set through frontmatter provenance."""

    raw_paths: set[str] = field(default_factory=set)
    dangling: list[str] = field(default_factory=list)


def page_rel(page: Path, root: Path) -> str:
    try:
        return str(page.relative_to(root))
    except ValueError:
        return str(page)


def _page_provenance(page: Path, root: Path) -> tuple[list[str], list[Path], list[str]]:
    """One page's direct provenance: (raw paths, referenced pages, dangling refs).

    Items follow the SCHEMA.md sources: grammar via lint's source_items, plus a
    repo-relative authority_ref. URLs and prefixed free text terminate."""
    text = page.read_text(encoding="utf-8")
    block = frontmatter_block(text)
    fm, _ = split_frontmatter(text)
    items = source_items(block)
    aref = ((fm or {}).get("authority_ref") or "").strip().strip("\"'")
    if aref:
        items.append(aref)

    raws: list[str] = []
    refs: list[Path] = []
    dangling: list[str] = []
    for item in items:
        if item.startswith("raw/"):
            ref = item.rstrip(".,:")
            if is_contained_raw_path(ref, root):
                raws.append(ref)
            else:
                dangling.append(
                    f"unsafe raw path '{ref}' (referenced from {page_rel(page, root)}) "
                    f"{RAW_CONTAINMENT_RULE}"
                )
        elif "://" in item or item.startswith("http"):
            continue
        elif SOURCE_NONSLUG_PREFIX_RE.match(item):
            continue
        elif item.startswith("wiki/") and item.endswith(".md"):
            target = root / item
            if target.is_file():
                refs.append(target)
            else:
                dangling.append(f"{item} (referenced from {page_rel(page, root)})")
        elif KEBAB_RE.match(item):
            target = root / "wiki" / "sources" / f"{item}.md"
            if target.is_file():
                refs.append(target)
            else:
                dangling.append(
                    f"sources slug '{item}' (referenced from {page_rel(page, root)}) "
                    "matches no wiki/sources/ page"
                )
    return raws, refs, dangling


def provenance_closure(
    start_pages: list[Path], root: Path, restrict_to: set[Path] | None = None
) -> Closure:
    """Breadth-first provenance closure over frontmatter references.

    With restrict_to set, traversal only continues through pages in that set:
    the raw paths found are exactly those with at least one fully consulted
    resolution chain. Dangling references fail closed at the call sites that
    need the closure (waiver truth, wiki-backed eligibility)."""
    closure = Closure()
    seen: set[Path] = set()
    queue = list(start_pages)
    while queue:
        page = queue.pop(0)
        if page in seen:
            continue
        seen.add(page)
        if not page.is_file():
            closure.dangling.append(page_rel(page, root))
            continue
        raws, refs, dangling = _page_provenance(page, root)
        closure.raw_paths.update(raws)
        closure.dangling.extend(dangling)
        for ref in refs:
            if restrict_to is not None and ref not in restrict_to:
                continue
            queue.append(ref)
    return closure


# --- Claim ledger ---------------------------------------------------------------


@dataclass
class Claim:
    number: int
    text: str
    fields: dict[str, str]

    @property
    def status(self) -> str:
        return self.fields.get("status", "").strip()

    @property
    def wiki_links(self) -> set[str]:
        return wikilinks(self.fields.get("wiki", ""))

    @property
    def raw_refs(self) -> list[str]:
        return raw_paths(self.fields.get("raw", ""))

    @property
    def quote(self) -> str:
        return self.fields.get("quote", "").strip().strip('"').strip()

    @property
    def from_ids(self) -> list[int]:
        return [int(m.group(1)) for m in FROM_ID_RE.finditer(self.fields.get("from", ""))]


def parse_claim_ledger(section_text: str) -> tuple[list[Claim], list[str]]:
    claims: list[Claim] = []
    problems: list[str] = []
    for line in section_text.splitlines():
        if not line.strip():
            continue
        match = CLAIM_LINE_RE.match(line.strip())
        if not match:
            problems.append(
                f"Claim ledger contains a non-claim line (claims are single-line, C<n>. ...): "
                f"{line.strip()[:60]!r}"
            )
            continue
        number = int(match.group(1))
        parts = CLAIM_FIELD_SPLIT_RE.split(match.group(2))
        text = parts[0].strip()
        fields: dict[str, str] = {}
        for key, value in zip(parts[1::2], parts[2::2]):
            if key in fields:
                problems.append(
                    f"C{number} has a duplicate '{key}' field (a recognized delimiter "
                    "inside a field value parses loudly; rephrase)"
                )
            fields[key] = value.strip()
        for key, value in fields.items():
            if "|" in value:
                problems.append(f"C{number} field '{key}' must not contain a pipe character")
        claims.append(Claim(number=number, text=text, fields=fields))
    ids = [claim.number for claim in claims]
    if ids != list(range(1, len(ids) + 1)):
        problems.append("claim IDs must be unique and sequential from C1")
    return claims, problems


def validate_claims(
    claims: list[Claim],
    consulted_pages: set[str],
    checked_raw: list[str],
    raw_only_findings: str,
    root: Path,
) -> list[str]:
    problems: list[str] = []
    ids = {claim.number for claim in claims}
    for claim in claims:
        label = f"C{claim.number}"
        status = claim.status
        if status not in CLAIM_STATUSES:
            problems.append(f"{label} has invalid status: {status or '<missing>'}")
            continue
        if status == "raw-verified":
            if not claim.wiki_links:
                problems.append(f"{label} (raw-verified) requires a wiki: field with a wikilink")
            if not claim.raw_refs:
                problems.append(f"{label} (raw-verified) requires a raw: field with a raw/ path")
            if not claim.quote:
                problems.append(f"{label} (raw-verified) requires a quote: field")
        elif status == "wiki-backed":
            if not claim.wiki_links:
                problems.append(f"{label} (wiki-backed) requires a wiki: field with a wikilink")
            if not claim.quote:
                problems.append(f"{label} (wiki-backed) requires a quote: field")
            if claim.raw_refs:
                problems.append(
                    f"{label} (wiki-backed) must not carry a raw: field; raw-confirmed claims are raw-verified"
                )
        elif status == "raw-only":
            if not claim.raw_refs:
                problems.append(f"{label} (raw-only) requires a raw: field with a raw/ path")
            if claim.fields.get("quote"):
                problems.append(f"{label} (raw-only) must not carry a quote (raw text may not be excerpted)")
            if not re.search(rf"\b{label}\b", raw_only_findings):
                problems.append(f"{label} (raw-only) must be reflected in Raw-only findings")
        elif status == "inference":
            if not claim.fields.get("from"):
                problems.append(f"{label} (inference) requires a from: field")
            for from_id in claim.from_ids:
                if from_id not in ids:
                    problems.append(f"{label} (inference) references unknown claim C{from_id}")
        for slug in sorted(claim.wiki_links):
            if slug not in consulted_pages:
                problems.append(f"{label} cites [[{slug}]] which is not in Pages consulted")
        for ref in claim.raw_refs:
            if ref not in checked_raw:
                problems.append(f"{label} cites {ref} which is not listed in Raw sources checked")
            if not is_contained_raw_path(ref, root):
                problems.append(f"{label} cites {ref} which {RAW_CONTAINMENT_RULE}")
            elif not (root / ref).is_file():
                problems.append(f"{label} cites {ref} which does not exist on disk")
    return problems


# --- Quote anchoring ---------------------------------------------------------------


def _strip_section(text: str, heading: str) -> str:
    return re.sub(rf"## {heading}\n.*?(?=\n## |\Z)", "", text, flags=re.DOTALL)


def evidentiary_body(text: str) -> str:
    """Page text minus frontmatter, generated/curated link sections, and
    fenced code blocks: the only regions a ledger quote may anchor to."""
    match = re.match(r"^---\n.*?\n---\n?", text, re.DOTALL)
    if match:
        text = text[match.end():]
    text = _strip_section(text, "Referenced by")
    text = _strip_section(text, "Related pages")
    text = FENCED_CODE_RE.sub(" ", text)
    return text


def validate_quotes(claims: list[Claim], corpus: dict[str, list[Path]]) -> list[str]:
    problems: list[str] = []
    for claim in claims:
        if claim.status not in ("raw-verified", "wiki-backed"):
            continue
        quote = claim.quote
        if not quote:
            continue  # missing quote already reported by validate_claims
        label = f"C{claim.number}"
        if len(quote.split()) > MAX_QUOTE_WORDS:
            problems.append(f"{label} quote exceeds {MAX_QUOTE_WORDS} words")
            continue
        needle = normalize(quote)
        found = False
        for slug in claim.wiki_links:
            for page in corpus.get(slug, []):
                body = normalize(evidentiary_body(page.read_text(encoding="utf-8")))
                if needle and needle in body:
                    found = True
                    break
            if found:
                break
        if not found:
            problems.append(
                f"{label} quote is not found in the evidentiary body of any cited page"
            )
    return problems


# --- Answer grammar and eligibility ---------------------------------------------------


def answer_units(section_text: str) -> tuple[list[str], list[str]]:
    units: list[str] = []
    problems: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            units.append(" ".join(paragraph))
            paragraph.clear()

    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith(("#", ">", "<")):
            problems.append(
                f"Answer must not contain heading, blockquote, or HTML lines: {stripped[:50]!r}"
            )
            continue
        if LIST_ITEM_RE.match(stripped):
            flush()
            units.append(stripped)
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            flush()
            if TABLE_SEPARATOR_RE.match(stripped):
                continue
            units.append(stripped)
            continue
        paragraph.append(stripped)
    flush()
    return units, problems


def high_stakes_page_problems(
    slug: str, corpus: dict[str, list[Path]], root: Path, owner_entries: tuple[str, ...]
) -> list[str]:
    """Why the pages behind `slug` disqualify a wiki-backed claim from a
    high-stakes answer, empty when every page qualifies. Order per spec:
    analysis exclusion first, then empty closure, then native-type or
    owner-registry membership."""
    problems: list[str] = []
    for page in corpus.get(slug, []):
        fm, _ = split_frontmatter(page.read_text(encoding="utf-8"))
        page_type = ((fm or {}).get("type") or "").strip()
        if page_type == "analysis":
            problems.append(
                f"[[{slug}]] is a type: analysis page, excluded before both eligibility branches"
            )
            continue
        closure = provenance_closure([page], root)
        if closure.dangling:
            problems.append(
                f"[[{slug}]] has a dangling provenance reference: {closure.dangling[0]}"
            )
            continue
        if closure.raw_paths:
            problems.append(
                f"[[{slug}]] has raw provenance in its closure; the claim must be raw-verified"
            )
            continue
        wiki_rel = page_rel(page, root / "wiki")
        if page_type not in HIGH_STAKES_WIKI_NATIVE_TYPES and wiki_rel not in owner_entries:
            problems.append(
                f"[[{slug}]] (type: {page_type or 'unknown'}) is neither wiki-native nor owner-registered"
            )
    return problems


def answer_eligibility_problems(
    referenced: list[int],
    claims_by_id: dict[int, Claim],
    corpus: dict[str, list[Path]],
    root: Path,
) -> list[str]:
    owner_entries = owner_registry_entries(root)
    memo: dict[int, list[str]] = {}

    def eligibility(claim_id: int, stack: tuple[int, ...]) -> list[str]:
        if claim_id in memo:
            return memo[claim_id]
        if claim_id in stack:
            return [f"C{claim_id} inference ancestry is cyclic"]
        claim = claims_by_id.get(claim_id)
        if claim is None:
            return []  # unknown IDs are reported by the anchoring pass
        problems: list[str] = []
        if claim.status == "wiki-backed":
            for slug in sorted(claim.wiki_links):
                problems.extend(high_stakes_page_problems(slug, corpus, root, owner_entries))
        elif claim.status == "raw-only":
            problems.append(f"C{claim_id} is raw-only and can never be answer-eligible")
        elif claim.status == "inference":
            for from_id in claim.from_ids:
                for problem in eligibility(from_id, stack + (claim_id,)):
                    problems.append(f"C{claim_id} inherits ineligibility: {problem}")
        memo[claim_id] = problems
        return problems

    problems: list[str] = []
    for claim_id in referenced:
        for problem in eligibility(claim_id, ()):
            problems.append(f"high-stakes answer claim C{claim_id}: {problem}")
    seen: set[str] = set()
    unique: list[str] = []
    for problem in problems:
        if problem not in seen:
            seen.add(problem)
            unique.append(problem)
    return unique


# --- Registry / manifest ----------------------------------------------------------------


def registry(root: Path = DEFAULT_ROOT) -> dict[str, object]:
    return {
        "trigger_phrases": TRIGGER_PHRASES,
        "legacy_trigger_phrases": LEGACY_TRIGGER_PHRASES,
        "legacy_tombstone": LEGACY_TOMBSTONE,
        "non_trigger_examples": NON_TRIGGER_EXAMPLES,
        "lanes": [asdict(lane) for lane in LANES],
        "packet_sections": PACKET_SECTIONS,
        "valid_verdicts": VALID_VERDICTS,
        "research_verdicts": RESEARCH_VERDICTS,
        "claim_statuses": CLAIM_STATUSES,
        "claim_field_keys": CLAIM_FIELD_KEYS,
        "max_quote_words": MAX_QUOTE_WORDS,
        "high_stakes_categories": HIGH_STAKES_CATEGORIES,
        "high_stakes_wiki_native_types": HIGH_STAKES_WIKI_NATIVE_TYPES,
        "raw_waiver_markers": RAW_WAIVER_MARKERS,
        "max_raw_files": MAX_RAW_FILES,
        "citation_audit_markers": CITATION_AUDIT_MARKERS,
        "required_consulted_pages": tuple(REQUIRED_CONSULTED_PAGES),
        "scope_retention_dimensions": SCOPE_RETENTION_DIMENSIONS,
        "page_relevance_tags": PAGE_RELEVANCE_TAGS,
        "scope_retention_output_targets": SCOPE_RETENTION_OUTPUT_TARGETS,
        "scope_retention_review_markers": SCOPE_RETENTION_REVIEW_MARKERS,
        "raw_only_qualified_none_markers": RAW_ONLY_QUALIFIED_NONE_MARKERS,
        "raw_only_reingest_markers": RAW_ONLY_REINGEST_MARKERS,
        "citation_integrity_failure_markers": CITATION_INTEGRITY_FAILURE_MARKERS,
        "contradiction_page_markers": CONTRADICTION_PAGE_MARKERS,
        "contradiction_page_required_when": contradiction_required_markers(root),
        "current_state_owner_registry": str(CURRENT_STATE_OWNERS),
        "answer_eligibility_registry": str(CURRENT_STATE_OWNERS),
        "contradiction_dismissal_markers": CONTRADICTION_DISMISSAL_MARKERS,
        "durable_write_claim_markers": DURABLE_CLAIM_MARKERS,
        "durable_write_approval_proof_markers": DURABLE_APPROVAL_PROOF_MARKERS,
        "durable_write_validation_proof_markers": DURABLE_VALIDATION_PROOF_MARKERS,
        "durable_write_destination_markers": DURABLE_DESTINATION_MARKERS,
        "analysis_capture_owner": "workflows/research/CONTEXT.md#analysis-capture",
    }


def print_manifest(*, root: Path = DEFAULT_ROOT, json_mode: bool = False) -> None:
    if json_mode:
        print(json.dumps(registry(root), indent=2, sort_keys=True))
        return
    print("WIKI-RESEARCH MANIFEST")
    print("Trigger phrases:")
    for trigger in TRIGGER_PHRASES:
        print(f"- {trigger}")
    print("Legacy trigger phrases (rejected with a rename tombstone):")
    for trigger in LEGACY_TRIGGER_PHRASES:
        print(f"- {trigger}")
    print("Non-trigger examples:")
    for example in NON_TRIGGER_EXAMPLES:
        print(f"- {example}")
    print("Claim statuses:")
    for status in CLAIM_STATUSES:
        print(f"- {status}")
    print("Claim field keys:")
    for key in CLAIM_FIELD_KEYS:
        print(f"- {key}")
    print(f"Max quote words: {MAX_QUOTE_WORDS}")
    print("High-stakes categories:")
    for category in HIGH_STAKES_CATEGORIES:
        print(f"- {category}")
    print("High-stakes wiki-native types:")
    for page_type in HIGH_STAKES_WIKI_NATIVE_TYPES:
        print(f"- {page_type}")
    print(f"Answer-eligibility registry: {CURRENT_STATE_OWNERS}")
    print("Raw waiver markers:")
    for marker in RAW_WAIVER_MARKERS:
        print(f"- {marker}")
    print(f"Max raw files: {MAX_RAW_FILES}")
    print("Scope-retention dimensions:")
    for dimension in SCOPE_RETENTION_DIMENSIONS:
        print(f"- {dimension}")
    print("Page relevance tags:")
    for tag in PAGE_RELEVANCE_TAGS:
        print(f"- {tag}")
    print("Scope-retention output targets:")
    for target in SCOPE_RETENTION_OUTPUT_TARGETS:
        print(f"- {target}")
    print("Lanes:")
    for lane in LANES:
        print(f"- {lane.name}: read_only={str(lane.read_only).lower()}; {lane.responsibility}")
    print("Packet sections:")
    for section in PACKET_SECTIONS:
        print(f"- {section}")


# --- Preflight -----------------------------------------------------------------------------


def has_explicit_trigger(question: str) -> bool:
    text = normalize(question)
    return any(trigger in text for trigger in TRIGGER_PHRASES)


def has_legacy_trigger(question: str) -> bool:
    text = normalize(question)
    return any(trigger in text for trigger in LEGACY_TRIGGER_PHRASES)


def is_standalone_research(question: str) -> bool:
    text = normalize(question)
    return bool(re.search(r"\b(research|swarm)\b", text)) and not has_explicit_trigger(question)


def run_preflight(question: str, *, json_mode: bool = False) -> int:
    accepted = has_explicit_trigger(question)
    legacy = not accepted and has_legacy_trigger(question)
    if json_mode:
        if accepted:
            reason = "explicit wiki-research trigger"
        elif legacy:
            reason = LEGACY_TOMBSTONE
        else:
            reason = "no explicit wiki-research trigger"
        print(json.dumps({
            "accepted": accepted,
            "reason": reason,
            "legacy_trigger": legacy,
            "standalone_research": is_standalone_research(question),
            "lanes": [asdict(lane) for lane in LANES] if accepted else [],
        }, indent=2, sort_keys=True))
        return 0 if accepted else 2

    if not accepted:
        print("WIKI-RESEARCH PREFLIGHT: REJECTED")
        if legacy:
            print(f"Reason: {LEGACY_TOMBSTONE}.")
        elif is_standalone_research(question):
            print("Reason: standalone research/swarm language is not enough; use the explicit wiki-research boundary.")
        else:
            print("Reason: no explicit wiki-research trigger. Use normal research.")
        return 2

    print("WIKI-RESEARCH PREFLIGHT: ACCEPTED")
    print("Reason: explicit wiki-research trigger.")
    print("Raw confirmation is the default; helper lanes are read-only and may not edit files, run durable writes, send external output, or decide final synthesis.")
    print("Required lanes:")
    for lane in LANES:
        print(f"- {lane.name}: {lane.responsibility}")
    return 0


# --- Packet validation ------------------------------------------------------------------------


def packet_sections(text: str) -> tuple[dict[str, str], list[str]]:
    """Split packet text into its recognized sections.

    Returns (sections, structural problems). A repeated section heading is a
    validation error and its content is appended to the first occurrence, so
    no user-visible packet text can escape validation by shadowing an earlier
    section. Non-empty text before the first recognized section (other than
    the packet header line) is also an error for the same reason."""
    sections: dict[str, list[str]] = {}
    problems: list[str] = []
    current: str | None = None
    for line in text.splitlines():
        match = SECTION_RE.match(line)
        if match and match.group(1) in PACKET_SECTIONS:
            name = match.group(1)
            if name in sections:
                problems.append(f"duplicate packet section: {name}")
                sections[name].append(match.group(2))
            else:
                sections[name] = [match.group(2)]
            current = name
            continue
        if current:
            sections[current].append(line)
            continue
        stripped = line.strip()
        if stripped and stripped != "WIKI-RESEARCH PACKET":
            problems.append(
                f"packet contains text outside recognized sections: {stripped[:60]!r}"
            )
    return {key: "\n".join(value).strip() for key, value in sections.items()}, problems


def non_stop_verdict(verdict: str) -> bool:
    return bool(verdict) and verdict != "STOP"


def needs_contradiction_page(sections: dict[str, str], root: Path) -> bool:
    combined = " ".join(
        sections.get(section, "")
        for section in ("Question", "Source scope", "Pages consulted", "Answer")
    )
    return has_marker(combined, contradiction_required_markers(root))


def expected_high_stakes(sections: dict[str, str], root: Path) -> bool:
    combined = " ".join(
        sections.get(section, "")
        for section in ("Question", "Source scope", "Pages consulted", "Answer")
    )
    return has_marker(combined, stakes_markers(root))


def declared_stakes(sections: dict[str, str]) -> str:
    line = sections.get("Stakes", "").splitlines()[0].strip() if sections.get("Stakes") else ""
    lowered = normalize(line)
    if lowered.startswith("standard"):
        return "standard"
    if lowered.startswith("high"):
        return "high"
    return ""


def has_self_disclaimed_citation_support(text: str) -> bool:
    return has_marker(text, CITATION_INTEGRITY_FAILURE_MARKERS)


def has_unqualified_contradiction_dismissal(text: str) -> bool:
    if has_marker(text, CONTRADICTION_QUALIFIED_CLEAR_MARKERS):
        return False
    return has_marker(text, CONTRADICTION_DISMISSAL_MARKERS)


def has_qualified_raw_only_none(text: str) -> bool:
    return has_marker(text, RAW_ONLY_QUALIFIED_NONE_MARKERS)


def has_raw_only_finding(text: str) -> bool:
    return bool(text.strip()) and not has_qualified_raw_only_none(text)


def is_negated(prefix: str) -> bool:
    prefix = normalize(prefix)
    return any(prefix.endswith(f"{negator} ") or prefix.endswith(negator) for negator in NEGATORS)


def has_unnegated_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    normalized = normalize(text)
    for phrase in phrases:
        pattern = re.escape(normalize(phrase))
        for match in re.finditer(pattern, normalized):
            prefix = normalized[max(0, match.start() - 40):match.start()]
            if is_negated(prefix):
                continue
            return True
    return False


def validate_packet_text(text: str, root: Path = DEFAULT_ROOT) -> list[str]:
    problems: list[str] = []
    stripped = text.lstrip()
    if not stripped.startswith("WIKI-RESEARCH PACKET"):
        problems.append("packet must start with WIKI-RESEARCH PACKET")

    sections, structural_problems = packet_sections(text)
    problems.extend(structural_problems)
    for section in PACKET_SECTIONS:
        if section not in sections:
            problems.append(f"missing packet section: {section}")

    verdict = sections.get("Verdict", "").splitlines()[0].strip() if sections.get("Verdict") else ""
    if verdict not in VALID_VERDICTS:
        problems.append(f"invalid verdict: {verdict or '<empty>'}")

    checks = normalize(sections.get("Checks actually run", ""))
    proposed_markers = ("proposed", "planned", "would run", "should run", "not yet run")
    if any(marker in checks for marker in proposed_markers):
        problems.append("Checks actually run must not list proposed or planned checks")
    if non_stop_verdict(verdict) and "preflight" not in checks:
        problems.append("Checks actually run must include preflight for non-STOP packets")

    if not non_stop_verdict(verdict):
        return problems

    # Stakes
    stakes = declared_stakes(sections)
    if stakes not in ("standard", "high"):
        problems.append("Stakes must declare standard or high (<categories>)")
    if expected_high_stakes(sections, root) and stakes == "standard":
        problems.append(
            "Stakes must be high: the question, scope, consulted pages, or answer hit "
            "high-stakes or current-state markers"
        )
    high_stakes = stakes == "high"
    if high_stakes and verdict == "NORMAL RESEARCH":
        problems.append("Stakes: high is incompatible with Verdict: NORMAL RESEARCH")

    # Pages consulted
    pages = sections.get("Pages consulted", "")
    consulted_pages = page_mentions(pages)
    for page_name, markers in REQUIRED_CONSULTED_PAGES.items():
        if not has_marker(pages, markers):
            problems.append(f"Pages consulted must include [[{page_name}]] for non-STOP packets")

    corpus = wiki_corpus(root)
    if corpus is None:
        problems.append(f"wiki corpus not found under {root}")
        return problems
    unknown_pages = sorted(slug for slug in consulted_pages if slug not in corpus)
    if unknown_pages:
        problems.append(
            f"Pages consulted lists pages not in the wiki corpus: {', '.join(unknown_pages)}"
        )
    consulted_paths: set[Path] = set()
    for slug in consulted_pages:
        consulted_paths.update(corpus.get(slug, []))

    # Raw sources checked
    raw_checked = sections.get("Raw sources checked", "")
    raw_limits = sections.get("Raw extraction limits", "")
    raw_only = sections.get("Raw-only findings", "")
    checked_raw_paths = raw_paths(raw_checked)
    waiver_marker = first_marker(raw_checked, RAW_WAIVER_MARKERS)
    if not raw_checked.strip():
        problems.append(
            "Raw sources checked must list checked files or state a waiver for non-STOP packets"
        )
    elif not checked_raw_paths and waiver_marker is None:
        problems.append(
            "Raw sources checked must list raw files or state a waiver from the "
            "runtime waiver vocabulary (raw confirmation is the default)"
        )
    for line in raw_checked.splitlines():
        if raw_paths(line) and not VIA_RE.search(line):
            problems.append(
                f"Raw sources checked line must name its extraction method with 'via': {line.strip()[:60]!r}"
            )
    for checked_path in checked_raw_paths:
        if not is_contained_raw_path(checked_path, root):
            problems.append(
                f"Raw sources checked lists {checked_path} which {RAW_CONTAINMENT_RULE}"
            )
    if len(checked_raw_paths) > MAX_RAW_FILES:
        problems.append(f"Raw sources checked must list no more than {MAX_RAW_FILES} raw/ paths")
    if checked_raw_paths:
        consulted_closure = provenance_closure(
            sorted(consulted_paths), root, restrict_to=consulted_paths
        )
        for checked_path in checked_raw_paths:
            if checked_path not in consulted_closure.raw_paths:
                problems.append(
                    f"Raw sources checked lists {checked_path} which has no fully consulted "
                    "resolution chain from a consulted page"
                )
        if not raw_limits.strip():
            problems.append("Raw extraction limits must be stated when raw sources are checked")
    if high_stakes and not checked_raw_paths:
        if waiver_marker is not None and waiver_marker != "no raw provenance exists":
            problems.append(
                "high-stakes packets accept only the 'no raw provenance exists' waiver"
            )
        if waiver_marker == "no raw provenance exists":
            full_closure = provenance_closure(sorted(consulted_paths), root)
            for dangling in full_closure.dangling:
                problems.append(
                    f"high-stakes waiver cannot be verified: dangling provenance reference: {dangling}"
                )
            if not full_closure.dangling and full_closure.raw_paths:
                problems.append(
                    "high-stakes 'no raw provenance exists' waiver is false: the provenance "
                    f"closure of consulted pages names {sorted(full_closure.raw_paths)[0]}"
                )

    # Claim ledger
    ledger_text = sections.get("Claim ledger", "")
    claims, ledger_problems = parse_claim_ledger(ledger_text)
    problems.extend(ledger_problems)
    claims_by_id = {claim.number: claim for claim in claims}
    if not claims:
        problems.append("Claim ledger must contain at least one claim for non-STOP packets")
    problems.extend(validate_claims(claims, consulted_pages, checked_raw_paths, raw_only, root))
    problems.extend(validate_quotes(claims, corpus))
    if has_self_disclaimed_citation_support(ledger_text):
        problems.append("Claim ledger must not disclaim or weaken its own citation support")

    # Raw coverage
    coverage_text = sections.get("Raw coverage", "")
    coverage_match = RAW_COVERAGE_RE.search(coverage_text)
    if not coverage_match:
        problems.append(
            "Raw coverage must state '<a> raw-verified / <b> wiki-backed / <c> raw-only / "
            "<d> inference of <n> claims; waiver: <none|marker>'"
        )
    else:
        tallies = {status: 0 for status in CLAIM_STATUSES}
        for claim in claims:
            if claim.status in tallies:
                tallies[claim.status] += 1
        stated = [int(coverage_match.group(i)) for i in range(1, 6)]
        actual = [
            tallies["raw-verified"],
            tallies["wiki-backed"],
            tallies["raw-only"],
            tallies["inference"],
            len(claims),
        ]
        if stated != actual:
            problems.append(
                f"Raw coverage counts {stated} do not match the claim ledger {actual}"
            )
        coverage_waiver = coverage_match.group(6).strip()
        if checked_raw_paths and normalize(coverage_waiver) != "none":
            problems.append("Raw coverage waiver must be 'none' when raw files were checked")
        if waiver_marker is not None and normalize(waiver_marker) not in normalize(coverage_waiver):
            problems.append(
                "Raw coverage waiver must repeat the waiver stated in Raw sources checked"
            )

    # Raw-only findings
    if has_raw_only_finding(raw_only):
        if not checked_raw_paths:
            problems.append("Raw-only findings require at least one raw file in Raw sources checked")
        if not has_marker(raw_only, RAW_ONLY_REINGEST_MARKERS):
            problems.append(
                "Raw-only findings must recommend re-ingest, source-page update, or sourcing-queue follow-up"
            )

    # Contradictions
    contradictions = sections.get("Contradictions or stale areas", "")
    if needs_contradiction_page(sections, root):
        if not has_marker(pages, CONTRADICTION_PAGE_MARKERS):
            problems.append(
                "current-state, property, or contradiction-sensitive packets must consult [[contradictions]]"
            )
        if not has_marker(contradictions, CONTRADICTION_PAGE_MARKERS):
            problems.append(
                "Contradictions or stale areas must cite [[contradictions]] for contradiction-sensitive packets"
            )
        if has_unqualified_contradiction_dismissal(contradictions):
            problems.append(
                "Contradictions or stale areas must not dismiss a contradiction-sensitive packet as none or not applicable without a relevance-qualified register note"
            )

    # Answer
    answer = sections.get("Answer", "")
    units, grammar_problems = answer_units(answer)
    problems.extend(grammar_problems)
    referenced_ids: list[int] = []
    for unit in units:
        unit_ids = [int(m.group(1)) for m in CLAIM_REF_RE.finditer(unit)]
        referenced_ids.extend(unit_ids)
        if not unit_ids:
            problems.append(
                f"Answer unit must reference at least one ledger claim ID: {unit[:60]!r}"
            )
    if not units:
        problems.append("Answer must contain at least one anchored unit")
    for claim_id in sorted(set(referenced_ids)):
        claim = claims_by_id.get(claim_id)
        if claim is None:
            problems.append(f"Answer references unknown claim C{claim_id}")
        elif claim.status == "raw-only":
            problems.append(
                f"Answer must not reference raw-only claim C{claim_id}; raw-only findings "
                "live only in Raw-only findings"
            )
    for slug in sorted(wikilinks(answer)):
        if slug not in consulted_pages:
            problems.append(f"Answer cites [[{slug}]] which is not in Pages consulted")
    for ref in raw_paths(answer):
        if ref not in checked_raw_paths:
            problems.append(f"Answer cites {ref} which is not listed in Raw sources checked")
    if has_self_disclaimed_citation_support(answer):
        problems.append("Answer must not disclaim or weaken its own citation support")
    if high_stakes:
        known_ids = [
            claim_id for claim_id in sorted(set(referenced_ids)) if claim_id in claims_by_id
        ]
        problems.extend(answer_eligibility_problems(known_ids, claims_by_id, corpus, root))

    # Lane results
    lane_results = normalize(sections.get("Lane results", ""))
    if not has_marker(lane_results, SCOPE_RETENTION_REVIEW_MARKERS):
        problems.append("Lane results must include a scope-retention review for non-STOP packets")
    if verdict in RESEARCH_VERDICTS:
        for lane in LANES:
            if not has_marker(lane_results, (lane.name, lane.name.replace("-", " "))):
                problems.append(
                    f"Lane results must report the {lane.name} lane for research-verdict packets"
                )
        if not has_marker(lane_results, CITATION_AUDIT_MARKERS):
            problems.append(
                "Lane results must report the citation audit for research-verdict packets"
            )
    if has_unnegated_phrase(
        lane_results,
        (
            "edit files",
            "edited file",
            "edited files",
            "write files",
            "wrote file",
            "wrote files",
            "durable write",
            "sent external",
            "sent external output",
        ),
    ):
        problems.append("helper lanes must stay read-only and non-writing")

    # Durable-write status
    durable = normalize(sections.get("Durable-write status", ""))
    if has_unnegated_phrase(durable, DURABLE_CLAIM_MARKERS):
        if has_raw_only_finding(raw_only):
            problems.append("packets with raw-only findings must not claim an analysis was filed")
        if "analysis-capture" not in durable and "workflows/research/context.md#analysis-capture" not in durable:
            problems.append("durable analysis filing must route through normal research analysis-capture")
        if not has_marker(durable, DURABLE_APPROVAL_PROOF_MARKERS):
            problems.append("durable analysis filing must name an approval record such as scripts/capture-runs.jsonl")
        if not has_marker(durable, DURABLE_VALIDATION_PROOF_MARKERS):
            problems.append("durable analysis filing must name validate_capture_runs.py proof")
        if not has_marker(durable, DURABLE_DESTINATION_MARKERS):
            problems.append("durable analysis filing must name the primary destination")
    if has_unnegated_phrase(durable, ("bypassed", "direct write", "without approval")):
        problems.append("durable-write status claims a bypass or direct write")

    return problems


def run_validate_packet(path: Path, *, root: Path = DEFAULT_ROOT, json_mode: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    problems = validate_packet_text(text, root)
    if json_mode:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2, sort_keys=True))
    elif problems:
        print("WIKI-RESEARCH PACKET: INVALID")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("WIKI-RESEARCH PACKET: valid")
    return 1 if problems else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deterministic guardrails for wiki-research.")
    sub = p.add_subparsers(dest="command", required=True)

    manifest = sub.add_parser("manifest", help="Print canonical research policy.")
    manifest.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repo root holding the current-state owner registry (default: this repo).",
    )
    manifest.add_argument("--json", action="store_true", help="Emit JSON.")

    preflight = sub.add_parser("preflight", help="Check whether a request explicitly invokes wiki-research.")
    preflight.add_argument("--question", required=True)
    preflight.add_argument("--json", action="store_true", help="Emit JSON.")

    validate = sub.add_parser("validate-packet", help="Validate a completed WIKI-RESEARCH PACKET.")
    validate.add_argument("--packet", required=True, type=Path)
    validate.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repo root holding the wiki corpus to validate against (default: this repo).",
    )
    validate.add_argument("--json", action="store_true", help="Emit JSON.")
    return p


def main() -> int:
    args = parser().parse_args()
    if args.command == "manifest":
        print_manifest(root=args.root, json_mode=args.json)
        return 0
    if args.command == "preflight":
        return run_preflight(args.question, json_mode=args.json)
    if args.command == "validate-packet":
        return run_validate_packet(args.packet, root=args.root, json_mode=args.json)
    raise AssertionError(f"unknown command {args.command}")


if __name__ == "__main__":
    sys.exit(main())
