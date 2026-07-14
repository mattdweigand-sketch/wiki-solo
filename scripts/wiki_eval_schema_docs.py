#!/usr/bin/env python3
"""Regression eval for check_schema_doc_parity.py.

Negative controls: a minimal parity-clean fixture tree is seeded with each
problem class the checker claims to catch (missing value, extra value, missing
marker, duplicate marker, unknown key, malformed marker, unregistered marker,
and unparseable following block) and each must report the corresponding
message, so the checker cannot silently go vacuous. Positive controls: the
clean fixture and the live repo schema docs both pass.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from check_schema_doc_parity import _live_constants, schema_doc_parity_problems
from eval_lib import Results

results = Results()

PREFERRED_ORDER = {
    "VALID_CONFIDENCE": ("high", "medium", "low", "contested"),
    "VALID_SOURCE_TYPE": (
        "book", "article", "podcast", "course", "conversation", "notes",
        "research", "video", "journal", "receipt", "other",
    ),
    "VALID_AUTHORITY_KIND": (
        "raw-source", "source-page", "owner-page", "external-url",
        "local-resource", "mixed", "none",
    ),
    "VALID_AUTHORITY_FRESHNESS": (
        "immutable-source", "stable-meaning", "current-state", "event-log",
        "predictive", "deprecated",
    ),
    "RELATED_LABELS": (
        "Supports", "Contradicts", "Depends on", "Derived from", "Part of",
        "Related",
    ),
}


def ordered(constants: dict[str, set[str]], name: str) -> list[str]:
    """Return a stable doc-order list for a constant set."""
    values = set(constants[name])
    preferred = [value for value in PREFERRED_ORDER.get(name, ()) if value in values]
    return preferred + sorted(values - set(preferred))


def pipe(values: list[str]) -> str:
    return " | ".join(values)


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"fixture text not found in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def build_clean_tree(root: Path, constants: dict[str, set[str]]) -> None:
    """A minimal parity-clean schema-doc tree, generated from constants so the
    fixture cannot drift from itself."""
    (root / "wiki").mkdir(parents=True)

    folders = sorted(constants["FOLDER_TYPE_KEYS"])
    types = sorted(constants["FOLDER_TYPE_VALUES"])
    source_types = ordered(constants, "VALID_SOURCE_TYPE")
    confidence = ordered(constants, "VALID_CONFIDENCE")
    authority_kind = ordered(constants, "VALID_AUTHORITY_KIND")
    authority_freshness = ordered(constants, "VALID_AUTHORITY_FRESHNESS")
    labels = ordered(constants, "RELATED_LABELS")

    (root / "AGENTS.md").write_text(
        "# Fixture Agents\n\n"
        "<!-- parity:enum key=entity-folders -->\n"
        f"**Entity types:** {', '.join(folders)}\n",
        encoding="utf-8",
    )

    entity_rows = "\n".join(
        f"| **{folder.title()}** | `wiki/{folder}/` | Fixture purpose |"
        for folder in folders
    )
    freshness_rows = "\n".join(
        f"| `{value}` | Fixture default |" for value in authority_freshness
    )
    source_type_rows = "\n".join(
        f"| `{value}` | Fixture trust | Fixture care | Fixture emphasis |"
        for value in source_types
    )
    confidence_lines = "\n".join(
        f"- `{value}` - Fixture meaning" for value in confidence
    )
    schema = (
        "# Wiki Schema Reference\n\n"
        "## Entity Types\n\n"
        "<!-- parity:enum key=entity-table-folders -->\n"
        "| Type | Location | Purpose |\n"
        "|---|---|---|\n"
        f"{entity_rows}\n\n"
        "## Page Format\n\n"
        "\\`\\`\\`yaml\n"
        "---\n"
        "title: <page title>\n"
        "<!-- parity:enum key=entity-type -->\n"
        f"type: {pipe(types)}\n"
        "created: YYYY-MM-DD\n"
        "updated: YYYY-MM-DD\n"
        "sources: []\n"
        "<!-- parity:enum key=source-type -->\n"
        f"source_type: {pipe(source_types)}  # SOURCE PAGES ONLY\n"
        "tags: []\n"
        "<!-- parity:enum key=confidence -->\n"
        f"confidence: {pipe(confidence)}\n"
        "---\n"
        "\\`\\`\\`\n\n"
        "Optional authority metadata:\n\n"
        "<!-- parity:enum key=authority-kind -->\n"
        f"- `authority_kind: {pipe(authority_kind)}`\n"
        "- `authority_ref: <path>`\n"
        "<!-- parity:enum key=authority-freshness -->\n"
        f"- `authority_freshness: {pipe(authority_freshness)}`\n\n"
        "Freshness defaults guide authoring.\n\n"
        "<!-- parity:enum key=freshness-defaults -->\n"
        "| authority_freshness | Default for |\n"
        "|---|---|\n"
        f"{freshness_rows}\n\n"
        "**Typed relationship labels:** The vocabulary is enforced by "
        "`RELATED_LABELS` in `scripts/lint.py`, the meanings table lives in "
        "`REFERENCES.md`, and the `schema-docs` eval suite enforces this.\n\n"
        "## Source-Type Summary Templates\n\n"
        "<!-- parity:enum key=source-type-table -->\n"
        "| `source_type` | Trustworthy for | Treat with care | Summary should emphasize |\n"
        "|---|---|---|---|\n"
        f"{source_type_rows}\n\n"
        "## Confidence Values\n\n"
        "<!-- parity:enum key=confidence-values -->\n"
        f"{confidence_lines}\n"
    )
    (root / "wiki" / "SCHEMA.md").write_text(schema, encoding="utf-8")

    label_rows = "\n".join(
        f"| `{label}` | Fixture meaning |" for label in labels
    )
    references = (
        "# Wiki References\n\n"
        "## Cross-Referencing Rules\n\n"
        "<!-- parity:enum key=related-labels -->\n"
        "| Label | Meaning |\n"
        "|---|---|\n"
        f"{label_rows}\n\n"
        "Format each item as `- Label: [[page]]`. To add a label, update "
        "`RELATED_LABELS` and this table together; the `schema-docs` eval "
        "suite enforces this.\n"
    )
    (root / "REFERENCES.md").write_text(references, encoding="utf-8")


CONSTANTS = _live_constants()
MISSING_CONFIDENCE_VALUE = (
    "contested" if "contested" in CONSTANTS["VALID_CONFIDENCE"]
    else ordered(CONSTANTS, "VALID_CONFIDENCE")[-1]
)


def drop_confidence_value(root: Path) -> None:
    path = root / "wiki" / "SCHEMA.md"
    old_values = ordered(CONSTANTS, "VALID_CONFIDENCE")
    new_values = [value for value in old_values if value != MISSING_CONFIDENCE_VALUE]
    replace_once(
        path,
        f"confidence: {pipe(old_values)}",
        f"confidence: {pipe(new_values)}",
    )


def add_extra_label(root: Path) -> None:
    path = root / "REFERENCES.md"
    replace_once(
        path,
        "| `Related` | Fixture meaning |\n\n",
        "| `Related` | Fixture meaning |\n| `Bogus` | Fixture meaning |\n\n",
    )


def delete_confidence_marker(root: Path) -> None:
    replace_once(
        root / "wiki" / "SCHEMA.md",
        "<!-- parity:enum key=confidence -->\n",
        "",
    )


def duplicate_confidence_marker(root: Path) -> None:
    marker = "<!-- parity:enum key=confidence -->\n"
    replace_once(root / "wiki" / "SCHEMA.md", marker, marker + marker)


def add_unknown_key(root: Path) -> None:
    replace_once(
        root / "wiki" / "SCHEMA.md",
        "# Wiki Schema Reference\n\n",
        "# Wiki Schema Reference\n\n<!-- parity:enum key=bogus -->\n\n",
    )


def malformed_marker(root: Path) -> None:
    replace_once(
        root / "wiki" / "SCHEMA.md",
        "<!-- parity:enum key=confidence -->",
        "<!-- parity enum key=confidence -->",
    )


def unregistered_marker(root: Path) -> None:
    (root / "wiki" / "glossary.md").write_text(
        "# Glossary\n\n"
        "<!-- parity:enum key=confidence -->\n"
        "- `high` - Fixture meaning\n",
        encoding="utf-8",
    )


def reword_confidence_block(root: Path) -> None:
    replace_once(
        root / "wiki" / "SCHEMA.md",
        f"confidence: {pipe(ordered(CONSTANTS, 'VALID_CONFIDENCE'))}",
        "confidence values are prose now",
    )


def break_inline_list(root: Path) -> None:
    path = root / "AGENTS.md"
    folders = sorted(CONSTANTS["FOLDER_TYPE_KEYS"])
    replace_once(
        path,
        f"**Entity types:** {', '.join(folders)}",
        "Entity types are prose now",
    )


def break_table_location(root: Path) -> None:
    replace_once(
        root / "wiki" / "SCHEMA.md",
        "| Type | Location | Purpose |",
        "| Type | Path | Purpose |",
    )


def break_table_first_column(root: Path) -> None:
    first = ordered(CONSTANTS, "VALID_AUTHORITY_FRESHNESS")[0]
    replace_once(
        root / "wiki" / "SCHEMA.md",
        f"| `{first}` | Fixture default |",
        "freshness rows are prose now",
    )


def break_bullet_enum(root: Path) -> None:
    first = ordered(CONSTANTS, "VALID_CONFIDENCE")[0]
    replace_once(
        root / "wiki" / "SCHEMA.md",
        f"- `{first}` - Fixture meaning",
        f"`{first}` is prose now",
    )


def case(name, mutate, expect_fragment):
    """Build the clean tree, apply `mutate(root)`, and assert on the problems:
    expect_fragment=None asserts a clean run; otherwise some problem line must
    contain the fragment."""
    with tempfile.TemporaryDirectory(prefix="wiki-schema-docs-eval-") as td:
        root = Path(td)
        build_clean_tree(root, CONSTANTS)
        if mutate:
            mutate(root)
        problems = schema_doc_parity_problems(repo_root=root, constants=CONSTANTS)
        if expect_fragment is None:
            ok = not problems
            detail = "unexpected problems: " + "; ".join(problems)
        else:
            ok = any(expect_fragment in p for p in problems)
            detail = f"expected {expect_fragment!r} in problems: {problems!r}"
        results.record(name, ok, detail)


case("clean-fixture-passes", None, None)
case(
    "missing-value-fires",
    drop_confidence_value,
    f"wiki/SCHEMA.md: confidence: enum drift missing-from-doc: {MISSING_CONFIDENCE_VALUE}",
)
case(
    "extra-value-fires",
    add_extra_label,
    "REFERENCES.md: related-labels: enum drift extra-in-doc: Bogus",
)
case(
    "missing-marker-fires",
    delete_confidence_marker,
    "wiki/SCHEMA.md: confidence: missing parity marker",
)
case(
    "duplicate-marker-fires",
    duplicate_confidence_marker,
    "wiki/SCHEMA.md: confidence: duplicate parity marker",
)
case(
    "unknown-key-fires",
    add_unknown_key,
    "wiki/SCHEMA.md: bogus: unknown parity marker key",
)
case(
    "near-miss-marker-fires",
    malformed_marker,
    "wiki/SCHEMA.md: malformed parity enum marker",
)
case(
    "unregistered-marker-fires",
    unregistered_marker,
    "wiki/glossary.md: unregistered parity enum marker",
)
case(
    "reworded-block-fires",
    reword_confidence_block,
    "wiki/SCHEMA.md: confidence: extraction failure for pipe-enum",
)
case(
    "inline-list-extraction-failure-fires",
    break_inline_list,
    "AGENTS.md: entity-folders: extraction failure for inline-list",
)
case(
    "table-location-extraction-failure-fires",
    break_table_location,
    "wiki/SCHEMA.md: entity-table-folders: extraction failure for table-location",
)
case(
    "table-first-column-extraction-failure-fires",
    break_table_first_column,
    "wiki/SCHEMA.md: freshness-defaults: extraction failure for table-first-column",
)
case(
    "bullet-enum-extraction-failure-fires",
    break_bullet_enum,
    "wiki/SCHEMA.md: confidence-values: extraction failure for bullet-enum",
)

live_problems = schema_doc_parity_problems()
results.record(
    "live-repo-passes",
    not live_problems,
    "problems: " + "; ".join(live_problems),
)

sys.exit(results.finish())
