---
id: B.1
title: Schema redesign — header fields become per-item columns
status: planned
branch: feature/B-1-schema
worktree: ../raptor-worktrees/feature/B-1-schema
target: develop
---

# Sprint B.1 — Schema redesign: header fields become per-item columns

Raptor is three scripts run by skills: `extract.py`, `load_sqlite.py`,
`render.py`. This sprint changes the schema they share. Nothing else.

## Goal

- In Markdown, Status, Created, Last Updated and Version can only be edited at
  the file level. In the database they are columns on every item, seeded from
  the file header, so QA can query and change them per REQ, NFR, ADR, design,
  and test plan.

## Exact Targets

- `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `scripts/extract.py`, `scripts/load_sqlite.py`, `scripts/render.py`
- `templates/*.md.j2` (header lines only)
- `tests/test_scripts.py`, `tests/fixtures/`

## Deliverables

- `Record` gains top-level `created`, `last_updated`, `version` (strings;
  `version` may be null). They move out of `document_metadata`, which keeps
  `owner`, `id_range`, `range_description`. `type` becomes
  `REQ | NFR | ADR | DESIGN | TEST`.
- `artifacts` table gains `created`, `last_updated`, `version` columns;
  `load_sqlite.py` writes them and loads the index's test plans as `TEST` rows
  (one per plan, fields from the plan's `metadata`).
- `extract.py`: reads `**Version:**` from the header; stamps the four fields on
  every item of the file; emits one `DESIGN` item per file under a `design/`
  directory (id from the file stem upper-cased, title from the H1, body the
  whole document). Parsing fix: a file's first id heading is the document
  title, not an item, when the file has no H1 and the same id recurs; a later
  heading that repeats an id already seen in the file is folded into that
  item as a subsection; an id seen in two files is reported as one diagnostic
  naming both files.
- Templates print `**Status:**`, `**Created:**`, `**Last Updated:**`,
  `**Version:**` under each item's heading, from the item's own fields.

## Ceilings

- `extract.py` 2,050 lines; `load_sqlite.py` 60; `render.py` 120;
  `record.py` 120; each template 60. No new files except fixtures.

## Acceptance

- `python -m pytest -q tests` passes; a fixture with two files, one design
  file, one test plan, and one repeated id covers every deliverable above.
- Consumer run: every item row has non-null `created` and `last_updated`;
  `version` non-null wherever the file header has one; zero rows for the
  duplicate title headings; DESIGN and TEST rows present; validation errors 0.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
