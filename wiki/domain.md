---
title: Domain Config
type: domain
created: 2026-05-17
updated: 2026-05-17
status: unconfigured
org: <Organization name>
domain: <One-line domain summary, e.g. "developer tools for payments">
entity_types_active:
  - source
  - product
  - feature
  - persona
  - customer
  - competitor
  - concept
  - initiative
  - decision
  - metric
  - person
  - analysis
  - style
entity_types_custom: []
raw_taxonomy: []
example_queries: []
---

# Domain Config

Single source of truth for **who this wiki is about**. Framework files defer to this page instead of hardcoding an organization name.

## Status

When `status: unconfigured` (the default for a fresh clone), this wiki is a blank template. An agent in a new session should notice this flag and route to [`SETUP.md`](../SETUP.md), which walks the user through an interview to fill this file out.

When `status: configured`, the wiki is ready to ingest sources and answer questions.

## Fields

| Field | Meaning |
|---|---|
| `org` | The organization (company, team, project) this wiki is about |
| `domain` | One-line description of the subject area |
| `entity_types_active` | Subset of the 13 entity types from [`SCHEMA.md`](SCHEMA.md) that this wiki uses. Drop any that don't fit your domain. |
| `entity_types_custom` | Any new entity types this domain needs that aren't in the default 13 |
| `raw_taxonomy` | Subfolder names that should exist under `raw/` for source-document organization |
| `example_queries` | 3–5 questions the wiki should answer well — useful for sanity-checking coverage |

## After configuration

The agent updates this file's `status:` to `configured`, replaces `<Organization>` placeholders in the framework files (see [`SETUP.md`](../SETUP.md) for the exact list), and appends a log entry to [`log.md`](log.md).
