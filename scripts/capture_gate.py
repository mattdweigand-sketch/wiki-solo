#!/usr/bin/env python3
"""Deterministic approval gate for capture, promotion, and synthesis.

The gate covers exactly three approval boundaries: filing an analysis
(analysis-capture), applying an artifact promotion (promotion-audit), and
promoting reviewed synthesis output (--kind=synthesis). Unapproved runs are
display-only. Approved reruns append or confirm a structured approval record
before the workflow applies the durable change.

Phases other than `accepted` never cross an approval boundary; the gate takes a
short non-approval path for them (route judgment lives in the routed prose
workflows). Two deterministic guards still apply on that path: no concrete
destination may sit under wiki/analyses/ (placeholders are skipped by design on
this display-only path), and every concrete destination must be under an
allowed durable root.

Determinism: the gate anchors on checkable facts, not only declared flags.
- Any capture route with a wiki/analyses/ destination in its declared scope
  requires --path to the drafted artifact; the gate counts its words itself.
  There is no declared word-count input. The synthesis branch may only touch
  wiki/analyses/ pages that already exist on disk; new analysis pages must go
  through the measured analysis-capture route.
- Approval-required routes reject placeholder ("<...>") paths anywhere in the
  approval scope (primary home and pages touched) and any path outside the
  allowed durable roots, so an approval names real, in-scope files. Before
  writing, every approval record is checked against validate_capture_runs.py's
  own rules; the gate never writes a record its validator would reject.
- synthesis approval displays the reviewed --drafts content and full edit scope
  before durable synthesis changes proceed.

Measurement scope: only word_count is measured (from --path); the measured file
is recorded as word_count_path. synthesized_pages is a declared value, never
measured; validate_capture_runs.py re-checks that declared number for the
3-page analysis qualification.

Exit codes:
  0: approved route is allowed to proceed
  2: approval required before proceeding
  3: invalid or blocked route (argparse usage errors are remapped here so that
     exit 2 always means exactly "approval required")
"""

from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path

from ledger_common import (
    ALLOWED_ROOTS,
    approved_at_now,
    split_scope,
    under_allowed_root,
    write_approval_record as _write_approval_record,
)
from validate_capture_runs import validate_approval


DEFAULT_APPROVAL_LEDGER = "scripts/capture-runs.jsonl"
SYNTHESIS_DEFAULT_HOME = "wiki/synthesis.md"

LEDGER_SCHEMA_DESCRIPTION = (
    "Append-only operational records written by scripts/capture_gate.py after "
    "the user approves exact analysis-capture, artifact-promotion, or synthesis "
    "approval scopes. Free routes such as ingest, decision capture, experience "
    "capture, and workflow updates remain unrecorded here."
)

ANALYSES_PREFIX = "wiki/analyses/"
APPROVAL_ROUTES = {"analysis-capture", "promotion-audit"}
FREE_PHASES = ("drafting", "source", "decision", "experience", "workflow")
# ALLOWED_ROOTS / ALLOWED_ROOT_FILES / under_allowed_root are single-sourced in
# ledger_common so the gate and its validator agree on the durable-root scope
# (and the raw/ exclusion) byte-for-byte.


PROMOTION_TRIGGERS = (
    "reusable_distinction",
    "ranking_or_framework",
    "open_question_resolution",
    "future_agent_behavior",
    "existing_page_update",
)

ACTION_LABELS = {
    "analysis-capture": "File a substantial research answer as an analysis page.",
    "promotion-audit": "Apply an artifact promotion to the wiki.",
}

TRIGGER_LABELS = {
    "reusable_distinction": "reusable distinction",
    "ranking_or_framework": "ranking or framework",
    "open_question_resolution": "open-question resolution",
    "future_agent_behavior": "future-agent behavior",
    "existing_page_update": "existing page update",
}


