---
id: B.1
title: Schema redesign — header fields become per-item columns
status: planned
branch: feature/B-1-schema
worktree: ../raptor-worktrees/feature/B-1-schema
target: develop
---

# Sprint B.1 — Schema redesign: header fields become per-item columns

Raptor's import is three scripts run by skills: `extract.py`, `load_sqlite.py`,
`render.py`. This sprint changes the schema they share so the SQLite fixture
holds every item and header field the corpus has (REQ-RAP-0002, REQ-RAP-0006).
Nothing else. Only fields that appear in the consumer Markdown become
columns; any other schema change is discussed with the operator first.

## Goal

- In Markdown, Status, Created, Last Updated and Version can only be edited at
  the file level. In the fixture they are columns on every row, seeded from
  the file header, so QA can query them per REQ, NFR, ADR, design document and
  test plan.

## Exact Targets

- `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `scripts/extract.py`, `scripts/load_sqlite.py`, `scripts/render.py`
- `templates/*.md.j2` (header lines only)
- `tests/test_scripts.py`, `tests/fixtures/`

## Deliverables

- `Record` gains top-level `created`, `last_updated`, `version` (strings;
  null when the file header lacks them). They
  move out of `document_metadata`, which keeps `owner`, `id_range`,
  `range_description`. `type` becomes `REQ | NFR | ADR | DESIGN | TEST`.
- `artifacts` table gains `created`, `last_updated`, `version` columns; `load_sqlite.py` writes them and loads the index's test plans as
  `TEST` rows (one per plan, fields from the plan's `metadata`).
- `extract.py`:
  - reads `**Version:**` from the header and stamps the four fields on every
    item of the file.
  - any ingested file that has no `## <ID>:` heading becomes one row: type
    from its route (`design_document` → `DESIGN`), id the file stem
    upper-cased, title the H1 or the first heading, body the whole document.
  - every id that appears more than once, in one file or across files, is
    reported as one diagnostic naming each file and line. No parsing rule
    works around it; the source is corrected (REQ-RAP-0006).
- Templates print `**Status:**`, `**Created:**`, `**Last Updated:**`,
  `**Version:**` under each item's heading, from the item's own fields.

## Ceilings

- `extract.py` 2,050 lines; `load_sqlite.py` 60; `render.py` 120;
  `record.py` 120; each template 60. No new files except fixtures.

## Acceptance

- `python -m pytest -q tests` passes; a fixture with two item files, one
  id-less design file, one test plan, and one repeated id covers every
  deliverable above.
- Consumer run: `created`, `last_updated` and `version` non-null wherever
  the file header has them; one `DESIGN` row per ingested id-less file; 27 `TEST` rows; the
  repeated-id diagnostics match the RAP-VAL-1 list until the source is
  corrected; validation errors 0.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
