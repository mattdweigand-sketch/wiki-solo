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
orphans, uncited pages, compiled pages with newer source inputs, review dates,
log growth, and sourcing-queue count drift) and surfaces them for a human or
agent to adjudicate. Tier 2 never fails the run unless --strict is passed.

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
import shlex
import subprocess
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

from _file_transactions import transaction_status
from _repo_paths import HTTP_URL_RE, EXISTING_FILE, RepoPathError, is_http_url, resolve_repo_path
from _wiki_parse import (
    FrontmatterError,
    LINK_RE,
    META_PAGES,
    authored_body_view,
    authored_link_view,
    dangling_slugs,
    evidentiary_view,
    frontmatter_block,
    get_entity_pages,
    parse_log_entry_date,
    parse_log_entry_type,
    section_body,
    status_review_view,
    strip_body_sections,
    strip_sections,
    split_frontmatter,
    split_quoted_csv,
)
from review_due import collect as collect_review_due

WIKI_ROOT = Path("wiki")
ADJUDICATIONS_PATH = Path("scripts/lint-adjudications.json")
LOG_ROTATION_WARN_LINES = 2500
# Date-only log entries before this cutoff predate the structured stale-text
# sweep proof template. Do not rewrite old history just to satisfy this check.
STALE_SWEEP_PROOF_REQUIRED_FROM = date(2026, 7, 5)

# META_PAGES is shared with rebuild_referenced_by.py via _wiki_parse, so the
# corpus enumeration cannot drift between linter and rebuild.

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
    ".claude", ".codex", ".github", ".git", ".wiki-transactions", "archive", "deliverables", "raw",
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
VALID_AUTHORITY_KIND = {
    "raw-source", "source-page", "owner-page", "external-url",
    "local-resource", "mixed", "none",
}
VALID_AUTHORITY_FRESHNESS = {
    "immutable-source", "stable-meaning", "current-state", "event-log",
    "predictive", "deprecated",
}
AUTHORITY_ANCHOR_FIELDS = (
    "authority_ref", "authority_freshness", "verify_before_action",
    "last_verified",
)
AUTHORITY_METADATA_FIELDS = ("authority_kind",) + AUTHORITY_ANCHOR_FIELDS
BASE_KEYS = {"title", "type", "created", "updated", "sources", "tags", "confidence"}
RELATED_LABELS = {"Supports", "Contradicts", "Depends on", "Derived from", "Part of", "Related"}

MARKDOWN_MD_LINK_RE = re.compile(r"\]\(([^)]+?\.md(?:[?#][^)]*)?)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUS_RE = re.compile(r"\*\*Status(?: note)?\s*\((\d{4}-\d{2}-\d{2})\)")
# Volatile status language in glossary entries. Glossary definitions are
# durable by design; live status belongs on owner pages. File-level updated:
# dates are too coarse to catch a single glossary entry that silently rots.
VOLATILE_STATUS_RE = re.compile(
    r"\b(still (?:missing|open|pending|owed|outstanding)|remains? open"
    r"|not yet|tentative(?:ly)?|awaiting|in progress|up in the air"
    r"|yet to be|to be determined|unresolved|pending)\b",
    re.IGNORECASE,
)
GLOSSARY_BULLET_ENTRY_RE = re.compile(r"^-\s+\*\*(?P<term>[^*]+)\*\*\s+[-:]\s+(?P<body>.*)$")
SOURCING_QUEUE_COUNT_MARKER_RE = re.compile(r"<!--\s*lint:entity-count\b(?P<attrs>.*?)-->")
SOURCING_QUEUE_COUNT_MARKER_INTENT_RE = re.compile(
    r"<!--(?=[^>]*\blint\s*:\s*entity-counts?\b)[\s\S]*?-->"
)
SOURCING_QUEUE_COUNT_ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)=([^\s]+)")
RAW_REPO_TOKEN_RE = re.compile(
    r"(?<![-A-Za-z0-9_./:\x00\x5c])raw/[^\s,\]\"')]+"
)
WIKI_REPO_TOKEN_RE = re.compile(
    r"(?<![-A-Za-z0-9_./:\x00\x5c])"
    r"wiki/[^\s,\])]+?\.md(?=$|[\s,\])}>\"'|]|[.;:](?=$|\s))"
)
# Entity classes required to enroll in the review_by outcome-review loop. The
# template makes decisions mandatory because they carry choices that should be
# revisited; analyses stay opt-in because many are reusable models rather than
# dated predictions.
REVIEW_BY_REQUIRED_FOLDERS = ("decisions",)
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

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
    """Body with generated and curated link sections removed."""
    return strip_body_sections(body, "Referenced by", "Related pages")


def nonblocking_frontmatter(text):
    """Tier-2 parse view; Tier 1 reports malformed leading frontmatter."""
    try:
        return split_frontmatter(text)
    except FrontmatterError:
        return None, ""


def nonblocking_frontmatter_block(text):
    """Raw Tier-2 frontmatter view without duplicating a malformed error."""
    try:
        return frontmatter_block(text)
    except FrontmatterError:
        return ""


def tokens(text):
    text = LINK_RE.sub(" ", text)
    text = re.sub(r"[`*#|>_\-\[\]()]", " ", text)
    out = set()
    for w in re.findall(r"[a-z][a-z0-9']+", text.lower()):
        if len(w) >= 4 and w not in STOPWORDS:
            out.add(w)
    return out


# Tokens in a sources: value that are not provenance slugs to existence-check:
# raw/ paths are checked separately, and free-text provenance (experience,
# web research, deliverable, an explicit URL) is prose, not a page reference.
# The prefix word must be followed by a colon or space so a kebab slug that
# merely STARTS with one of these words (e.g. web-agents-2026) stays checked.
SOURCE_NONSLUG_PREFIX_RE = re.compile(r"^(experience|web|deliverable|source)[:\s]", re.I)


def source_items(fm_block):
    """Split each sources: line in a frontmatter block into its list items.
    Inline values use the shared split_quoted_csv grammar; block-style lists
    (indented '- item' lines under a bare sources: key) are walked the same
    way block_list_has_items walks agent_use_cases, so block-sourced pages get
    the same provenance checks as inline-sourced ones."""
    items = []
    lines = fm_block.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*sources?:\s*(.*)$", line)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline:
            items.extend(split_quoted_csv(inline))
            continue
        for nxt in lines[i + 1:]:
            im = re.match(r"^\s+-\s+(.*)$", nxt)
            if im:
                item = im.group(1).strip().strip("\"'").strip()
                if item:
                    items.append(item)
            elif re.match(r"^\S", nxt):  # next top-level key
                break
    return items


def _mask_http_urls(text):
    chars = list(text)
    for match in HTTP_URL_RE.finditer(text):
        for index in range(*match.span()):
            chars[index] = "\x00"
    return "".join(chars)


def _unsafe_source_path_expressions(item, safe_spans):
    """Path-shaped raw/wiki expressions not accepted by the canonical regexes."""
    scan = _mask_http_urls(item)
    out = []
    for match in re.finditer(r"(?:raw|wiki)[\\/]", scan, re.IGNORECASE):
        if any(start <= match.start() < end for start, end in safe_spans):
            continue
        start = match.start()
        while start > 0 and not scan[start - 1].isspace() and scan[start - 1] not in ",])}|":
            start -= 1
        end = match.end()
        while end < len(scan) and not scan[end].isspace() and scan[end] not in ",])}|":
            end += 1
        expression = item[start:end].strip("([{<\"'")
        entry = (match.group(0)[0:3].lower() if match.group(0).lower().startswith("raw") else "wiki",
                 expression)
        if expression and entry not in out:
            out.append(entry)
    return out


def source_repo_references(item, *, repo_root=None):
    """Resolve canonical raw/wiki refs in one sources: item.

    Returns ``(references, errors)`` where references are ``(kind, path)``
    tuples. The same classifier feeds Tier 1 existence checks and Tier 2 quote
    haystacks, so a path rejected by the guard can never be read as evidence.
    """
    root = Path.cwd() if repo_root is None else Path(repo_root)
    if SOURCE_NONSLUG_PREFIX_RE.match(item) or is_http_url(item):
        return [], []

    raw_matches = list(RAW_REPO_TOKEN_RE.finditer(item))
    wiki_matches = list(WIKI_REPO_TOKEN_RE.finditer(item))
    safe_spans = [match.span() for match in (*raw_matches, *wiki_matches)]
    errors = [
        f"unsafe {family} repository path expression: {expression!r}"
        for family, expression in _unsafe_source_path_expressions(item, safe_spans)
    ]
    if not raw_matches and not wiki_matches and not errors and (
        "/" in item
        or "\\" in item
        or item.startswith((".", "~"))
        or (not any(char.isspace() for char in item) and Path(item).suffix)
    ):
        errors.append(f"unsafe provenance path expression: {item!r}")
    references = []
    for match in raw_matches:
        raw_ref = match.group(0).rstrip(".,:")
        canonical_input = raw_ref[:-1] if raw_ref.endswith("/") else raw_ref
        try:
            canonical = resolve_repo_path(
                canonical_input,
                repo_root=root,
                allowed_prefixes=("raw",),
                mode=EXISTING_FILE,
                require_regular_file=False,
            )
        except RepoPathError:
            errors.append(f"'{raw_ref}' does not exist or is unsafe")
        else:
            references.append(("raw", canonical))
    for match in wiki_matches:
        wiki_ref = match.group(0)
        try:
            canonical = resolve_repo_path(
                wiki_ref,
                repo_root=root,
                allowed_prefixes=("wiki",),
                mode=EXISTING_FILE,
            )
        except RepoPathError:
            errors.append(f"'{wiki_ref}' does not exist or is unsafe")
        else:
            references.append(("wiki", canonical))
    return references, errors


