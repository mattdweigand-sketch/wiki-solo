# Wiki Swarm Research Overlay

Use this workflow only after `python3 scripts/wiki_swarm.py preflight --question "<request>"` accepts the request. Use `python3 scripts/wiki_swarm.py manifest` to inspect the runtime-owned trigger boundary and lane contract.

This is a high-rigor overlay on the normal research workflow for broad questions where coverage, contradiction checking, and a review packet matter. It is not a new workspace and it is not a mandatory multi-agent system. Default to one orchestrator running the lanes serially.

## Load / Skip

- **Load:** `workflows/research/CONTEXT.md`, `wiki/index.md`, `wiki/primer.md`, then only the specific pages the question touches. When filing an analysis, also load `wiki/SCHEMA.md` and follow `workflows/research/CONTEXT.md#analysis-capture` exactly.
- **Skip:** raw sources, unrelated entity folders, broad folder reads, durable writes before the approval gate, and child agents or parallel threads unless the split policy below is met.

## Invocation Boundary

Run `python3 scripts/wiki_swarm.py preflight --question "<request>"` before applying this overlay. If preflight rejects the request, use `workflows/research/CONTEXT.md`.

Do not infer this workflow from ordinary broad questions, high-stakes wording, "be thorough", "use agents", or standalone swarm language. The runtime owns the accepted trigger phrases.

## Readiness Verdicts

Start with one verdict:

- `NORMAL RESEARCH` - the request invoked wiki-swarm, but the question is narrow enough that the normal research workflow is sufficient.
- `SINGLE-AGENT SWARM` - the question is broad enough to need the lane checks, but one orchestrator can run them serially.
- `SPLIT LANES` - the user explicitly asked for parallel agents or the review burden justifies a split.
- `STOP` - the question, source of truth, permission boundary, or durable-write intent is unclear enough that proceeding would produce misleading work.

For `NORMAL RESEARCH`, say why and continue through `workflows/research/CONTEXT.md`. For `STOP`, ask the smallest concrete question needed to proceed.

## Split Policy

Prefer one orchestrator. Split into child threads or parallel agents only when at least one condition is true:

- The user explicitly asks for parallel agents or separate lanes.
- The page set spans several independent domains and serial review would likely miss contradictions.
- The answer requires independent reviewer pressure, not just faster searching.

Split lanes are read-only. A child lane may return page lists, cited facts, contradictions, confidence notes, and open questions. It must not edit files, run durable writes, send external output, or decide final synthesis.

## Required Lanes

Run every lane in `python3 scripts/wiki_swarm.py manifest`, even when one orchestrator performs them serially. Report the lane outputs under `Lane results`.

## Output Contract

Return a `WIKI-SWARM PACKET` with these sections:

```text
WIKI-SWARM PACKET
Verdict: NORMAL RESEARCH | SINGLE-AGENT SWARM | SPLIT LANES | STOP
Question:
Source scope:
Pages consulted:
Lane results:
Supported facts:
Inferences:
Contradictions or stale areas:
Answer:
What not to say:
Checks actually run:
Durable-write status:
Promotion audit:
```

Keep `Checks actually run` factual. Do not list proposed checks as if they were completed.

`validate-packet` enforces the checkable part of this contract. For any non-`STOP` packet, include `[[index]]` and `[[primer]]` in `Pages consulted`, cite at least one consulted wiki page in both `Supported facts` and `Answer`, and list `preflight` under `Checks actually run`.

For current-state, status, maintenance, or contradiction-sensitive packets, consult `[[contradictions]]` and cite it in `Contradictions or stale areas`. Do not use bare dismissal language such as "none found" or "not applicable"; if the register has no material conflict for the answer, say that as a relevance-qualified note after checking `[[contradictions]]`.

If `Durable-write status` claims an analysis was filed, the packet must name the normal analysis-capture route plus proof markers: the approval record, `validate_capture_runs.py`, and the primary destination. Chat-only packets should say that no durable write was requested.

## Durable Write Boundary

Default output is chat-only. If the answer qualifies for analysis filing, follow `workflows/research/CONTEXT.md#analysis-capture` exactly. Do not duplicate or reinterpret that procedure here.

Append to `wiki/log.md` only when an analysis was filed or the user explicitly asked for a durable query record, matching the normal research workflow.

Before final output, save or stage the packet text and run `python3 scripts/wiki_swarm.py validate-packet --packet <path>`. Fix any packet-shape or policy failure before responding.

## Completion Check

Before finishing, verify:

- Runtime preflight accepted the request.
- The verdict matches the actual route taken.
- `wiki/index.md` and `wiki/primer.md` were used before page-specific reading.
- Every material factual claim in the answer has a `[[page]]` citation or is labeled as inference.
- Contradictions and stale areas were surfaced rather than smoothed over.
- Durable writes, if any, went through the normal research approval gate.
