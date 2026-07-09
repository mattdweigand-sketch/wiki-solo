# Wiki Research Deep-Research Overlay

Use this workflow only after `python3 scripts/wiki_research.py preflight --question "<request>"` accepts the request. Use `python3 scripts/wiki_research.py manifest` to inspect the runtime-owned trigger boundary, lane contract, claim-ledger vocabulary, and waiver vocabulary.

This is a high-rigor overlay on the normal research workflow for questions where accuracy is non-negotiable: coverage, claim-level citations, raw-source confirmation, contradiction checking, and a review packet. It is not a new workspace and it is not a mandatory multi-agent system. Default to one orchestrator running the lanes serially.

## Load / Skip

- **Load:** `workflows/research/CONTEXT.md`, `wiki/index.md`, `wiki/primer.md`, then only the specific pages the question touches. When filing an analysis, also load `wiki/SCHEMA.md` and follow `workflows/research/CONTEXT.md#analysis-capture` exactly.
- **Skip:** unrelated entity folders, broad folder reads, durable writes before the approval gate, and child agents or parallel threads unless the split policy below is met. Raw sources are read only through the default raw verification boundary below.

## Invocation Boundary

Run `python3 scripts/wiki_research.py preflight --question "<request>"` before applying this overlay. If preflight rejects the request, use `workflows/research/CONTEXT.md`.

Do not infer this workflow from ordinary broad questions, high-stakes wording, "be thorough", "use agents", or standalone research or swarm language. The runtime owns the accepted trigger phrases and rejects the retired wiki-swarm triggers with a rename tombstone.

## Readiness Verdicts

Start with one verdict:

- `NORMAL RESEARCH` - the request invoked wiki-research, but the question is narrow, standard-stakes, and the normal research workflow is sufficient.
- `DEEP RESEARCH` - the question needs the lane checks, the claim ledger, and default raw verification; one orchestrator runs the lanes serially.
- `SPLIT LANES` - the user explicitly asked for parallel agents or the review burden justifies a split.
- `STOP` - the question, source of truth, permission boundary, or durable-write intent is unclear enough that proceeding would produce misleading work.

High stakes never takes the `NORMAL RESEARCH` verdict: when the question, scope, consulted pages, or answer sit in the runtime-owned high-stakes categories, a narrow question means a short claim ledger, not relaxed guarantees. The runtime validator enforces the incompatibility.

For `NORMAL RESEARCH`, say why and continue through this overlay's packet contract at standard stakes. For `STOP`, ask the smallest concrete question needed to proceed.

## Split Policy

Prefer one orchestrator. Split into child threads or parallel agents only when at least one condition is true:

- The user explicitly asks for parallel agents or separate lanes.
- The page set spans several independent domains and serial review would likely miss contradictions.
- The answer requires independent reviewer pressure, not just faster searching.

Split lanes are read-only. A child lane may return page lists, ledger claims, contradictions, confidence notes, and open questions. It must not edit files, run durable writes, send external output, or decide final synthesis.

## Required Lanes

Run every lane in `python3 scripts/wiki_research.py manifest`, even when one orchestrator performs them serially. Report the lane outputs under `Lane results`.

Two lanes carry judgment the validator cannot see, and their obligations are part of this workflow, not optional polish. The citation-auditor confirms that each citation supports its claim as written, that each factual sentence in the answer maps to a referenced claim, and that each high-stakes wiki-backed claim cites the page that owns the fact rather than a page that merely mentions it. The reviewer additionally checks that no raw-only content is smuggled into the answer as paraphrase. A claim or answer unit that fails these audits is fixed, downgraded, or moved to `What not to say` before the packet finalizes.

## Claim Ledger

Every material factual claim lives in the `Claim ledger` as a single line carrying its citations, a short verbatim quote from the cited page's evidentiary body, and a verification status. The statuses, field keys, quote limit, waiver vocabulary, high-stakes categories, wiki-native type allowlist, and answer-eligibility registry are runtime-owned; read them from `python3 scripts/wiki_research.py manifest` rather than from memory, and do not re-enumerate them here or in packets beyond what the packet grammar needs.

The answer is built from the ledger: every answer unit references ledger claim IDs, so nothing reaches the answer without passing through the ledger's citation, quote, and status rules. Quotes come from wiki pages only, never from raw files.

## Default Raw Verification