def inline_list_items(value):
    """Parse a simple inline YAML scalar or list (the tags: shape) into item
    strings, via the shared split_quoted_csv grammar."""
    return split_quoted_csv(value)


def fm_scalar(value):
    """Normalize one scalar frontmatter value for deterministic lint checks."""
    if value is None:
        return ""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1].strip()
    return value


def read_raw_buckets_registry():
    """Load the governed raw-folder taxonomy, even when raw/ is absent.

    A malformed or empty registry must not disable membership checks by making
    the raw tree temporarily empty. Returns ``(bucket_names, error)``.
    """
    path = Path("scripts/raw-buckets.json")
    if not path.exists():
        return None, "raw bucket taxonomy file is missing"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"unreadable JSON: {exc}"
    if not isinstance(raw, dict):
        return None, "top level must be a JSON object"
    description = raw.get("description")
    if not isinstance(description, str) or not fm_scalar(description):
        return None, "must contain a nonempty string 'description'"
    buckets = raw.get("buckets")
    if not isinstance(buckets, dict):
        return None, "must contain a 'buckets' object"
    if not buckets:
        return None, "'buckets' must be a nonempty object"
    for key, value in buckets.items():
        if not isinstance(key, str) or not KEBAB_RE.fullmatch(key):
            return None, f"bucket key {key!r} is not kebab-case"
        if not isinstance(value, str) or not fm_scalar(value):
            return None, f"bucket {key!r} needs a nonempty string description"
    return set(buckets), None


def check_meta_utf8():
    """Read every present governed wiki-root Markdown page as UTF-8."""
    fails = []
    for name in sorted(META_PAGES):
        path = WIKI_ROOT / f"{name}.md"
        if not path.exists():
            continue
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            fails.append(("meta-encoding", str(path), f"not valid UTF-8: {exc}"))
        except OSError as exc:
            fails.append(("meta-encoding", str(path), f"could not read: {exc}"))
    return fails


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
                else:
                    # Entity pages are exactly one level deep. Report a direct
                    # bad entry once; descendants of an already-invalid direct
                    # directory add no useful information.
                    for entry in sorted(p.iterdir()):
                        entry_rel = str(entry)
                        if entry.is_symlink():
                            fails.append(("wiki-structure", entry_rel,
                                          "unexpected direct special entry in entity folder"))
                        elif entry.is_dir():
                            fails.append(("wiki-structure", entry_rel,
                                          "direct directory in entity folder; pages must be direct .md files"))
                        elif entry.is_file() and entry.name == ".gitkeep":
                            # Fresh template clones retain empty entity folders
                            # with tracked placeholders until setup creates pages.
                            continue
                        elif entry.is_file() and entry.suffix != ".md":
                            fails.append(("wiki-structure", entry_rel,
                                          "direct non-.md file in entity folder"))
                        elif not entry.is_file():
                            fails.append(("wiki-structure", entry_rel,
                                          "unexpected direct special entry in entity folder"))
            elif p.is_file():
                if name not in WIKI_ALLOWED_FILES:
                    fails.append(("wiki-structure", rel, "unexpected wiki/ root file"))
            else:
                fails.append(("wiki-structure", rel, "unexpected wiki/ entry type"))

    raw_buckets_path = Path("scripts/raw-buckets.json")
    raw_allowed_dirs, raw_registry_error = read_raw_buckets_registry()
    if raw_registry_error:
        fails.append(("raw-buckets", str(raw_buckets_path), raw_registry_error))

    raw_root = Path("raw")
    if raw_root.exists():
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
            elif p.name == ".gitkeep":
                # The tracked placeholder (mirroring raw/.gitkeep) that ships
                # the folder with a fresh clone; not a loose deliverable.
                continue
            else:
                fails.append(("deliverables-structure", rel, "loose deliverable; move it into a clearly labeled subfolder"))

    # tmp/ is intentionally disposable scratch space. Lint does not govern
    # its contents; the maintenance workflow may empty it at the end of a run.
    transactions_clean, transaction_reports = transaction_status(Path.cwd().resolve())
    if not transactions_clean:
        for detail in transaction_reports:
            fails.append(("transaction-state", ".wiki-transactions/", detail))
    return fails

def check_no_tracked_raw():
    """raw/ source artifacts must not be committed; raw/.gitkeep and
    raw/README.md are tracked template exceptions. Fail Tier-1 on any other
    tracked raw/ path. No-ops when git is unavailable or this is not a work
    tree, so lint still runs outside a git context (e.g. eval fixtures copied
    to a temp dir)."""
    cwd = Path.cwd().resolve()
    has_git_metadata = any(
        (candidate / ".git").exists() for candidate in (cwd, *cwd.parents)
    )
    try:
        worktree = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        if has_git_metadata:
            return [("raw-tracked", "raw/",
                     f"git worktree check failed; invariant blocked: {exc}")]
        return []
    if worktree.returncode != 0 or worktree.stdout.strip() != b"true":
        if has_git_metadata:
            stderr = worktree.stderr.decode("utf-8", "replace").strip()
            detail = "git worktree check failed inside apparent worktree"
            if stderr:
                detail += f": {stderr}"
            return [("raw-tracked", "raw/", detail)]
        return []

    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", ":(icase)raw"],
            capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return [("raw-tracked", "raw/",
                 f"git ls-files failed inside worktree; invariant blocked: {exc}")]
    if out.returncode != 0:
        stderr = out.stderr.decode("utf-8", "replace").strip()
        detail = f"git ls-files failed inside worktree (exit {out.returncode})"
        if stderr:
            detail += f": {stderr}"
        return [("raw-tracked", "raw/", detail)]
    fails = []
    allowed = {"raw/.gitkeep", "raw/readme.md"}
    for path in out.stdout.decode("utf-8", "replace").split("\0"):
        if path and path.lower() not in allowed:
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
    pages = set(get_entity_pages(WIKI_ROOT))
    pages.update(
        WIKI_ROOT / f"{name}.md"
        for name in META_PAGES
        if (WIKI_ROOT / f"{name}.md").exists()
    )
    for p in sorted(pages):
        # check_folder_structure reports symlinks, directories, FIFOs, and
        # other direct entity specials. This content scan must not dereference
        # or open them before the structural failure can be reported.
        if p.is_symlink() or not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # the per-page UTF-8 check reports encoding failures
        except OSError:
            continue  # the owning path/meta read reports regular-file errors
        rel = str(p.relative_to(WIKI_ROOT))
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped in STRAY_TAG_EXACT or stripped.startswith("<parameter"):
                fails.append(("stray-tag", rel,
                              f"line {i}: stray tool-call artifact '{stripped}'"))
    return fails