def yn(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"yes", "true", "1", "y"}:
        return True
    if lowered in {"no", "false", "0", "n"}:
        return False
    raise argparse.ArgumentTypeError("expected yes/no")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Require approval for wiki analysis capture, promotion, or synthesis.",
    )
    p.add_argument("--artifact", required=True, help="Short description of the artifact.")
    p.add_argument(
        "--kind",
        choices=["capture", "synthesis"],
        default="capture",
        help="Approval branch. Default capture preserves existing phase-derived behavior.",
    )
    p.add_argument(
        "--phase",
        choices=["accepted", *FREE_PHASES],
        help="Current state of the user request. Required for --kind=capture. Only "
             "'accepted' can derive an approval route; every other phase takes the "
             "short non-approval path.",
    )
    p.add_argument("--primary-home", default="", help="Exact intended path, if known.")
    p.add_argument("--pages-touched", default="", help="Comma-separated intended paths.")
    p.add_argument("--source-path", default="", help="Source path or URL if a source is involved.")
    p.add_argument(
        "--path",
        default="",
        help="Path to the drafted artifact on disk. Required whenever the primary "
             "home is under wiki/analyses/; the gate counts its words itself.",
    )
    p.add_argument("--drafts", default="", help="Reviewed synthesis content for --kind=synthesis.")
    p.add_argument("--synthesized-pages", type=int, default=0)
    p.add_argument(
        "--domain-context",
        dest="domain_context",
        type=yn,
        default=False,
        help="Whether the answer is about this wiki's configured domain.",
    )
    p.add_argument(
        "--life-context",
        dest="domain_context",
        type=yn,
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "--trigger",
        action="append",
        choices=PROMOTION_TRIGGERS,
        default=[],
        help="Reusable-artifact trigger. Repeat for multiple triggers.",
    )
    p.add_argument(
        "--approved",
        action="store_true",
        help="Set only after the user explicitly approves this exact route.",
    )
    p.add_argument(
        "--approval-ledger",
        default=DEFAULT_APPROVAL_LEDGER,
        help="JSONL file for approved capture, promotion, and synthesis records.",
    )
    return p


def is_placeholder(path: str) -> bool:
    return "<" in path or ">" in path


def is_analyses_path(path: str) -> bool:
    """Case-insensitive (the repo lives on case-insensitive APFS, so a
    case-variant spelling must not slip past the analyses rules) and
    directory-aware: normpath turns 'wiki/analyses/' into the bare
    'wiki/analyses', which is still the analyses folder."""
    lowered = path.lower()
    return lowered.startswith(ANALYSES_PREFIX) or lowered == ANALYSES_PREFIX.rstrip("/")


def normalize_path(path: str) -> str:
    """Resolve ./, //, and .. so destinations cannot be spelled around guards."""
    return posixpath.normpath(path.strip())


def real_destinations(home: str, pages_touched: str) -> list[str]:
    """Concrete declared destination paths, normalized."""
    out: list[str] = []
    for path in [home, *split_scope(pages_touched)]:
        path = path.strip()
        if not path or path == "none" or is_placeholder(path):
            continue
        out.append(normalize_path(path))
    return out


def measure_word_count(path: str) -> int | None:
    """Count word tokens in the drafted artifact, or None if it can't be read."""
    p = Path(path)
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return len(re.findall(r"\w+", text))


def classify_accepted(args: argparse.Namespace, word_count: int) -> tuple[str, str, str]:
    """Derive the route for --phase accepted, the only phase that can require
    approval. word_count is the measured count from --path (0 when no path)."""
    qualifies_analysis = (
        args.synthesized_pages >= 3 and word_count > 300 and args.domain_context
    )
    if qualifies_analysis:
        return (
            "analysis-capture",
            args.primary_home or "wiki/analyses/<slug>.md",
            "Matches the research analysis criteria: 3+ pages, >300 words, domain-context question.",
        )

    if args.trigger:
        trigger_labels = [TRIGGER_LABELS[trigger] for trigger in args.trigger]
        return (
            "promotion-audit",
            args.primary_home or "wiki/<page>.md",
            "Promotion trigger present: " + ", ".join(trigger_labels) + ".",
        )

    return (
        "chat-only",
        "none",
        "Does not meet analysis-capture criteria and has no promotion trigger.",
    )


def scope_with_home(home: str, pages_touched: str) -> list[str]:
    """pages_touched as a normalized, deduplicated list, guaranteeing a
    concrete primary_home is included."""
    scope = list(dict.fromkeys(normalize_path(p) for p in split_scope(pages_touched)))
    home = home.strip()
    if home and home != "none" and not is_placeholder(home) and home not in scope:
        scope.insert(0, home)
    return scope


