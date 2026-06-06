# Maintenance

## What This Workspace Is

Wiki hygiene. The substrate gets messy as it grows: contradictions appear, claims go stale, terms drift, sources get queued but never ingested. This workspace is where periodic upkeep happens — and where decisions get captured before they become folklore.

**Inputs:** [`../../../wiki/`](../../../wiki/), this workspace's own scratchpads ([`contradictions.md`](contradictions.md), [`sourcing-queue.md`](sourcing-queue.md), [`design-notes.md`](design-notes.md)).
**Outputs:** Updated wiki pages, updated scratchpads, new decision pages in [`../../../wiki/decisions/`](../../../wiki/decisions/), entries in [`../../../wiki/log.md`](../../../wiki/log.md).

---

## What to Load

| Task | Load These | Skip These |
|---|---|---|
| Lint the wiki | [`docs/lint-criteria.md`](docs/lint-criteria.md), [`contradictions.md`](contradictions.md), [`../../../wiki/index.md`](../../../wiki/index.md), then pages on demand | ingest/, research/ docs |
| Capture a decision | [`docs/decision-capture.md`](docs/decision-capture.md), the affected entity pages | docs/lint-criteria.md, contradictions.md (unless the decision resolves one) |
| Refresh sourcing queue | [`sourcing-queue.md`](sourcing-queue.md), recent entries in [`../../../wiki/log.md`](../../../wiki/log.md) | docs/decision-capture.md, docs/lint-criteria.md |
| Resolve a contradiction | [`contradictions.md`](contradictions.md), the two (or more) pages in conflict, their cited sources | docs/lint-criteria.md (you're surgical here, not sweeping) |

---

## Folder Structure

```
maintenance/
├── CONTEXT.md                ← You are here
├── contradictions.md         ← Open + closed contradictions across the wiki
├── sourcing-queue.md         ← Prioritized list of gaps and the artifacts that would fill them
├── design-notes.md           ← Meta: how the wiki itself is evolving
└── docs/
    ├── lint-criteria.md      ← What "lint" looks for
    └── decision-capture.md   ← How to record a decision (page format, cross-linking)
```

Note: `contradictions.md`, `sourcing-queue.md`, and `design-notes.md` used to live in `wiki/` but are operational files about the wiki — not entity pages — so they live here now.

---

## Tasks

### Lint the wiki
The user says "lint" or "lint the wiki." See [`docs/lint-criteria.md`](docs/lint-criteria.md) for the full checklist (contradictions, stale claims, orphans, missing cross-refs, terminology drift, confidence upgrades). Process:

1. Read the wiki using `wiki/index.md` as the entry point. For deep lints, sample-read pages by category.
2. Report findings grouped by category. Don't propose 50 fixes at once — top 10–15.
3. Ask which to apply. Apply the approved ones.
4. Update [`contradictions.md`](contradictions.md): resolved → closed, new → opened.
5. Update [`sourcing-queue.md`](sourcing-queue.md) if gaps shifted.
6. Run `python3 .agents/scripts/rebuild_referenced_by.py` from the repo root.
7. Append a log entry:
   ```
   ## [YYYY-MM-DD] lint
   Issues found: ...
   Fixes applied: ...
   Contradictions opened/closed: ...
   ```

### Capture a decision
The user says "capture decision [topic]" or describes a decision in passing. See [`docs/decision-capture.md`](docs/decision-capture.md) for page format. Process:

1. Create `../../../wiki/decisions/<slug>.md` with full frontmatter and body.
2. Cross-link from affected entity pages back to the decision.
3. Append a log entry:
   ```
   ## [YYYY-MM-DD] decision | <decision summary>
   Page created: decisions/<slug>
   Affects: ...
   ```

Decisions are first-class because they are exactly what makes this a "company context layer" rather than indexed documentation. Capture early and liberally.

### Refresh sourcing queue
The user says "refresh sourcing queue" — or it should be triggered after any ingest that closes or opens a gap. Process:

1. Read [`sourcing-queue.md`](sourcing-queue.md).
2. Re-prioritize based on what the latest ingests revealed.
3. For each priority gap (customers, competitors, decisions, metrics, initiatives, people), name the source artifact most likely to fill it (CRM export, win/loss interview, board deck, KPI dashboard, etc.).
4. Append a log entry summarizing changes to the queue.

### Resolve a contradiction
The user says "resolve [contradiction]" or picks one from [`contradictions.md`](contradictions.md). Process:

1. Read the entry, the conflicting pages, and their cited sources.
2. Determine: is one source authoritative? Are the sources describing different time windows? Is it actually a definition mismatch (terminology drift)?
3. Update the affected pages to reflect the resolution. If the contradiction is genuine and unresolved (we don't know which is right), keep `confidence: contested` but document the disagreement explicitly.
4. Mark the entry in [`contradictions.md`](contradictions.md) as `resolved` with a brief note on how.
5. Log it.

---

## Cadence (Suggested)

The wiki doesn't enforce cadence — these are just sane defaults:

- **Weekly:** Refresh sourcing queue. Quick contradiction sweep (any new ones flagged this week?).
- **Monthly:** Full lint pass.
- **As-needed:** Capture decisions in real time. Resolve specific contradictions when they block work.

---

## What NOT to Do

- **Don't resolve contradictions silently.** Every resolution leaves a trail in `contradictions.md` (status: closed, with reasoning) and ideally a `Disagreement` section in the affected page if it stays `contested`.
- **Don't bulk-rewrite pages during lint.** Lint reports issues; user approves; agent applies surgically. Maintenance is not re-extraction.
- **Don't add to `sourcing-queue.md` without a specific artifact in mind.** "We need more on Allvue" is not actionable. "We need the Q3 Allvue analyst report" is.
- **Don't load `ingest/workflows/` or `research/docs/`.** Different jobs — different context.