def parse_sourcing_queue_count_markers():
    """Read explicit entity-count markers from wiki/sourcing-queue.md.

    The sourcing queue is prose, so lint does not infer counts from wording.
    Only comments like `<!-- lint:entity-count folder=people count=6 -->` are
    executable. Malformed markers are Tier-1 failures; valid markers feed the
    Tier-2 drift signal.
    """
    path = WIKI_ROOT / "sourcing-queue.md"
    if not path.exists():
        return [], []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [], [("sourcing-queue-count-marker", str(path), f"not valid UTF-8: {e}")]

    markers = []
    fails = []
    seen_folders = set()
    strict_spans = set()
    for match in SOURCING_QUEUE_COUNT_MARKER_RE.finditer(text):
        strict_spans.add(match.span())

    for match in SOURCING_QUEUE_COUNT_MARKER_INTENT_RE.finditer(text):
        if match.span() in strict_spans:
            continue
        line = text.count("\n", 0, match.start()) + 1
        fails.append(("sourcing-queue-count-marker", str(path),
                      f"line {line}: malformed entity-count marker"))

    for match in SOURCING_QUEUE_COUNT_MARKER_RE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        attrs_text = match.group("attrs")
        attr_matches = list(SOURCING_QUEUE_COUNT_ATTR_RE.finditer(attrs_text))
        pairs = [(item.group(1), item.group(2)) for item in attr_matches]
        valid = True

        cursor = 0
        for item in attr_matches:
            if attrs_text[cursor:item.start()].strip():
                valid = False
            cursor = item.end()
        if attrs_text[cursor:].strip():
            valid = False
        if not valid:
            fails.append(("sourcing-queue-count-marker", str(path),
                          f"line {line}: malformed attribute text"))

        values = {}
        for key, value in pairs:
            if key not in {"folder", "count"}:
                fails.append(("sourcing-queue-count-marker", str(path),
                              f"line {line}: unknown attribute '{key}'"))
                valid = False
            elif key in values:
                fails.append(("sourcing-queue-count-marker", str(path),
                              f"line {line}: duplicate attribute '{key}'"))
                valid = False
            else:
                values[key] = value

        folder = values.get("folder")
        count_text = values.get("count")

        if not folder:
            fails.append(("sourcing-queue-count-marker", str(path),
                          f"line {line}: missing folder"))
            valid = False
        elif folder not in FOLDER_TYPE:
            fails.append(("sourcing-queue-count-marker", str(path),
                          f"line {line}: unknown folder '{folder}'"))
            valid = False
        elif folder in seen_folders:
            fails.append(("sourcing-queue-count-marker", str(path),
                          f"line {line}: duplicate folder '{folder}'"))
            valid = False

        if count_text is None:
            fails.append(("sourcing-queue-count-marker", str(path),
                          f"line {line}: missing count"))
            valid = False
            count = None
        else:
            try:
                count = int(count_text)
            except ValueError:
                fails.append(("sourcing-queue-count-marker", str(path),
                              f"line {line}: count '{count_text}' is not an integer"))
                valid = False
                count = None
            else:
                if count < 0:
                    fails.append(("sourcing-queue-count-marker", str(path),
                                  f"line {line}: count must be non-negative"))
                    valid = False

        if valid:
            seen_folders.add(folder)
            markers.append((folder, count, line))
    return markers, fails


def check_sourcing_queue_count_markers():
    """Fail Tier-1 on malformed sourcing-queue entity-count markers."""
    _markers, fails = parse_sourcing_queue_count_markers()
    return fails


def check_log_entry_headers():
    """Every "## " line in wiki/log.md must be a recognized entry header
    ("## [YYYY-MM-DD] ..." or "## YYYY-MM-DD ..."), and no "## " line may sit
    inside a fenced code block at all. rotate_log.py cuts the log only at
    recognized headers and is deliberately fence-unaware, so a nonconforming
    header would be silently merged into the previous entry's archive block,
    and a fenced example that LOOKS like a header would become a bogus cut
    point. The grammar is the shared LOG_ENTRY_HEADER_RE in _wiki_parse."""
    fails = []
    path = WIKI_ROOT / "log.md"
    if not path.exists():
        return fails
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        # An undecodable log must fail loudly here: silently returning would
        # disarm the rotate_log cut-point guard for the whole file.
        return [("log-entry-header", str(path), f"not valid UTF-8: {e}")]
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not line.startswith("## "):
            continue
        if in_fence:
            fails.append(("log-entry-header", str(path),
                          f"line {i}: fenced '## ' line; rotate_log.py cuts are "
                          f"fence-unaware, so reword the example: {line.strip()!r}"))
        elif parse_log_entry_date(line) is None:
            fails.append(("log-entry-header", str(path),
                          f"line {i}: '## ' line is not a recognized log entry "
                          f"header (\"## [YYYY-MM-DD] ...\"): {line.strip()!r}"))
    return fails


def log_entries(text):
    """Return recognized wiki/log.md entries with header metadata and body lines."""
    entries = []
    current = None
    for line_no, line in enumerate(text.splitlines(), 1):
        entry_date = parse_log_entry_date(line)
        if entry_date is not None:
            if current is not None:
                entries.append(current)
            current = {
                "line": line_no,
                "header": line,
                "date": entry_date,
                "type": parse_log_entry_type(line),
                "body": [],
            }
        elif current is not None:
            current["body"].append((line_no, line))
    if current is not None:
        entries.append(current)
    return entries


def split_stale_sweep_fields(payload):
    """Split semicolon fields while allowing semicolons inside JSON strings."""
    out = []
    cur = []
    in_string = False
    escape = False
    depth = 0
    for ch in payload:
        if in_string:
            cur.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth < 0:
                return [], "unbalanced JSON brackets"
        elif ch == ";" and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if in_string:
        return [], "unterminated quoted string"
    if depth != 0:
        return [], "unbalanced JSON brackets"
    out.append("".join(cur).strip())
    return [x for x in out if x], None


def json_string_array(value, field):
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as e:
        return None, f"{field} must be a JSON array of strings: {e.msg}"
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        return None, f"{field} must be a JSON array of strings"
    return parsed, None


def validate_stale_sweep_command(command):
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return f"commands entries must be shell-parseable: {e}"
    if not parts or parts[0] != "rg":
        return "commands entries must be rg evidence shaped like: rg -n -i -- '<phrase>' wiki"
    try:
        sep = parts.index("--")
    except ValueError:
        return "commands entries must include -- before the phrase"
    flags = parts[1:sep]
    if flags != ["-n", "-i"]:
        return "commands entries must use exactly -n -i before --"
    tail = parts[sep + 1:]
    if len(tail) != 2:
        return "commands entries must name exactly one phrase and the wiki root after --"
    phrase, root = tail
    if not phrase.strip():
        return "commands entries must include a non-empty phrase"
    if root.rstrip("/") != "wiki":
        return "commands entries must search the wiki root (wiki or wiki/)"
    return None


def validate_stale_sweep_proof(line):
    prefix = "Stale-text sweep:"
    if not line.startswith(prefix):
        return "line must start with 'Stale-text sweep:'"
    payload = line[len(prefix):].strip()
    if not payload:
        return "missing status field"
    segments, err = split_stale_sweep_fields(payload)
    if err:
        return err
    fields = {}
    for segment in segments:
        if "=" not in segment:
            return f"field segment missing '=': {segment!r}"
        key, value = segment.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            return f"field segment has empty key: {segment!r}"
        if key in fields:
            return f"duplicate field '{key}'"
        fields[key] = value

    status = fields.get("status")
    if status not in {"completed", "not_applicable"}:
        return "status must be completed or not_applicable"

    if status == "completed":
        required = {
            "status", "commands", "hit_count", "pages_fixed",
            "historical_no_change_hits",
        }
        extra = set(fields) - required
        missing = required - set(fields)
        if missing:
            return "completed proof missing field(s): " + ", ".join(sorted(missing))
        if extra:
            return "completed proof has unexpected field(s): " + ", ".join(sorted(extra))
        commands, err = json_string_array(fields["commands"], "commands")
        if err:
            return err
        if not commands:
            return "commands must include at least one command string"
        for command in commands:
            err = validate_stale_sweep_command(command)
            if err:
                return err
        for field in ("pages_fixed", "historical_no_change_hits"):
            _parsed, err = json_string_array(fields[field], field)
            if err:
                return err
        if not re.fullmatch(r"\d+", fields["hit_count"]):
            return "hit_count must be a non-negative integer"
        return None

    required = {"status", "reason"}
    extra = set(fields) - required
    missing = required - set(fields)
    if missing:
        return "not_applicable proof missing field(s): " + ", ".join(sorted(missing))
    if extra:
        return "not_applicable proof has unexpected field(s): " + ", ".join(sorted(extra))
    try:
        reason = json.loads(fields["reason"])
    except json.JSONDecodeError as e:
        return f"reason must be a JSON string: {e.msg}"
    if not isinstance(reason, str) or not reason.strip():
        return "reason must be a non-empty JSON string"
    return None