def approval_guard(args: argparse.Namespace, route: str, home: str) -> str | None:
    """Block reasons for approval-required capture routes."""
    if not args.artifact.strip():
        return ("--artifact must be a non-empty description; the gate will not "
                "write an approval record its own validator would reject.")
    if is_placeholder(home) or not home or home == "none":
        return (f"{route} requires a concrete --primary-home path "
                "(no placeholder); name the real durable destination.")
    placeholders = [p for p in split_scope(args.pages_touched) if is_placeholder(p)]
    if placeholders:
        return (f"approval scope must name concrete paths, not placeholders: "
                f"{placeholders}")
    if any(p == "none" for p in split_scope(args.pages_touched)):
        return ("approval scope must name real files; drop the 'none' entries "
                "from --pages-touched.")
    analyses_targets = [d for d in real_destinations(home, args.pages_touched)
                        if is_analyses_path(d)]
    if route == "analysis-capture" or analyses_targets:
        if not args.path:
            target = analyses_targets[0] if analyses_targets else home
            return (f"{route} targeting {target} requires --path to the drafted "
                    "artifact so its word count is measured, not declared; any "
                    f"{ANALYSES_PREFIX} destination in the scope triggers this.")
        if measure_word_count(args.path) is None:
            return f"--path {args.path!r} is not a readable file."
    return None


def out_of_root_destinations(args: argparse.Namespace, home: str) -> list[str]:
    """Concrete declared destinations outside allowed durable roots or under raw/."""
    return [d for d in real_destinations(home, args.pages_touched) if not under_allowed_root(d)]


def capture_approval_record(args: argparse.Namespace, route: str, home: str, scope: list[str],
                            word_count: int, word_count_source: str) -> dict[str, object]:
    return {
        "record_type": "capture_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "approved_at": approved_at_now(),
        "artifact": args.artifact.strip(),
        "route": route,
        "phase": args.phase,
        "primary_home": home.strip(),
        "pages_touched": scope,
        "source_path": args.source_path.strip(),
        "synthesized_pages": args.synthesized_pages,
        "word_count": word_count,
        "word_count_source": word_count_source,
        "word_count_path": args.path.strip(),
        "domain_context": args.domain_context,
        "triggers": sorted(args.trigger),
    }


def synthesis_approval_record(args: argparse.Namespace, home: str, scope: list[str]) -> dict[str, object]:
    return {
        "record_type": "synthesis_approval",
        "schema_version": 1,
        "approval_status": "approved",
        "approved_at": approved_at_now(),
        "artifact": args.artifact.strip(),
        "drafts": args.drafts.strip(),
        "primary_home": home.strip(),
        "pages_touched": scope,
        # Fully derived: synthesis_guard has already required home in scope.
        "ledger_update_required": home.strip() == SYNTHESIS_DEFAULT_HOME,
    }


def write_approval_record(record: dict[str, object], ledger: str,
                          record_type: str) -> tuple[bool, Path, str]:
    return _write_approval_record(
        Path(ledger),
        record,
        record_type=record_type,
        schema_description=LEDGER_SCHEMA_DESCRIPTION,
    )


def print_capture_summary(args: argparse.Namespace, route: str, home: str, reason: str,
                          scope: list[str]) -> None:
    files = ", ".join(scope) if scope else (home if home else "none")
    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print(f"Machine mode: {route}")
    if route in ACTION_LABELS:
        print(f"Proposed action: {ACTION_LABELS[route]}")
    print(f"Primary home: {home}")
    print(f"Reason: {reason}")
    print(f"Pages touched: {files}")


def print_synthesis_summary(args: argparse.Namespace, home: str, scope: list[str]) -> None:
    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print("Machine mode: synthesis")
    print("Proposed action: Approve synthesis content and update the synthesis ledger.")
    print(f"Primary home: {home}")
    print(f"Drafts for review: {args.drafts}")
    print(f"Files the agent may edit after approval: {', '.join(scope)}")


def print_capture_approval_request(args: argparse.Namespace, route: str, home: str,
                                   scope: list[str]) -> None:
    action = ACTION_LABELS[route]
    files = ", ".join(scope)
    print()
    print("APPROVAL REQUIRED")
    print("No files have been changed yet.")
    print()
    print("What you are approving:")
    print(f"- Durable action: {action}")
    print(f"- Artifact: {args.artifact}")
    print(f"- Primary destination: {home}")
    print(f"- Files the agent may edit: {files}")
    print()
    print("Approve only if these are correct:")
    print("- This artifact should be saved to the wiki, not left in chat.")
    print("- The primary destination is the right durable home.")
    print("- The file list is the full intended edit scope.")
    print()
    print('Reply with plain-language approval, such as "approve" or "yes", or say what should change.')
    print()
    print("Agents: re-run with --approved only after the user clearly approves the displayed action, destination, and file scope.")


