#!/usr/bin/env python3
"""Regression evals for rotate_log.py.

The rotator is allowed to mutate wiki/log.md, but only when explicitly run. These
cases exercise it in temporary repos so the live wiki is never touched.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rotate_log  # noqa: E402
from eval_lib import Results  # noqa: E402


ROTATE = REPO_ROOT / "scripts" / "rotate_log.py"
LINT = REPO_ROOT / "scripts" / "lint.py"
LINT_FIXTURE = REPO_ROOT / "scripts" / "fixtures" / "wiki-lint"

ROTATION_DATE = "2026-06-27"


def write_log(root: Path, entries: list[str], header: str | None = None) -> None:
    header = header or (
        "# Wiki Log\n"
        "\n"
        "Append-only, oldest first.\n"
        "\n"
        "---\n"
        "\n"
    )
    path = root / "wiki" / "log.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "".join(entries), encoding="utf-8")


def plain_entry(day: int, title: str, extra: str = "") -> str:
    body = extra or f"Body line for plain entry {day}.\n"
    return (
        f"## 2026-01-{day:02d} | {title}\n"
        f"Action: fixture {day}.\n"
        f"{body}"
        "Verification: fixture.\n"
        "\n"
    )


def bracket_entry(day: int, title: str, extra: str = "") -> str:
    body = extra or f"Body line for bracket entry {day}.\n"
    return (
        f"## [2026-01-{day:02d}] {title}\n"
        f"Action: fixture {day}.\n"
        f"{body}"
        "Verification: fixture.\n"
        "\n"
    )


def run_rotate(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROTATE), "--date", ROTATION_DATE, *args],
        cwd=root,
        text=True,
        capture_output=True,
    )


def parse_entries_from_text(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    _, entries = rotate_log.parse_log(lines)
    return ["".join(entry.lines) for entry in entries]


def archive_payload(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "\n---\n\n"
    assert marker in text, "archive header marker missing"
    payload = text.split(marker, 1)[1]
    if payload.endswith("\n---\n"):
        payload += "\n"
    return payload


def live_original_entries(root: Path) -> list[str]:
    entries = parse_entries_from_text((root / "wiki" / "log.md").read_text(encoding="utf-8"))
    original_entries = [entry for entry in entries if "maintenance | Log rotation" not in entry]
    if original_entries and original_entries[-1].endswith("\n---\n\n"):
        original_entries[-1] = original_entries[-1][:-len("\n---\n\n")]
    return original_entries


def with_temp_root(fn) -> None:
    with tempfile.TemporaryDirectory(prefix="wiki-rotate-eval-") as td:
        fn(Path(td))


results = Results()
record = results.record


def case_rotates_losslessly(root: Path) -> None:
    entries = [
        plain_entry(1, "bootstrap", "Body date 2025-10-28 must not name archive.\n"),
        plain_entry(2, "second"),
        bracket_entry(3, "ingest | third"),
        bracket_entry(4, "maintenance | fourth", "Future body date 2026-12-31 must not name archive.\n"),
        bracket_entry(5, "promotion | fifth"),
        bracket_entry(6, "query | sixth"),
        bracket_entry(7, "ingest | seventh"),
        bracket_entry(8, "lint"),
    ]
    write_log(root, entries)
    original_entries = parse_entries_from_text((root / "wiki" / "log.md").read_text(encoding="utf-8"))
    target = 35

    proc = run_rotate(root, "--target-lines", str(target))
    archive_files = sorted((root / "archive" / "wiki-log").glob("*.md"))
    archive_entries = parse_entries_from_text(archive_payload(archive_files[0]))
    kept_entries = live_original_entries(root)
    live_line_count = len((root / "wiki" / "log.md").read_text(encoding="utf-8").splitlines())

    record("rotate-exits-zero", proc.returncode == 0, proc.stderr.strip())
    record("rotates-under-target", live_line_count <= target, f"{live_line_count} > {target}")
    record("archive-created-on-header-dates",
           len(archive_files) == 1
           and archive_files[0].name.startswith("2026-01-01-to-")
           and "2025-10-28" not in archive_files[0].name
           and "2026-12-31" not in archive_files[0].name,
           f"archive files: {[p.name for p in archive_files]}")
    record("archive-has-human-header",
           archive_files and "Rotated Wiki Log" in archive_files[0].read_text(encoding="utf-8"),
           "archive header missing")
    record("live-log-has-pointer",
           "Archived entries:" in (root / "wiki" / "log.md").read_text(encoding="utf-8"),
           "live log pointer missing")
    record("live-log-has-rotation-entry",
           "maintenance | Log rotation" in (root / "wiki" / "log.md").read_text(encoding="utf-8"),
           "rotation entry missing")
    record("payload-conserved",
           original_entries == archive_entries + kept_entries,
           "original entries were not exactly partitioned across archive and live log")

    before_second = {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*.md"))
    }
    second = run_rotate(root, "--target-lines", str(target))
    after_second = {
        str(p.relative_to(root)): p.read_text(encoding="utf-8")
        for p in sorted(root.rglob("*.md"))
    }
    record("second-run-noop",
           second.returncode == 0 and before_second == after_second and "No rotation needed" in second.stdout,
           f"stdout={second.stdout!r} stderr={second.stderr!r}")


with_temp_root(case_rotates_losslessly)


def case_dry_run_no_write(root: Path) -> None:
    entries = [plain_entry(i, f"entry {i}") for i in range(1, 8)]
    write_log(root, entries)
    before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    proc = run_rotate(root, "--dry-run", "--target-lines", "30")
    after = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    record("dry-run-no-write",
           proc.returncode == 0 and before == after and not (root / "archive").exists(),
           f"stdout={proc.stdout!r} stderr={proc.stderr!r}")


with_temp_root(case_dry_run_no_write)


def case_under_target_noop(root: Path) -> None:
    write_log(root, [plain_entry(1, "small"), bracket_entry(2, "small | two")])
    before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    proc = run_rotate(root, "--target-lines", "80")
    after = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    record("under-target-left-untouched",
           proc.returncode == 0 and before == after and "No rotation needed" in proc.stdout,
           f"stdout={proc.stdout!r} stderr={proc.stderr!r}")


with_temp_root(case_under_target_noop)


def case_target_validation(root: Path) -> None:
    write_log(root, [plain_entry(i, f"entry {i}") for i in range(1, 8)])
    before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    bad_target = rotate_log.LOG_ROTATION_WARN_LINES - rotate_log.MIN_ROTATION_HEADROOM_LINES
    proc = run_rotate(root, "--target-lines", str(bad_target))
    after = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    record("target-at-headroom-rejected",
           proc.returncode != 0 and before == after and "must be below" in proc.stderr,
           f"stdout={proc.stdout!r} stderr={proc.stderr!r}")


with_temp_root(case_target_validation)


def case_newest_entry_floor(root: Path) -> None:
    huge_body = "".join(f"Newest line {i}.\n" for i in range(40))
    write_log(root, [plain_entry(1, "old"), bracket_entry(2, "huge newest", huge_body)])
    before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    proc = run_rotate(root, "--target-lines", "20")
    after = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    record("newest-entry-floor-refuses-impossible-cut",
           proc.returncode != 0 and before == after and not (root / "archive").exists(),
           f"stdout={proc.stdout!r} stderr={proc.stderr!r}")


with_temp_root(case_newest_entry_floor)


def case_archive_collision_refused(root: Path) -> None:
    """The one potential data-loss path: a rerun on a LATER date produces the
    same archive filename with different content (the rotation date is embedded
    in the header). The script must refuse, leave both files untouched, and name
    the recovery path; the same-date rerun completing an interrupted rotation is
    covered by second-run-noop."""
    entries = [plain_entry(i, f"entry {i}") for i in range(1, 8)]
    write_log(root, entries)
    proc = run_rotate(root, "--target-lines", "30")
    archive_files = sorted((root / "archive" / "wiki-log").glob("*.md"))
    assert proc.returncode == 0 and len(archive_files) == 1, proc.stderr
    archive_before = archive_files[0].read_text(encoding="utf-8")

    # Restore the pre-rotation log (simulating an interrupted rotation whose
    # archive was written but whose log rewrite is being retried later), then
    # re-run with a DIFFERENT date so the would-be archive content differs.
    write_log(root, entries)
    log_before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    later = subprocess.run(
        [sys.executable, str(ROTATE), "--date", "2026-06-28", "--target-lines", "30"],
        cwd=root, text=True, capture_output=True,
    )
    record("later-date-collision-refused",
           later.returncode != 0
           and "already exists with different content" in later.stderr,
           f"stdout={later.stdout!r} stderr={later.stderr!r}")
    record("collision-refusal-names-recovery",
           "re-run with the original" in later.stderr and "--date" in later.stderr,
           f"stderr={later.stderr!r}")
    record("collision-leaves-both-files-untouched",
           archive_files[0].read_text(encoding="utf-8") == archive_before
           and (root / "wiki" / "log.md").read_text(encoding="utf-8") == log_before,
           "archive or live log changed during a refused rotation")

    # Same-date rerun after the interruption completes the log rewrite against
    # the identical existing archive (the documented recovery path).
    recover = run_rotate(root, "--target-lines", "30")
    record("same-date-rerun-completes-recovery",
           recover.returncode == 0
           and archive_files[0].read_text(encoding="utf-8") == archive_before
           and "maintenance | Log rotation"
               in (root / "wiki" / "log.md").read_text(encoding="utf-8"),
           f"stdout={recover.stdout!r} stderr={recover.stderr!r}")


with_temp_root(case_archive_collision_refused)


def case_no_recognized_headers(root: Path) -> None:
    write_log(root, ["Free prose with no entry headers at all.\n" for _ in range(40)])
    before = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    proc = run_rotate(root, "--target-lines", "30")
    after = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    record("no-recognized-headers-refused",
           proc.returncode != 0 and before == after
           and "no recognized log entry headers" in proc.stderr
           and not (root / "archive").exists(),
           f"stdout={proc.stdout!r} stderr={proc.stderr!r}")


with_temp_root(case_no_recognized_headers)


def case_archive_ignored_by_lint(root: Path) -> None:
    shutil.copytree(LINT_FIXTURE / "wiki", root / "wiki")
    shutil.copytree(LINT_FIXTURE / "scripts", root / "scripts")
    entries = [plain_entry(i, f"entry {i}") for i in range(1, 8)]
    write_log(root, entries)
    proc = run_rotate(root, "--target-lines", "30")
    lint = subprocess.run(
        [sys.executable, str(LINT), "--tier1"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    record("archive-ignored-by-tier1-lint",
           proc.returncode == 0 and lint.returncode == 0,
           f"rotate stderr={proc.stderr!r}; lint stdout={lint.stdout!r}; lint stderr={lint.stderr!r}")


with_temp_root(case_archive_ignored_by_lint)


sys.exit(results.finish())