def check_stale_sweep_proof_entries():
    """New ingest log entries must carry parseable stale-text sweep evidence.

    This validates the proof shape only. It deliberately does not decide whether
    the search terms or hit classifications were semantically complete.
    """
    fails = []
    path = WIKI_ROOT / "log.md"
    if not path.exists():
        return fails
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [("stale-sweep-proof", str(path), f"not valid UTF-8: {e}")]
    for entry in log_entries(text):
        if entry["type"] != "ingest":
            continue
        try:
            entry_date = date.fromisoformat(entry["date"])
        except ValueError:
            fails.append(("stale-sweep-proof", str(path),
                          f"line {entry['line']}: ingest entry date "
                          f"{entry['date']} is not a real calendar date"))
            continue
        if entry_date < STALE_SWEEP_PROOF_REQUIRED_FROM:
            continue
        proof_lines = [
            (line_no, line) for line_no, line in entry["body"]
            if line.startswith("Stale-text sweep:")
        ]
        if not proof_lines:
            fails.append(("stale-sweep-proof", str(path),
                          f"line {entry['line']}: ingest entry dated {entry['date']} "
                          "is missing structured Stale-text sweep proof"))
            continue
        if len(proof_lines) > 1:
            fails.append(("stale-sweep-proof", str(path),
                          f"line {entry['line']}: ingest entry has multiple "
                          "Stale-text sweep proof lines"))
        for line_no, line in proof_lines:
            err = validate_stale_sweep_proof(line)
            if err:
                fails.append(("stale-sweep-proof", str(path),
                              f"line {line_no}: {err}"))
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
    # A suppression filed under a misspelled or retired category key would
    # silently detach; unknown keys fail loudly instead (REFERENCES.md rule).
    # Underscore-prefixed keys are documentation metadata (e.g. _description),
    # never suppression lists.
    known_keys = {
        "accepted_orphans", "hub_pages", "skipped_crossref_pairs",
        "reviewed_confidence_low", "reviewed_near_duplicates",
        "reviewed_quotes", "reviewed_recompile_candidates",
        "reviewed_authority_missing", "reviewed_glossary_volatile",
        "reviewed_unconsumed_sources",
    }
    unknown = sorted(k for k in set(raw) - known_keys if not k.startswith("_"))
    if unknown:
        return {}, ("unknown top-level category key(s): " + ", ".join(unknown)
                    + "; suppression entries under an unrecognized key would "
                      "silently detach")
    for key in ("accepted_orphans", "hub_pages", "reviewed_confidence_low",
                "reviewed_authority_missing", "reviewed_unconsumed_sources"):
        for e in raw.get(key, []):
            if not isinstance(e, dict) or not isinstance(e.get("page"), str):
                return {}, f"every '{key}' entry needs a string 'page' field"
    for key in ("skipped_crossref_pairs", "reviewed_near_duplicates",
                "reviewed_recompile_candidates"):
        for e in raw.get(key, []):
            pair = e.get("pair") if isinstance(e, dict) else None
            if not (isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(x, str) for x in pair)):
                return {}, f"every '{key}' entry needs a two-item string 'pair' field"
    for e in raw.get("reviewed_quotes", []):
        if not (isinstance(e, dict) and isinstance(e.get("page"), str)
                and isinstance(e.get("quote"), str)):
            return {}, "every 'reviewed_quotes' entry needs string 'page' and 'quote' fields"
    for e in raw.get("reviewed_glossary_volatile", []):
        if not (isinstance(e, dict) and isinstance(e.get("term"), str)
                and isinstance(e.get("phrase"), str)):
            return {}, ("every 'reviewed_glossary_volatile' entry needs "
                        "string 'term' and 'phrase' fields")
    return raw, None


# --------------------------- Tier 1: per-page check registry ---------------------------
#
# Each per-page check below is a small, self-contained function a maintainer can
# read in isolation. It receives one PageContext and returns a list of fail
# tuples (check, page_relpath, detail), the same shape the loop appends. Two
# registries list them in evaluation order: TIER1_PATH_CHECKS (path-only, run
# before frontmatter parsing) and TIER1_PAGE_CHECKS (frontmatter-dependent);
# tier1() iterates the entity pages and, for each, runs every check in order.
# This preserves the exact emit order of the previous inlined loop (page-outer,
# check-inner), so the grouped/sorted report is byte-for-byte identical.


class PageContext:
    """Everything a Tier-1 per-page check needs about one entity page.

    Built once per page in the tier1() loop and passed to each registered check,
    so the checks share parsing work (read, split_frontmatter, frontmatter_block)
    instead of each re-deriving it."""

    __slots__ = ("path", "rel", "stem", "folder", "text", "fm", "fm_block",
                 "frontmatter_error",
                 "valid_slugs", "source_slugs")

    def __init__(self, path, text, valid_slugs, source_slugs):
        self.path = path
        self.rel = str(path.relative_to(WIKI_ROOT))
        self.stem = path.stem
        self.folder = path.parent.name if path.parent != WIKI_ROOT else None
        self.text = text
        self.frontmatter_error = None
        try:
            self.fm, _ = split_frontmatter(text)
            self.fm_block = frontmatter_block(text)
        except FrontmatterError as exc:
            self.fm = None
            self.fm_block = ""
            self.frontmatter_error = str(exc)
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

    required_scalars = {"title", "type", "created", "updated", "confidence"}
    if ctx.folder == "sources":
        required_scalars.add("source_type")
    for key in sorted(required_scalars & set(ctx.fm)):
        if not fm_scalar(ctx.fm[key]):
            fails.append(("frontmatter", ctx.rel,
                          f"{key} must be a nonempty scalar"))

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


def check_authority_field_values(ctx):
    """Authority metadata fields use accepted scalar values and dates."""
    fails = []
    kind = fm_scalar(ctx.fm.get("authority_kind"))
    if "authority_kind" in ctx.fm and kind not in VALID_AUTHORITY_KIND:
        fails.append(("authority-field-values", ctx.rel,
                      f"authority_kind '{kind}' is not an accepted value"))

    freshness = fm_scalar(ctx.fm.get("authority_freshness"))
    if ("authority_freshness" in ctx.fm
            and freshness not in VALID_AUTHORITY_FRESHNESS):
        fails.append(("authority-field-values", ctx.rel,
                      f"authority_freshness '{freshness}' is not an accepted value"))

    verify = fm_scalar(ctx.fm.get("verify_before_action"))
    if "verify_before_action" in ctx.fm and verify not in {"true", "false"}:
        fails.append(("authority-field-values", ctx.rel,
                      "verify_before_action must be true or false"))

    verified = fm_scalar(ctx.fm.get("last_verified"))
    if "last_verified" in ctx.fm:
        if not DATE_RE.match(verified):
            fails.append(("authority-field-values", ctx.rel,
                          f"last_verified '{verified}' is not YYYY-MM-DD"))
        else:
            try:
                date.fromisoformat(verified)
            except ValueError:
                fails.append(("authority-field-values", ctx.rel,
                              f"last_verified '{verified}' is not a real calendar date"))
    return fails


def check_authority_kind_anchor(ctx):
    """Any authority-scoped field requires authority_kind as the anchor."""
    present = [k for k in AUTHORITY_ANCHOR_FIELDS if k in ctx.fm]
    if present and "authority_kind" not in ctx.fm:
        return [("authority-kind-anchor", ctx.rel,
                 "authority metadata present without authority_kind: "
                 + ", ".join(present))]
    return []


def check_authority_ref_required(ctx):
    """authority_kind values other than none require a non-empty authority_ref."""
    kind = fm_scalar(ctx.fm.get("authority_kind"))
    if kind in VALID_AUTHORITY_KIND and kind != "none" and not fm_scalar(ctx.fm.get("authority_ref")):
        return [("authority-ref-required", ctx.rel,
                 f"authority_ref required when authority_kind is '{kind}'")]
    return []