def print_synthesis_approval_request() -> None:
    print()
    print("APPROVAL REQUIRED")
    print("Do not update wiki/synthesis.md, flip draft confidence/status, or log a synthesis promotion yet.")
    print()
    print("Approve only if these are correct:")
    print("- The reviewed synthesis content is right.")
    print("- The primary ledger/durable home is right.")
    print("- The file list is the full intended approval edit scope.")
    print()
    print('Reply with plain-language approval, such as "approve" or "yes", or say what should change.')
    print()
    print("Agents: re-run with --approved only after the user clearly approves the displayed draft and file scope.")


def print_capture_approval_confirmed(args: argparse.Namespace, route: str, home: str,
                                     scope: list[str]) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved action: {ACTION_LABELS[route]}")
    print(f"Approved primary destination: {home}")
    print(f"Approved file scope: {', '.join(scope)}")
    print(f"Approval record: {args.approval_ledger}")
    print("Proceed only within this approved scope.")


def print_synthesis_approval_confirmed(args: argparse.Namespace, home: str, scope: list[str]) -> None:
    print()
    print("APPROVAL CONFIRMED")
    print(f"Approved synthesis: {args.artifact}")
    print(f"Approved primary home: {home}")
    print(f"Approved file scope: {', '.join(scope)}")
    print(f"Approval record: {args.approval_ledger}")
    print("Proceed only within this approved scope.")


def blocked(reason: str, args: argparse.Namespace) -> int:
    """Print the BLOCKED banner with the reason and return exit code 3."""
    print("CAPTURE GATE: BLOCKED")
    print(f"Artifact: {args.artifact}")
    print(f"Reason: {reason}")
    return 3


def synthesis_guard(args: argparse.Namespace, home: str, scope: list[str]) -> str | None:
    if not args.artifact.strip():
        return ("--artifact must be a non-empty description; the gate will not "
                "write an approval record its own validator would reject.")
    if not args.drafts.strip():
        return "Synthesis approval requires --drafts so the user can review what changed."
    if not args.pages_touched.strip():
        return "Synthesis approval requires --pages-touched so the editable scope is explicit."

    checked_scope = scope + [home]
    placeholders = [p for p in checked_scope if p and is_placeholder(p)]
    if placeholders:
        return f"approval scope must name concrete paths, not placeholders: {placeholders}"
    if home not in scope:
        return f"primary home {home} must be included in --pages-touched."
    outside = [p for p in checked_scope if p and not under_allowed_root(posixpath.normpath(p))]
    if outside:
        return f"approval scope paths must be under an allowed root: {outside}"
    # Synthesis flips status on existing, already-reviewed analyses pages. A
    # NEW analysis has a draft to measure, so it must go through the measured
    # analysis-capture route instead of this unmeasured branch.
    missing_analyses = [p for p in checked_scope
                        if p and is_analyses_path(p) and not Path(p).is_file()]
    if missing_analyses:
        return (f"synthesis may only touch existing {ANALYSES_PREFIX} pages; file a "
                f"new analysis through analysis-capture with a measured draft: "
                f"missing {missing_analyses}")
    return None


def run_synthesis(args: argparse.Namespace) -> int:
    home = args.primary_home.strip() or SYNTHESIS_DEFAULT_HOME
    if home and not is_placeholder(home):
        home = normalize_path(home)
    scope = list(dict.fromkeys(normalize_path(p) for p in split_scope(args.pages_touched)))

    reason = synthesis_guard(args, home, scope)
    if reason:
        return blocked(reason, args)

    print_synthesis_summary(args, home, scope)
    if args.approved:
        record = synthesis_approval_record(args, home, scope)
        problems = validate_approval(record)
        if problems:
            return blocked("refusing to write an approval record its own validator "
                           "rejects: " + "; ".join(problems), args)
        print("Approval: confirmed for this exact synthesis content and file scope.")
        wrote, ledger_path, label = write_approval_record(
            record, args.approval_ledger, "synthesis_approval"
        )
        if wrote:
            print(f"Structured approval record: appended approval for {label} to {ledger_path}")
        else:
            print(f"Structured approval record: already present for {label} in {ledger_path}")
        print_synthesis_approval_confirmed(args, home, scope)
        return 0

    print_synthesis_approval_request()
    return 2


