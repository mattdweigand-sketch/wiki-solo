---
title: Primer for Downstream Agents
type: style
created: 2026-05-17
updated: 2026-05-17
---

# Primer

Routing into the wiki by question type. When an agent gets a question, this page maps the question shape to the right entry points.

| Question type | Start with |
|---|---|
| "What is <entity>?" | `wiki/<entity-type>/<slug>.md` directly, or [`index.md`](index.md) if the slug is unknown |
| "How does X compare to Y?" | Both entity pages; then check [`analyses/`](analyses/) for an existing comparison |
| "What's our position on X?" | [`decisions/`](decisions/), then [`initiatives/`](initiatives/) |
| "Who uses X?" | [`customers/`](customers/) and [`personas/`](personas/) |
| "What does <term> mean here?" | [`glossary.md`](glossary.md) |

Add domain-specific routing rows below as the wiki grows.