def check_authority_ref_shape(ctx):
    """authority_ref shape and cheap existence checks by authority_kind."""
    fails = []
    if "authority_kind" not in ctx.fm:
        return fails
    kind = fm_scalar(ctx.fm.get("authority_kind"))
    if kind not in VALID_AUTHORITY_KIND:
        return fails
    ref = fm_scalar(ctx.fm.get("authority_ref"))

    if kind == "none":
        if ref:
            fails.append(("authority-ref-shape", ctx.rel,
                          "authority_kind 'none' requires authority_ref to be absent or empty"))
        return fails
    if not ref:
        return fails  # authority-ref-required reports the missing value.

    def contained(prefixes, *, require_regular_file=True):
        try:
            resolve_repo_path(
                ref,
                repo_root=Path.cwd(),
                allowed_prefixes=prefixes,
                mode=EXISTING_FILE,
                require_regular_file=require_regular_file,
            )
        except RepoPathError:
            return False
        return True

    if kind == "raw-source":
        if not contained(("raw",), require_regular_file=False):
            fails.append(("authority-ref-shape", ctx.rel,
                          f"raw-source authority_ref '{ref}' must be a contained existing raw/ path"))
    elif kind == "source-page":
        if not ref.endswith(".md") or not contained(("wiki/sources",)):
            fails.append(("authority-ref-shape", ctx.rel,
                          f"source-page authority_ref '{ref}' must be a contained existing wiki/sources/*.md file"))
    elif kind == "owner-page":
        if not ref.endswith(".md") or not contained(("wiki",)):
            fails.append(("authority-ref-shape", ctx.rel,
                          f"owner-page authority_ref '{ref}' must be a contained existing wiki/*.md file"))
        elif ref.startswith("wiki/sources/"):
            fails.append(("authority-ref-shape", ctx.rel,
                          f"owner-page authority_ref '{ref}' must not be under wiki/sources/"))
    elif kind == "external-url":
        if not is_http_url(ref):
            fails.append(("authority-ref-shape", ctx.rel,
                          f"external-url authority_ref '{ref}' must be exactly one http:// or https:// URL"))
    elif kind == "local-resource":
        if ref.lower().startswith("source:"):
            return fails
        try:
            resolve_repo_path(
                ref,
                repo_root=Path.cwd(),
                allowed_prefixes=tuple(sorted(ROOT_ALLOWED_DIRS - {".git"})),
                allowed_root_files=ROOT_ALLOWED_FILES,
                mode=EXISTING_FILE,
                require_regular_file=False,
            )
        except RepoPathError:
            fails.append(("authority-ref-shape", ctx.rel,
                          f"local-resource authority_ref '{ref}' must exist under the repo root or start with source:"))
    elif kind == "mixed":
        # Mixed prose stays terminal only when explicitly classified. Any
        # path-shaped value still crosses the shared containment boundary.
        if ref.lower().startswith("source:") or is_http_url(ref):
            return fails
        path_shaped = (
            "/" in ref
            or "\\" in ref
            or ref.startswith((".", "~"))
            or ref in ROOT_ALLOWED_FILES
            or (not any(char.isspace() for char in ref) and Path(ref).suffix)
        )
        if path_shaped:
            try:
                resolve_repo_path(
                    ref,
                    repo_root=Path.cwd(),
                    allowed_prefixes=tuple(sorted(ROOT_ALLOWED_DIRS - {".git"})),
                    allowed_root_files=ROOT_ALLOWED_FILES,
                    mode=EXISTING_FILE,
                    require_regular_file=False,
                )
            except RepoPathError:
                fails.append(("authority-ref-shape", ctx.rel,
                              f"mixed authority_ref '{ref}' is an unsafe repository path"))
    return fails


def check_source_page_authority(ctx):
    """Source pages with authority metadata stay immutable source summaries."""
    if ctx.folder != "sources" or not any(k in ctx.fm for k in AUTHORITY_METADATA_FIELDS):
        return []
    fails = []
    kind = fm_scalar(ctx.fm.get("authority_kind"))
    if kind in VALID_AUTHORITY_KIND and kind not in {"raw-source", "external-url", "mixed"}:
        fails.append(("source-page-authority", ctx.rel,
                      "source pages with authority metadata must use raw-source, external-url, or mixed"))
    freshness = fm_scalar(ctx.fm.get("authority_freshness"))
    if freshness in VALID_AUTHORITY_FRESHNESS and freshness != "immutable-source":
        fails.append(("source-page-authority", ctx.rel,
                      "source pages may only set authority_freshness to immutable-source"))
    return fails


def check_predictive_review_enrollment(ctx):
    """Predictive authority metadata must enroll in the review_by loop."""
    if fm_scalar(ctx.fm.get("authority_freshness")) == "predictive" and not ctx.fm.get("review_by"):
        return [("predictive-review-enrollment", ctx.rel,
                 "authority_freshness 'predictive' requires review_by")]
    return []


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
        if SOURCE_NONSLUG_PREFIX_RE.match(item) or is_http_url(item):
            continue
        references, errors = source_repo_references(item)
        fails.extend(("source-ref", ctx.rel, error) for error in errors)
        if references or errors:
            continue
        if KEBAB_RE.match(item) and item not in ctx.source_slugs:
            fails.append(("source-ref", ctx.rel,
                          f"source '{item}' matches no wiki/sources/ page"))
        elif not KEBAB_RE.match(item):
            fails.append(("source-ref", ctx.rel,
                          f"unclassified provenance reference: {item!r}"))
    return fails


def check_dangling_links(ctx):
    """Wikilinks resolve to a real page. Code spans are stripped (a [[link]]
    inside a code example is not a failure); the shared dangling_slugs helper
    keeps this in lockstep with the Tier-2 meta-page dangling check."""
    if ctx.frontmatter_error:
        return []
    return [("dangling-link", ctx.rel, f"[[{slug}]] resolves to nothing")
            for slug in dangling_slugs(ctx.text, ctx.valid_slugs)]


def check_synthesis_not_cited(ctx):
    """The synthesis ledger is orientation, never provenance: synthesis claims
    cite original pages, not the ledger (the rule wiki/synthesis.md states in
    prose; promoted from the ledger's 2026-06-10 standing question on
    2026-07-09). Flags [[synthesis]] or a bare `synthesis` slug among the
    sources: items, and "(source: [[synthesis]])"-style citations in the
    authored body. A plain [[synthesis]] link stays legal: in the body it is
    orientation, not provenance, and Related pages / Referenced by sit past
    the authored_body cut."""
    fails = []
    if ctx.fm_block:
        for item in source_items(ctx.fm_block):
            if item == "synthesis" or "[[synthesis]]" in item:
                fails.append(("synthesis-as-source", ctx.rel,
                              "sources: cites the synthesis ledger; cite the original pages"))
    scan = evidentiary_view(ctx.text)
    for _ in re.finditer(r"\(sources?:[^)]*\[\[synthesis\]\]", scan, re.I):
        fails.append(("synthesis-as-source", ctx.rel,
                      "body cites [[synthesis]] as a source; cite the original pages"))
    return fails


def check_related_labels(ctx):
    """Related-pages relationship labels come from the fixed vocabulary
    (RELATED_LABELS here; the meanings table lives in REFERENCES.md). A bullet
    may be untyped ("- [[page]]"), but a "Label:" prefix on a bullet that carries
    a [[link]] must be one of the six labels. A plain prose bullet ("- Note:
    ...", a page-to-create) is permitted by SCHEMA and is not an attempted
    typed label."""
    fails = []
    related = section_body(ctx.text, "Related pages")
    if related is not None:
        for line in related.splitlines():
            lm = re.match(r"^-\s+([A-Za-z][A-Za-z ]*?):\s", line)
            if lm and "[[" in line and lm.group(1) not in RELATED_LABELS:
                fails.append(("related-label", ctx.rel,
                              f"'{lm.group(1)}:' is not an allowed relationship label"))
    return fails


def check_open_questions(ctx):
    """Non-source pages carry an "Open questions / gaps" section (SCHEMA rule:
    required on every non-source entity type). Sources are exempt; confidence
    already flags preview-only material there. Presence-only and deterministic,
    so it gates like the other structural mandates."""
    if ctx.folder == "sources":
        return []
    if not re.search(r"^##+ Open [Qq]uestions", ctx.text, re.M):
        return [("open-questions", ctx.rel, "missing Open questions / gaps section")]
    return []


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
# Path-only checks: they read the path, not the frontmatter dict, so tier1()
# runs them before frontmatter parsing and they still fire on pages whose
# frontmatter is missing or malformed. Kept as their own tuple so the
# pre-parse/post-parse split is structural, not a slice-plus-comment.
TIER1_PATH_CHECKS = (
    check_filename,
    check_entity_folder,
)

TIER1_PAGE_CHECKS = (
    check_required_keys,
    check_type_matches_folder,
    check_confidence_value,
    check_source_type_placement,
    check_dates,
    check_authority_field_values,
    check_authority_kind_anchor,
    check_authority_ref_required,
    check_authority_ref_shape,
    check_source_page_authority,
    check_predictive_review_enrollment,
    check_source_refs,
    check_dangling_links,
    check_synthesis_not_cited,
    check_related_labels,
    check_open_questions,
    check_confidence_restate,
)


