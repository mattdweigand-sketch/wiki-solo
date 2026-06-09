"""Shared self-contained source fixtures for wiki eval scripts."""

from __future__ import annotations

from pathlib import Path


TEXT_SOURCES = {
    "raw/ai-research/folder-organization-guide.md": "# Folder Organization Guide\n\nFixture source for no-write harness evaluation.\n",
    "raw/videos/2026-06-08-pewdiepie-did-it-again.md": "# Pewdiepie Did It Again\n\nFixture source used to exercise existing-source and apply-boundary behavior.\n",
}

IMAGE_SOURCES = {
    "raw/social/2026-06-08-deep-agents-rubrics-sydney-runkle.jpg": b"fixture image placeholder\n",
}

def ensure_eval_sources() -> None:
    for path_text, content in TEXT_SOURCES.items():
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    for path_text, content in IMAGE_SOURCES.items():
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)

    stale_sidecar = Path("raw/social/2026-06-08-deep-agents-rubrics-sydney-runkle.ocr.txt")
    if stale_sidecar.exists():
        stale_sidecar.unlink()


def write_existing_source_page() -> Path:
    path = Path("wiki/sources/pewdiepie-did-it-again.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
title: Pewdiepie Did It Again
type: source
created: 2026-06-08
updated: 2026-06-08
sources: [2026-06-08-pewdiepie-did-it-again.md]
source_type: synthesis
tags: [fixture]
confidence: medium
---

Fixture source page for no-write harness evaluation.

## Referenced by

_No inbound links yet._
""",
        encoding="utf-8",
    )
    return path


def remove_existing_source_page() -> None:
    path = Path("wiki/sources/pewdiepie-did-it-again.md")
    if path.exists():
        path.unlink()
