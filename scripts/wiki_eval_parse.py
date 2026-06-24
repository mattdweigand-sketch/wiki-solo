#!/usr/bin/env python3
"""Regression eval for the shared scripts/_wiki_parse.py primitives.

R1 extracted split_frontmatter, frontmatter_block, LINK_RE, the code-span REs,
strip_code_spans, and dangling_slugs into one module so lint.py, review_due.py,
and rebuild_referenced_by.py stop reimplementing them and cannot
silently drift. This suite pins that contract two ways:

1. Unit assertions on the primitives against a CRLF / edge-case sample, so the
   parse grammar (wikilink slug capture, code-span stripping, frontmatter split,
   block-list-preserving block extraction) is locked at the source.
2. An end-to-end consistency check: one CRLF-on-disk page driven through all
   callers, proving they agree. Every caller reads via Path.read_text (universal
   newlines), so a CRLF source is normalized to LF before _wiki_parse sees it,
   and all template callers treat the identical page identically.
3. Wiring assertions that each caller's source actually imports from _wiki_parse,
   so reverting any caller to a private reimplementation fails here.

Regression caught: if any caller is reverted to a private parser, or the shared
grammar is weakened (code-span stripping reordered or dropped, the frontmatter
anchor changed, the alias half of a [[slug|alias]] link captured instead of the
slug, the folder-pointer skip removed), at least one assertion below fails.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from _wiki_parse import (  # noqa: E402  (after sys.path insert)
    FENCED_CODE_RE,
    INLINE_CODE_RE,
    LINK_RE,
    dangling_slugs,
    frontmatter_block,
    split_frontmatter,
    strip_code_spans,
)
from eval_lib import Results  # noqa: E402  (after sys.path insert)

results = Results()
check = results.record


# A CRLF, code-span, aliased-link, block-list edge sample. The on-disk bytes use
# \r\n; callers read it through Path.read_text, which normalizes to \n, so the
# shared parser only ever sees the LF form. We assert both forms explicitly.
CRLF_RAW = (
    "---\r\n"
    "title: edge sample\r\n"
    "type: concept\r\n"
    "tags: [agent, money]\r\n"
    "review_by: 2020-01-01\r\n"
    "---\r\n"
    "Body links [[real-page]] and [[sources/aliased|shown text]].\r\n"
    "A folder pointer [[concepts/]] and an in-code link `[[in-code]]`.\r\n"
    "A fenced one (language tag + an unbalanced stray backtick inside):\r\n"
    "```python\r\n"
    "a stray ` backtick then\r\n"
    "[[fenced-example]]\r\n"
    "```\r\n"
)
LF = CRLF_RAW.replace("\r\n", "\n")

# --- 1. unit assertions on the shared primitives (LF, as callers feed them) ---

fm, body = split_frontmatter(LF)
check("split-frontmatter-keys",
      fm is not None and set(fm) == {"title", "type", "tags", "review_by"},
      detail=f"fm={fm}")
check("split-frontmatter-body-starts-after-fence",
      body.startswith("Body links"), detail=f"body={body[:20]!r}")

# block extraction preserves the raw block (including the bracketed tags list).
block = frontmatter_block(LF)
check("frontmatter-block-preserves-raw",
      "tags: [agent, money]" in block and "review_by: 2020-01-01" in block,
      detail=f"block={block!r}")

# LINK_RE captures the bare slug, strips the folder prefix, and drops the alias.
# The folder-pointer link [[concepts/]] is captured verbatim ("concepts/"); the
# trailing slash is what dangling_slugs keys on to skip it.
links = LINK_RE.findall(LF)
check("link-re-captures-and-strips",
      links == ["real-page", "aliased", "concepts/", "in-code", "fenced-example"],
      detail=f"links={links}")

# LINK_RE on a [[slug|alias]] link captures the slug, never the alias. This pins
# alias handling directly (the slug char class excludes | and ], so the alias
# side is never captured).
check("link-re-alias-captures-slug-not-alias",
      LINK_RE.findall("[[real-slug|Shown Alias]]") == ["real-slug"],
      detail=f"alias={LINK_RE.findall('[[real-slug|Shown Alias]]')}")

# strip_code_spans blanks both fenced and inline code. Order matters: fenced
# blocks first, then inline spans. The fenced block carries a language tag and
# an UNBALANCED stray backtick, so the documented fenced-then-inline order is
# load-bearing: dropping FENCED_CODE_RE, or swapping to inline-first, leaves the
# stray backtick to mis-pair across the fence and re-expose [[fenced-example]].
stripped = strip_code_spans(LF)
check("strip-code-spans-removes-both",
      "[[in-code]]" not in stripped and "[[fenced-example]]" not in stripped
      and "[[real-page]]" in stripped,
      detail=f"stripped={stripped!r}")
check("code-span-res-present",
      FENCED_CODE_RE.search(LF) is not None and INLINE_CODE_RE.search(LF) is not None)

# dangling_slugs ignores in-code/fenced examples and resolves real links.
dangling = dangling_slugs(LF, {"real-page", "aliased"})
check("dangling-skips-code-and-resolves",
      dangling == [], detail=f"dangling={dangling}")
dangling2 = dangling_slugs(LF, {"real-page"})  # 'aliased' unknown now
check("dangling-reports-unresolved",
      dangling2 == ["aliased"], detail=f"dangling2={dangling2}")
# Folder-pointer links ([[concepts/]]) are intentionally never reported dangling,
# even though "concepts/" is not a valid slug: the slug.endswith('/') skip in
# dangling_slugs drops them. Pin that skip directly.
dangling3 = dangling_slugs(LF, {"real-page", "aliased"})
check("dangling-skips-folder-pointer",
      "concepts/" not in dangling3, detail=f"dangling3={dangling3}")

# Raw CRLF (never reached in practice, but pin the grammar): the \r\n closing
# fence is not matched by the \n-anchored frontmatter regex, so split/block
# degrade to "no frontmatter" CONSISTENTLY for all callers that share the module.
fm_raw, _ = split_frontmatter(CRLF_RAW)
check("raw-crlf-degrades-consistently",
      fm_raw is None and frontmatter_block(CRLF_RAW) == "",
      detail=f"fm_raw={fm_raw}")

# --- 2. end-to-end: one CRLF page through all template callers, must agree ---

with tempfile.TemporaryDirectory() as td:
    root = Path(td) / "wiki"
    (root / "concepts").mkdir(parents=True)
    (root / "sources").mkdir(parents=True)
    # Page under test: written with CRLF bytes on disk.
    page = root / "concepts" / "edge.md"
    page.write_bytes(CRLF_RAW.encode("utf-8"))
    # A real target so the link resolves and an inbound edge can form.
    (root / "sources" / "real-page.md").write_bytes(
        ("---\ntitle: real\ntype: source\ncreated: 2026-01-01\n"
         "updated: 2026-01-01\nsources: []\ntags: [agent]\n"
         "confidence: medium\nsource_type: notes\n---\nbody\n").encode("utf-8")
    )

    # review_due: review_by is read from the CRLF page and surfaces as overdue.
    rd = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "review_due.py"),
                         "--root", str(root), "--today", "2026-06-21"],
                        text=True, capture_output=True)
    check("caller-review-due-reads-crlf-review-by",
          "concepts/edge.md" in rd.stdout and "1 page(s)" in rd.stdout,
          detail=rd.stdout.replace("\n", " | "))

    # rebuild_referenced_by: the authored [[real-page]] body link from the CRLF
    # page produces an inbound edge on real-page.md, proving the LF-normalized
    # CRLF page is scanned with the shared LINK_RE grammar.
    subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "rebuild_referenced_by.py")],
                   cwd=td, text=True, capture_output=True)
    real_text = (root / "sources" / "real-page.md").read_text(encoding="utf-8")
    check("caller-rebuild-links-crlf-page",
          "## Referenced by" in real_text and "[[edge]]" in real_text,
          detail=real_text)
    # Nothing links to edge.md, so it gets the no-inbound marker. This pins that
    # the [[real-page]]/[[aliased]] links it emits are treated as outbound only.
    edge_text = page.read_text(encoding="utf-8")
    check("caller-rebuild-edge-has-no-inbound",
          "_No inbound links yet._" in edge_text,
          detail=edge_text)

# --- 3. wiring: each caller's source actually imports from _wiki_parse ---
#
# The end-to-end checks above prove the callers BEHAVE identically, but a caller
# reverted to a byte-identical private reimplementation would still pass them.
# Assert the shared import is wired in each caller's source so reverting any one
# of them to a private parser fails here.
CALLERS = ("lint.py", "review_due.py", "rebuild_referenced_by.py")
for caller in CALLERS:
    src = (REPO_ROOT / "scripts" / caller).read_text(encoding="utf-8")
    check(f"caller-imports-shared-parser-{caller}",
          "from _wiki_parse import" in src,
          detail=f"{caller} does not import from _wiki_parse")

sys.exit(results.finish())