def tier1(entity_pages, valid_slugs, index_targets, index_duplicates, index_read_fails=()):
    fails = []  # (check, page_relpath, detail)
    fails.extend(check_folder_structure())
    fails.extend(check_no_tracked_raw())
    fails.extend(check_meta_utf8())
    fails.extend(check_stray_tool_tags())
    fails.extend(check_sourcing_queue_count_markers())
    fails.extend(check_log_entry_headers())
    fails.extend(check_stale_sweep_proof_entries())
    fails.extend(index_read_fails)

    def rel(p):
        return str(p.relative_to(WIKI_ROOT))

    # Structural lint owns special entries. Never dereference a symlink or
    # open a FIFO/device merely because its name ends in .md.
    regular_entity_pages = [
        p for p in entity_pages if not p.is_symlink() and p.is_file()
    ]

    # wikilinks resolve by bare stem, so two pages sharing one is an
    # ambiguous link target and a miscounted inbound graph
    by_stem = {}
    for p in regular_entity_pages:
        by_stem.setdefault(p.stem, []).append(p)
    # source-page slugs, for resolving bare-slug provenance refs
    source_slugs = {
        p.stem for p in regular_entity_pages if p.parent.name == "sources"
    }

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
    for p in regular_entity_pages:
        r = rel(p)
        entity_relpaths.add(r)
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            fails.append(("encoding", r, f"not valid UTF-8: {e}"))
            continue
        except OSError as e:
            fails.append(("encoding", r, f"could not read: {e}"))
            continue

        ctx = PageContext(p, text, valid_slugs, source_slugs)

        # path-only checks run even without parseable frontmatter.
        for check in TIER1_PATH_CHECKS:
            fails.extend(check(ctx))

        if ctx.fm is None:
            detail = "missing or malformed frontmatter"
            if ctx.frontmatter_error:
                detail += f": {ctx.frontmatter_error}"
            fails.append(("frontmatter", r, detail))
            continue

        # frontmatter-dependent per-page checks, in registry order.
        for check in TIER1_PAGE_CHECKS:
            fails.extend(check(ctx))

    # index coverage (only for paths that name an entity folder). If index.md
    # itself is unreadable, report that root cause instead of flooding the output
    # with every page as index-missing.
    if not index_read_fails:
        for r in sorted(entity_relpaths - index_targets):
            fails.append(("index-missing", r, "no row in index.md"))
        for t in sorted(index_targets - entity_relpaths):
            if "/" in t and t.split("/")[0] in FOLDER_TYPE:
                fails.append(("index-stale", t, "index.md row points to missing page"))
        # "one row per page" is two-sided: coverage above, uniqueness here. Duplicate
        # rows have appeared under concurrent sessions and were invisible to lint.
        for t in index_duplicates:
            if "/" in t and t.split("/")[0] in FOLDER_TYPE:
                fails.append(("index-duplicate", t, "multiple index.md rows point to this page"))

    # the adjudication file must parse and every entry must reference an
    # existing page; otherwise suppression silently turns off or a rename
    # silently detaches the settled judgment.
    raw, adj_err = read_adjudications()
    if adj_err:
        fails.append(("adjudication-file", str(ADJUDICATIONS_PATH), adj_err))
    else:
        referenced = []
        for key in ("accepted_orphans", "hub_pages", "reviewed_confidence_low",
                    "reviewed_quotes", "reviewed_authority_missing",
                    "reviewed_unconsumed_sources"):
            referenced += [e["page"] for e in raw.get(key, [])]
        for key in ("skipped_crossref_pairs", "reviewed_near_duplicates"):
            for e in raw.get(key, []):
                referenced += e["pair"]
        for page in sorted(set(referenced)):
            if page not in entity_relpaths:
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"entry references missing page '{page}'"))
        for e in raw.get("reviewed_recompile_candidates", []):
            compiled, source = e["pair"]
            if compiled not in entity_relpaths:
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"recompile entry references missing compiled page '{compiled}'"))
            elif Path(compiled).parent.name == "sources":
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"recompile compiled page must not be under sources/: '{compiled}'"))
            if source not in entity_relpaths:
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"recompile entry references missing source page '{source}'"))
            elif Path(source).parent.name != "sources":
                fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                              f"recompile source page must be under sources/: '{source}'"))
        gv_entries = raw.get("reviewed_glossary_volatile", [])
        if gv_entries:
            glossary_terms = {term for term, _line in glossary_entry_lines()}
            for e in gv_entries:
                if e["term"] not in glossary_terms:
                    fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                                  "glossary_volatile entry references missing "
                                  f"glossary term '{e['term']}'"))
                if not VOLATILE_STATUS_RE.fullmatch(e["phrase"]):
                    fails.append(("adjudication-stale", str(ADJUDICATIONS_PATH),
                                  f"glossary_volatile phrase '{e['phrase']}' is "
                                  "not in the volatile-language vocabulary"))

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


def quote_mismatches(entity_pages, adjudicated_quotes, used=None):
    """Tier-2 candidates: quoted text attributed to a source that does not
    appear verbatim in the cited wiki page or its raw files. Deterministic
    string matching only; whether a non-match is a defect (vs. labeled own
    framing) is adjudicated by the lint workflow, not decided here. `used`
    (when given) collects the adjudication keys that suppressed a candidate."""
    by_stem = {p.stem: p for p in entity_pages}
    out, suppressed = [], 0
    for p in entity_pages:
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # tier1 reports it
        rel = str(p.relative_to(WIKI_ROOT))
        _, body = nonblocking_frontmatter(text)
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
                cited_fm = nonblocking_frontmatter_block(cited_text)
                if cited_fm:
                    for item in source_items(cited_fm):
                        references, _errors = source_repo_references(item)
                        for kind, canonical in references:
                            if kind != "raw":
                                continue
                            rp = Path.cwd().joinpath(*canonical.split("/"))
                            if rp.is_file():
                                try:
                                    haystacks.append(normalize_quote(
                                        rp.read_text(encoding="utf-8")))
                                except (OSError, UnicodeDecodeError):
                                    pass
            if not haystacks:
                continue
            found = any(all(f in h for f in frags) for h in haystacks)
            if found:
                continue
            key = (rel, normalize_quote(quote_raw))
            if key in adjudicated_quotes:
                if used is not None:
                    used.add(key)
                suppressed += 1
                continue
            preview = quote_raw[:70] + ("..." if len(quote_raw) > 70 else "")
            out.append(f'{rel}: "{preview}" not found in cited source(s)')
    return sorted(out), suppressed


# --------------------------- Tier 2 ---------------------------

def glossary_entry_lines():
    """Yield (term, line) for every non-fenced body line of each glossary entry.

    The template's starter glossary uses bold bullet entries, while the durable
    entry template uses `### Term` headings. Support both so the lint signal
    protects current starter content and future configured entries.
    """
    path = WIKI_ROOT / "glossary.md"
    if not path.exists():
        return
    term = None
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("### "):
            term = line[4:].strip()
            continue
        bullet = GLOSSARY_BULLET_ENTRY_RE.match(line)
        if bullet:
            yield bullet.group("term").strip(), bullet.group("body")
            continue
        if term is not None:
            yield term, line


def load_adjudications():
    """Settled Tier-2 judgments, held as data so lint stops re-surfacing them.

    Returns a dict of plain sets/pair-sets; empty when the file is absent so
    lint stays fully operable without it.
    """
    empty = {
        "orphans": set(), "hubs": set(), "pairs": set(),
        "confidence": set(), "duplicates": set(), "quotes": set(),
        "recompile": set(), "authority_missing": set(),
        "glossary_volatile": set(),
        "unconsumed_sources": set(),
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
        "quotes": {(e["page"], normalize_quote(e["quote"]))
                   for e in raw.get("reviewed_quotes", [])},
        "recompile": {(e["pair"][0], e["pair"][1])
                      for e in raw.get("reviewed_recompile_candidates", [])},
        "authority_missing": {e["page"] for e in raw.get("reviewed_authority_missing", [])},
        "glossary_volatile": {(e["term"], e["phrase"].lower())
                              for e in raw.get("reviewed_glossary_volatile", [])},
        "unconsumed_sources": {e["page"]
                               for e in raw.get("reviewed_unconsumed_sources", [])},
    }


def latest_status_date(text):
    # Strip code spans first so a **Status (date)** written as a format example
    # inside a code fence is not read as a real status note.
    out = []
    try:
        view = status_review_view(text)
    except FrontmatterError:
        return None
    for value in STATUS_RE.findall(view):
        try:
            out.append(date.fromisoformat(value))
        except ValueError:
            continue
    return max(out) if out else None


def frontmatter_updated_date(fm):
    if not fm or not fm.get("updated"):
        return None
    try:
        return date.fromisoformat(fm["updated"])
    except ValueError:
        return None


def normalize_markdown_target(href):
    href = href.strip()
    if "://" in href or href.startswith("mailto:"):
        return None
    href = href.split("#", 1)[0].split("?", 1)[0]
    if href.startswith("./"):
        href = href[2:]
    if href.startswith("wiki/"):
        href = href[len("wiki/"):]
    return str(Path(href))


