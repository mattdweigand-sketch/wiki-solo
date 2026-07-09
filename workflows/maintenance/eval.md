# Wiki Eval

Run this workflow when the task is to verify the wiki system itself: scripts, gates, ledgers, backlink rebuilds, export behavior, stale-text sweep proof, wrapper parity, schema-doc parity, wiki-swarm runtime guardrails, and the deterministic Tier-1 gate. The `SUITES` registry in `scripts/wiki_eval.py` is the authoritative list of what runs.

This is different from `/wiki-lint`: lint checks wiki content; eval checks the tools that check and protect the wiki.

## Wrapper Surface Contract

The live convenience surfaces are `.claude/commands/wiki-*.md` and `.codex/skills/wiki-*/SKILL.md`. They must cover the same eight shortcuts; `EXPECTED_SKILLS` in `scripts/check_wrapper_parity.py` is the authoritative name registry (the human-facing list lives in `AGENTS.md` and the README command table).

Canonical procedure belongs in `workflows/`. A wrapper is only a thin pointer: canonical routing paths plus at most one `scripts/*.py` command hint. It must not carry a numbered-step list or route-classification procedure. Deleting wrapper folders does not remove the underlying wiki workflow; it only removes that agent surface's shortcut.

`python3 scripts/check_wrapper_parity.py` enforces the checkable part (the `wrapper-parity` suite runs it via `scripts/wiki_eval_wrappers.py`, which also seeds negative fixtures so the checker itself cannot go vacuous):

- both wrapper surfaces cover exactly the expected `wiki-*` names
- no wrapper carries more than one `scripts/*.py` reference
- no wrapper carries a numbered-step list
- every `workflows/*.md` path a wrapper names exists in the tree
- every shortcut with a single canonical task workflow names that route; `EXPECTED_WORKFLOW_REFS` in `scripts/check_wrapper_parity.py` is the authoritative route registry (`wiki-swarm` is deliberately absent because the swarm suite separately pins both swarm wrappers to route through the root)

It deliberately does not limit how many `workflows/` paths a wrapper names, because naming a workspace `CONTEXT.md` plus the routed task file is the legitimate thin-pointer pattern. It also cannot catch content drift between a wrapper and its twin (one surface carrying a guidance sentence the other lacks); keep wrapper bodies pointer-only so there is nothing to drift.

Historical note: identical global installs under `~/.codex/skills/wiki-*` once created duplicate repo-local and global slash-command entries. That one-time cleanup is complete and its removal machinery was retired 2026-07-01; if duplicate slash entries ever reappear, delete the global copies by hand.

## Policy-Constant Placement Contract

A chosen-policy value (a vocabulary, threshold, enum, or registry) that a script enforces and a workflow names may live as a named constant in that script rather than a governed JSON file. Default placement is the code constant while all of these hold: it is small enough to review in a diff, exactly one script owns it, the owning workflow file names it, and eval or Tier-1 coverage exercises it.

Migrate it to a governed `scripts/*.json` file when any one of these fires:

1. Routine maintenance extends the value, so agents edit it as data.
2. A second script needs the same value.
3. Governed data such as `scripts/lint-adjudications.json` must validate against it.
4. Growth makes review, ownership, or extension materially better as JSON than as a named constant.

A migration keeps the shape of the existing registries: a `description` field naming the purpose and owning workflow, Tier-1 validation of the config shape, existing eval coverage preserved against the new source, and doc pointers updated. When a vocabulary migrates to JSON, docs point at the file rather than re-enumerating it; deliberate duplication for authoring convenience requires a parity marker.

## Schema Doc Parity Contract

The frontmatter vocabularies (entity folders, entity types, `confidence`, `source_type`, `authority_kind`, `authority_freshness`, and related-page labels) are canonical as constants in `scripts/lint.py`. The enumerations in `wiki/SCHEMA.md`, `REFERENCES.md`, and `AGENTS.md` are documentation of those constants, each marked with a `<!-- parity:enum key=... -->` comment. When changing a vocabulary, update the constant and every marked doc site in the same change.

`python3 scripts/check_schema_doc_parity.py` enforces set equality per marker. The `schema-docs` suite runs it via `scripts/wiki_eval_schema_docs.py`, which also seeds negative fixtures so the checker cannot go vacuous. It deliberately does not check prose meanings, table right-hand columns, or ordering: those are editorial.

A new doc enumeration of a canonical vocabulary must either defer to the source by name without re-enumerating, or carry a parity marker. An unmarked enumeration is a review finding, not an allowed state. A parity marker outside a registered doc site is also a failure; register the site in `scripts/check_schema_doc_parity.py` when extending coverage.

## Load / Skip

- **Load:** `scripts/wiki_eval.py`; `scripts/check_wrapper_parity.py` when the task concerns wrapper parity; `scripts/check_schema_doc_parity.py` when the task concerns schema docs; `scripts/wiki_swarm.py` when the task concerns wiki-swarm guardrails; any failing suite output if a run fails.
- **Skip:** wiki entity pages, raw sources, unrelated workflow files, and Tier-2/Tier-3 content review.

## Steps

1. From the repo root, run:

   ```bash
   python3 scripts/wiki_eval.py
   ```

2. If it fails, inspect only the failing suite and make the narrowest fix.
3. Re-run `python3 scripts/wiki_eval.py` until it passes or a blocker is clear.
4. Run `git diff --check` before finishing when files changed.

## Failure -> Eval Escalation

When a real tool or workflow failure repeats, has high blast radius, or could silently regress, add the smallest eval fixture that would have caught it. Do not add evals for one-off judgment calls or prose taste. The eval must fail before the fix and pass after the fix; otherwise leave it as a known limitation rather than adding hollow coverage.

## Report

Report whether `wiki_eval.py` passed, which suite failed if any, what was fixed, and whether `git diff --check` passed when relevant.