Raw confirmation is the default. The planner does not decide whether raw verification is warranted; it decides which provenance-closure files to check, or which runtime-owned waiver applies, and says so either way. Check raw files named in the provenance closure of consulted pages using reproducible text extraction, naming each file and method under `Raw sources checked` and every gap, unreadable region, or unavailable tool under `Raw extraction limits`.

For questions in the runtime-owned high-stakes categories, treat wiki-only support as provisional: a claim the answer relies on is not settled until it is raw-verified, or until its cited pages are confirmed provenance-free by closure (not by glance) and wiki-native or owner-registered. The runtime validator verifies the waiver against the actual closure and fails dangling provenance references closed.

A raw-only fact is an ingest gap. Report it under `Raw-only findings` as a minimal paraphrase with a re-ingest or source-page-update recommendation, never as answer support, and never in a packet that files a durable write. Ingest is the only route by which a raw-only finding becomes durable wiki knowledge, and raw-only claim IDs never appear in the `Answer`.

Extraction artifacts, including screenshots, go to `tmp/` only. Never quote more raw content than the mediating source page already carries; raw files hold private material and packet text can flow into committed analyses. Cite raw files by path and locator, never by fresh excerpt.

## Scope Retention

For any wiki-research question, preserve the runtime-owned scope-retention dimensions exposed by `python3 scripts/wiki_research.py manifest`. Do not narrow the answer so far that a consulted page's relevant warning disappears.

Page-scout should tag why each consulted page matters using the runtime-owned page relevance tags. Evidence-extractor should pull both positive facts and runtime-owned scope-retention dimensions from those pages into the ledger. Synthesizer should carry retained caveats into the runtime-owned output targets as appropriate. Reviewer should check that no material caveat from a consulted page was silently dropped; if a caveat is intentionally excluded, say why in `Lane results` or `What not to say`.

Raw verification must not narrow the compiled-page scope. Raw confirmation verifies compiled claims and exposes ingest gaps, but it does not replace the condition, status, contradiction, and open-follow-up review across consulted wiki pages.

## Output Contract

Return a `WIKI-RESEARCH PACKET` with the sections listed in `python3 scripts/wiki_research.py manifest`. Keep `Checks actually run` factual; do not list proposed checks as if they were completed.

`validate-packet` enforces the checkable part of this contract: packet shape, verdict and stakes rules, `[[index]]` and `[[primer]]` consulted, consulted pages exist in the corpus, the claim-ledger grammar with per-claim citations and quote anchoring, raw-file legality through the provenance closure with fully consulted resolution chains, coverage arithmetic, answer grammar and claim-ID anchoring, the raw-only answer ban, and the high-stakes answer-eligibility rules.

For current-state, property, stale-status, or contradiction-sensitive packets, consult `[[contradictions]]` and cite it in `Contradictions or stale areas`. Do not use bare dismissal language such as "none found" or "not applicable"; if the register has no material conflict for the answer, say that as a relevance-qualified note after checking `[[contradictions]]`.

If `Durable-write status` claims an analysis was filed, the packet must name the normal analysis-capture route plus proof markers: the approval record, capture-run validation, and the primary destination. Chat-only packets should say that no durable write was requested.

## Durable Write Boundary

Default output is chat-only. If the answer qualifies for analysis filing, follow `workflows/research/CONTEXT.md#analysis-capture` exactly. Do not duplicate or reinterpret that procedure here.

Append to `wiki/log.md` only when an analysis was filed or the user explicitly asked for a durable query record, matching the normal research workflow.

Before final output, save or stage the packet text and run `python3 scripts/wiki_research.py validate-packet --packet <path>`. Fix any packet-shape or policy failure before responding.

## Completion Check

Before finishing, verify:

- Runtime preflight accepted the request.
- The verdict matches the actual route taken, and high stakes did not take `NORMAL RESEARCH`.
- `wiki/index.md` and `wiki/primer.md` were used before page-specific reading.
- Every material factual claim lives in the ledger with citations and a quote, and every answer unit references ledger claim IDs.
- Raw verification was performed against closure-named files or waived with a runtime-owned waiver, stated either way.
- The citation-auditor and reviewer judgment checks ran and their outcomes are reported under `Lane results`.
- Contradictions and stale areas were surfaced rather than smoothed over.
- Scope retention was checked against the runtime-owned dimensions and any material caveat from consulted pages was included or explicitly excluded.
- Durable writes, if any, went through the normal research approval gate.