def resolve_markdown_target(href, relpaths, stem_to_relpaths):
    normalized = normalize_markdown_target(href)
    if not normalized:
        return None
    if normalized in relpaths:
        return normalized
    matches = stem_to_relpaths.get(Path(normalized).stem, [])
    return matches[0] if len(matches) == 1 else None


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

    __slots__ = ("pages", "data", "inbound", "outbound", "adj", "adj_used")

    def __init__(self, pages, valid_slugs, adjudicated):
        self.pages = pages
        self.data = {}
        self.inbound = {p: 0 for p in pages}
        self.outbound = {}
        for p in pages:
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                # tier1 reports the encoding failure; skip for candidate signals
                text = ""
            fm, _ = nonblocking_frontmatter(text)
            try:
                ab = evidentiary_view(text)
            except FrontmatterError:
                ab = ""
            status_date = latest_status_date(text)
            dates = [d for d in (frontmatter_updated_date(fm), status_date)
                     if d is not None]
            self.data[p] = {
                "fm": fm or {},
                "status_date": status_date,
                "freshness": max(dates) if dates else None,
                "tokens": tokens(ab),
                "words": len(re.findall(r"\w+", ab)),
                # A [[link]] inside a code example is not a citation.
                "body_links": bool(LINK_RE.search(ab)),
                # Raw-block parse so block-style sources: lists count as cited.
                "source_items": source_items(nonblocking_frontmatter_block(text)),
            }
            # Outbound links must be authored; generated "Referenced by" blocks
            # would echo inbound links back and fabricate a bidirectional graph,
            # and a [[link]] inside a code span is a syntax example, not an edge
            # (the same rule the dangling scan and the rebuild apply). Fences
            # are blanked before the section strip so a fenced "## Referenced
            # by" example cannot swallow authored links after it.
            try:
                link_view = authored_link_view(text)
            except FrontmatterError:
                link_view = ""
            self.outbound[p] = set(LINK_RE.findall(link_view))

        stems = {p.stem: p for p in pages}
        for p in pages:
            for slug in self.outbound[p]:
                if slug in stems and stems[slug] is not p:
                    self.inbound[stems[slug]] += 1

        # adjudicated is always supplied by the sole caller (tier2 <- main, which
        # passes load_adjudications()); load_adjudications already returns the
        # empty template when the file is absent, so no fallback is needed here.
        self.adj = adjudicated
        # Which adjudication entries actually suppressed a candidate this run.
        # Signals record usage as they suppress; signal_adjudication_dead (kept
        # last in TIER2_SIGNALS) reports the entries that suppressed nothing.
        self.adj_used = {key: set() for key in adjudicated}


def signal_quote_mismatch(ctx):
    """Quoted text attributed to a source that is not verbatim in the cited page."""
    return quote_mismatches(ctx.pages, ctx.adj["quotes"], ctx.adj_used["quotes"])


def signal_orphans(ctx):
    """Pages with no inbound links."""
    orphans = [str(p.relative_to(WIKI_ROOT)) for p in ctx.pages if ctx.inbound[p] == 0]
    out, suppressed = [], 0
    for o in sorted(orphans):
        if o in ctx.adj["orphans"]:
            ctx.adj_used["orphans"].add(o)
            suppressed += 1
        else:
            out.append(o)
    return out, suppressed


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
                ctx.adj_used["duplicates"].add(frozenset((ra, rb)))
                suppressed += 1
                continue
            dups.append((j, ra, rb))
    return sorted(dups, reverse=True)[:15], suppressed


def signal_uncited(ctx):
    """Non-source pages with no sources and no body links. Checked via
    source_items on the raw frontmatter block: the key parser flattens a
    block-style sources: list to '', which must still count as cited."""
    uncited = []
    for p in ctx.pages:
        if p.parent.name == "sources":
            continue
        if not ctx.data[p]["source_items"] and not ctx.data[p]["body_links"]:
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
            rel = str(p.relative_to(WIKI_ROOT))
            if rel in ctx.adj["confidence"]:
                ctx.adj_used["confidence"].add(rel)
                suppressed += 1
                continue
            upgrade.append(f"{p.relative_to(WIKI_ROOT)} ({ctx.inbound[p]} inbound)")
    return sorted(upgrade), suppressed


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
        if a.parent.name == "sources" and b.parent.name == "sources":
            continue
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
            for hub in (ra, rb):
                if hub in ctx.adj["hubs"]:
                    ctx.adj_used["hubs"].add(hub)
            if frozenset((ra, rb)) in ctx.adj["pairs"]:
                ctx.adj_used["pairs"].add(frozenset((ra, rb)))
            suppressed += 1
            continue
        cocite.append((score, len(shared), ra, rb))
    return sorted(cocite, reverse=True), suppressed


def signal_log_rotation_due(ctx):
    """Log file has crossed the documented rotation warning threshold."""
    _ = ctx
    path = WIKI_ROOT / "log.md"
    if not path.exists():
        return [], 0
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], 0  # meta-page encoding is outside this maintenance signal
    line_count = len(text.splitlines())
    if line_count <= LOG_ROTATION_WARN_LINES:
        return [], 0
    return ([f"{path} has {line_count} lines; threshold is {LOG_ROTATION_WARN_LINES}"], 0)


def signal_sourcing_queue_count_drift(ctx):
    """Entity-count markers in sourcing-queue.md that disagree with the corpus."""
    _ = ctx
    markers, fails = parse_sourcing_queue_count_markers()
    if fails:
        return [], 0  # Tier-1 reports malformed markers
    if not markers:
        return [], 0
    counts = {}
    for page in get_entity_pages(WIKI_ROOT):
        counts[page.parent.name] = counts.get(page.parent.name, 0) + 1
    out = []
    for folder, declared, _line in markers:
        actual = counts.get(folder, 0)
        if declared != actual:
            out.append(
                f"{WIKI_ROOT / 'sourcing-queue.md'}: folder {folder} "
                f"declares {declared} but actual count is {actual}"
            )
    return out, 0


def signal_recompile_candidates(ctx):
    """Compiled pages older than authored source links they already depend on.

    This is a review prompt, not a stale-page verdict. It only follows direct
    authored links from non-source pages to source pages; reverse source-to-page
    links are intentionally left out until the noisier direction has a proven
    precision case.
    """
    stem_to_pages = {}
    for p in ctx.pages:
        stem_to_pages.setdefault(p.stem, []).append(p)

    out, suppressed = [], 0
    for p in sorted(ctx.pages):
        if p.parent.name == "sources":
            continue
        page_freshness = ctx.data[p].get("freshness")
        if page_freshness is None:
            continue
        page_rel = str(p.relative_to(WIKI_ROOT))
        source_hits = []
        for slug in sorted(ctx.outbound.get(p, set())):
            matches = stem_to_pages.get(slug, [])
            if len(matches) != 1:
                continue
            source = matches[0]
            if source.parent.name != "sources":
                continue
            source_updated = frontmatter_updated_date(ctx.data[source]["fm"])
            if source_updated is None or source_updated <= page_freshness:
                continue
            source_rel = str(source.relative_to(WIKI_ROOT))
            pair = (page_rel, source_rel)
            if pair in ctx.adj["recompile"]:
                ctx.adj_used["recompile"].add(pair)
                suppressed += 1
                continue
            source_hits.append((source_rel, source_updated))
        if source_hits:
            hits = "; ".join(
                f"{source_rel} {source_updated.isoformat()}"
                for source_rel, source_updated in source_hits
            )
            out.append(
                f"{page_rel} (page {page_freshness.isoformat()}): "
                f"newer sources: {hits}"
            )
    return out, suppressed


def signal_glossary_volatile_status(ctx):
    """Glossary entries restating volatile status.

    Definitions should be durable. When a glossary entry says something is
    still pending or remains open, the claim can rot without any source page
    changing. Resolve by rewriting to a dated fact or delegating to the owner
    page. Adjudicate only durable definitional or rhetorical usage.
    """
    out = []
    suppressed = 0
    hits = dict.fromkeys(
        (term, m.group(0).lower())
        for term, line in glossary_entry_lines()
        for m in VOLATILE_STATUS_RE.finditer(line)
    )
    for term, phrase in hits:
        if (term, phrase) in ctx.adj["glossary_volatile"]:
            ctx.adj_used["glossary_volatile"].add((term, phrase))
            suppressed += 1
            continue
        out.append(f"glossary.md '{term}': \"{phrase}\" (rewrite to a dated "
                   "fact or delegate to the owner page)")
    return out, suppressed


def signal_authority_missing(ctx):
    """Pages likely needing authority metadata but lacking authority_kind.

    The template version only uses generic signals available in every configured
    wiki: dated Status notes and review_by checkpoints. Domain-specific owner
    registries can add stricter checks later through an explicit tooling change.
    """
    candidates = []
    suppressed = 0
    for p in sorted(ctx.pages):
        rel = str(p.relative_to(WIKI_ROOT))
        if p.parent.name == "sources":
            continue
        fm = ctx.data[p]["fm"]
        if "authority_kind" in fm:
            continue

        priority = None
        reason = None
        if ctx.data[p].get("status_date") is not None:
            priority = 0
            reason = "has dated Status note"
        elif fm.get("review_by"):
            priority = 1
            reason = "has review_by"
        if reason is None:
            continue

        if rel in ctx.adj["authority_missing"]:
            ctx.adj_used["authority_missing"].add(rel)
            suppressed += 1
            continue
        candidates.append((priority, rel, reason))

    out = [f"{rel}: {reason}" for _priority, rel, reason in sorted(candidates)]
    return out, suppressed