def run_free_phase(args: argparse.Namespace) -> int:
    """Phases other than accepted never require this gate; the routed prose
    workflows own that judgment. Two deterministic guards still apply so a
    mistaken invocation cannot legitimize a bad destination."""
    home = args.primary_home.strip()
    if home and home != "none" and not is_placeholder(home):
        home = normalize_path(home)

    if any(is_analyses_path(d) for d in real_destinations(home, args.pages_touched)):
        return blocked(f"phase '{args.phase}' may not write to {ANALYSES_PREFIX}; "
                       "an analysis must go through analysis-capture or promotion-audit.",
                       args)

    outside = out_of_root_destinations(args, home)
    if outside:
        return blocked("destinations must be under an allowed root "
                       f"({', '.join(ALLOWED_ROOTS)}) and never raw/: offending {outside}",
                       args)

    print("CAPTURE GATE")
    print(f"Artifact: {args.artifact}")
    print(f"Machine mode: non-approval (phase {args.phase})")
    print("Approval: not required; only --phase accepted can cross an approval "
          "boundary. Route judgment lives in the routed workflows; do not edit "
          "files a drafting conversation has not asked for.")
    return 0


def run_capture(args: argparse.Namespace) -> int:
    if not args.phase:
        return blocked("--phase is required when --kind=capture.", args)

    if args.phase != "accepted":
        return run_free_phase(args)

    # Measure the word count from the real draft when a path is given, so the
    # decision rests on a fact rather than a declared number. An unreadable
    # --path blocks here with the precise diagnosis; letting it fall through
    # would misclassify the run as chat-only and report the wrong problem.
    word_count = 0
    word_count_source = "unmeasured"
    if args.path:
        measured = measure_word_count(args.path)
        if measured is None:
            return blocked(f"--path {args.path!r} is not a readable file.", args)
        word_count = measured
        word_count_source = "measured"

    if args.synthesized_pages < 0:
        return blocked("--synthesized-pages must be a non-negative count of "
                       "distinct wiki pages synthesized.", args)

    route, home, reason = classify_accepted(args, word_count)
    # Normalize a concrete home once so every downstream check and stored record
    # see the same resolved path.
    if home and home != "none" and not is_placeholder(home):
        home = normalize_path(home)

    # These guards check the DECLARED inputs, not the route-derived home: a
    # chat-only classification discards --primary-home, and a discarded
    # analyses or out-of-root declaration must still block rather than exit 0.
    declared_home = args.primary_home.strip()
    if route not in APPROVAL_ROUTES:
        analyses_declared = [d for d in real_destinations(declared_home, args.pages_touched)
                             if is_analyses_path(d)]
        if analyses_declared:
            hint = ""
            if not args.path:
                hint = (" If this is a drafted analysis, re-run with --path to the "
                        "draft so its word count is measured, not declared.")
            return blocked(f"route '{route}' may not write to {ANALYSES_PREFIX}; "
                           "an analysis must go through analysis-capture or "
                           f"promotion-audit.{hint}", args)

    outside = out_of_root_destinations(args, declared_home)
    if outside:
        return blocked("destinations must be under an allowed root "
                       f"({', '.join(ALLOWED_ROOTS)}) and never raw/: offending {outside}",
                       args)

    approval_required = route in APPROVAL_ROUTES

    if approval_required:
        block = approval_guard(args, route, home)
        if block:
            return blocked(block, args)

    scope = scope_with_home(home, args.pages_touched)
    print_capture_summary(args, route, home, reason, scope)

    if route == "chat-only":
        print("Approval: not required; do not edit files.")
        return 0

    if args.approved:
        record = capture_approval_record(args, route, home, scope,
                                         word_count, word_count_source)
        problems = validate_approval(record)
        if problems:
            return blocked("refusing to write an approval record its own validator "
                           "rejects: " + "; ".join(problems), args)
        print("Approval: confirmed for this exact route.")
        wrote, ledger_path, label = write_approval_record(
            record, args.approval_ledger, "capture_approval"
        )
        if wrote:
            print(f"Structured approval record: appended approval for {label} to {ledger_path}")
        else:
            print(f"Structured approval record: already present for {label} in {ledger_path}")
        print_capture_approval_confirmed(args, route, home, scope)
        return 0

    print_capture_approval_request(args, route, home, scope)
    return 2


def main() -> int:
    try:
        args = parser().parse_args()
    except SystemExit as exc:
        # argparse exits 2 on usage errors, which would collide with this
        # gate's "approval required" code; remap so exit 2 keeps one meaning.
        if exc.code == 2:
            return 3
        return exc.code if isinstance(exc.code, int) else 3
    if args.kind == "synthesis":
        return run_synthesis(args)
    return run_capture(args)


if __name__ == "__main__":
    sys.exit(main())