def signal_unconsumed_sources(ctx):
    """Source pages that no non-source entity page cites with an authored link.

    A source linked only by sibling sources, meta pages, or generated
    "Referenced by" blocks was filed but never integrated into the knowledge
    layer. The orphan check cannot see this class because batch-ingested sources
    can cross-link each other; accepted_orphans also suppresses this signal
    because an intentional standalone record is accepted as unconsumed too.
    """
    consumed = set()
    for p in ctx.pages:
        if p.parent.name != "sources":
            consumed |= ctx.outbound[p]

    out, suppressed = [], 0
    for p in sorted(ctx.pages):
        if p.parent.name != "sources" or p.stem in consumed:
            continue
        rel = str(p.relative_to(WIKI_ROOT))
        if rel in ctx.adj["unconsumed_sources"]:
            ctx.adj_used["unconsumed_sources"].add(rel)
            suppressed += 1
        elif rel in ctx.adj["orphans"]:
            ctx.adj_used["orphans"].add(rel)
            suppressed += 1
        else:
            out.append(f"{rel}: no authored link from any non-source entity page")
    return out, suppressed


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


# Ingest entries since the last synthesis pass that count as a burst worth
# distilling. The synthesize workflow stays manual and approval-gated; this only
# surfaces the trigger.
SYNTHESIS_BURST_THRESHOLD = 8


def signal_synthesis_due(ctx):
    """Ingest burst with no synthesis pass following. Counts `ingest` log
    entries after the most recent `synthesis` entry (all of them if none); at
    SYNTHESIS_BURST_THRESHOLD or more, surfaces a candidate so the synthesize
    trigger does not depend on remembering to notice a burst. Self-clearing:
    logging a synthesis pass resets the count."""
    _ = ctx
    path = WIKI_ROOT / "log.md"
    if not path.exists():
        return [], 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return [], 0
    ingests_since = 0
    for line in lines:
        # Type extraction shares the header grammar (parse_log_entry_type in
        # _wiki_parse), so both live header forms are recognized identically.
        entry_type = parse_log_entry_type(line) or ""
        if entry_type.startswith("synthesis"):
            ingests_since = 0
        elif entry_type == "ingest":
            ingests_since += 1
    if ingests_since < SYNTHESIS_BURST_THRESHOLD:
        return [], 0
    return ([f"{ingests_since} ingest entries since the last synthesis pass "
             f"(threshold {SYNTHESIS_BURST_THRESHOLD}); consider a synthesize run"], 0)


def signal_review_due(ctx):
    """Pages whose review_by date has passed (outcome grading due). Mirrors
    review_due.py on the most-frequently-run surface, so a due review cannot
    wait unseen for the next /wiki-eval; the grading itself stays the review
    workflow's judgment. Self-clearing: grading advances or clears review_by."""
    _ = ctx
    due, _bad = collect_review_due(WIKI_ROOT, date.today())
    return ([f"{rel} (review_by {val}, {overdue} day(s) overdue)"
             for overdue, rel, val in due], 0)


def _adjudication_entry_labels(category, entries):
    """Human-readable labels for dead adjudication entries of one category."""
    out = []
    for e in sorted(entries, key=repr):
        if isinstance(e, frozenset):
            out.append(f"{category}: " + " ~ ".join(sorted(e)))
        elif isinstance(e, tuple):
            out.append(f"{category}: " + " -> ".join(str(x) for x in e))
        else:
            out.append(f"{category}: {e}")
    return out


def signal_adjudication_dead(ctx):
    """Adjudication entries that suppressed nothing this run. A dead entry means
    the candidate it settled no longer fires at all, so the suppression is inert
    residue; prune it (or keep it deliberately, if the candidate is expected to
    return). tier2() computes this after every other signal regardless of
    registry position, because it reads which entries those signals actually
    consumed via ctx.adj_used.

    hub_pages is excluded on purpose: it suppresses event-driven co-citation
    candidates that can legitimately go quiet between events and re-fire later,
    so "suppressed nothing this run" says nothing about whether the entry is
    inert. The lint workflow documents the exclusion."""
    out = []
    names = {
        "orphans": "accepted_orphans",
        "pairs": "skipped_crossref_pairs", "confidence": "reviewed_confidence_low",
        "duplicates": "reviewed_near_duplicates", "quotes": "reviewed_quotes",
        "recompile": "reviewed_recompile_candidates",
        "authority_missing": "reviewed_authority_missing",
        "glossary_volatile": "reviewed_glossary_volatile",
        "unconsumed_sources": "reviewed_unconsumed_sources",
    }
    for key, category in names.items():
        dead = ctx.adj[key] - ctx.adj_used[key]
        out.extend(_adjudication_entry_labels(category, dead))
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
    ("missing_related", "missing cross-refs (link profiles >=50% overlapping, not linked)", signal_missing_related),
    ("log_rotation_due", "log rotation due", signal_log_rotation_due),
    ("sourcing_queue_count_drift", "sourcing queue entity count drift", signal_sourcing_queue_count_drift),
    ("recompile_candidates", "compiled pages with newer source inputs (review for no-change, small update, or recompile)", signal_recompile_candidates),
    ("glossary_volatile_status", "glossary entries restating volatile status (rewrite to a dated fact or delegate to the owner page)", signal_glossary_volatile_status),
    ("authority_missing", "pages likely needing authority metadata but lacking authority_kind", signal_authority_missing),
    ("unconsumed_sources", "source pages not consumed by any non-source entity page (wire an authored link or adjudicate)", signal_unconsumed_sources),
    ("review_by_missing", "decisions with no review_by (enroll in the outcome-review loop or leave for now)", signal_review_by_missing),
    ("review_due", "outcome reviews due (review_by has passed; run the review workflow)", signal_review_due),
    ("synthesis_due", "ingest burst with no synthesis pass following (consider a synthesize run)", signal_synthesis_due),
    # adjudication_dead's row sets its report position; tier2() computes it
    # after every other signal regardless of where this row sits, because it
    # reads which adjudication entries the other signals consumed.
    ("adjudication_dead", "adjudication entries suppressing nothing this run (prune or keep deliberately)", signal_adjudication_dead),
)


def tier2(entity_pages, valid_slugs, adjudicated):
    ctx = Tier2Context(list(entity_pages), valid_slugs, adjudicated)

    out = {}
    suppressed = 0
    for key, _label, signal in TIER2_SIGNALS:
        if signal is signal_adjudication_dead:
            continue
        items, delta = signal(ctx)
        out[key] = items
        suppressed += delta

    # Computed after the loop so it sees every other signal's adjudication
    # consumption; the ordering is structural, not a "keep this row last" rule.
    dead_items, dead_delta = signal_adjudication_dead(ctx)
    out["adjudication_dead"] = dead_items
    suppressed += dead_delta

    out["_suppressed"] = suppressed
    return out


# --------------------------- reporting ---------------------------

def parse_index_targets():
    """(targets, duplicates, read_fails): every .md path index.md links, plus
    the paths more than one row points to (the uniqueness half of "one row per
    page"). read_fails carries root-cause file read problems."""
    idx = WIKI_ROOT / "index.md"
    if not idx.exists():
        return set(), [], []
    try:
        text = idx.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return set(), [], [("index", str(idx), f"not valid UTF-8: {e}")]
    targets = re.findall(r"\]\(([^)]+?\.md)\)", text)
    seen, dups = set(), set()
    for t in targets:
        if t in seen:
            dups.add(t)
        seen.add(t)
    return seen, sorted(dups), []


def main():
    ap = argparse.ArgumentParser(description="Lint the wiki by enforcement tier.")
    ap.add_argument("--strict", action="store_true", help="fail on Tier-2 candidates too")
    ap.add_argument("--tier1", action="store_true", help="run Tier 1 only")
    args = ap.parse_args()

    if not WIKI_ROOT.exists():
        print(f"Error: 'wiki/' not found. Run from the repo root. cwd={Path.cwd()}",
              file=sys.stderr)
        return 2

    entity_pages = [
        path for path in get_entity_pages(WIKI_ROOT)
        if not path.is_symlink() and path.is_file()
    ]
    valid_slugs = {p.stem for p in entity_pages} | META_PAGES
    index_targets, index_duplicates, index_read_fails = parse_index_targets()

    print(f"Wiki lint: {len(entity_pages)} entity pages\n")

    t1 = tier1(entity_pages, valid_slugs, index_targets, index_duplicates,
               index_read_fails)
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
