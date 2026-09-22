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
Id-less documents are not allowed: Raptor never invents an id.

## Goal

- In Markdown, Status, Created, Last Updated and Version can only be edited at
  the file level. In the fixture they are columns on every row, seeded from
  the file header, so QA can query them per REQ, NFR, ADR, TEST and design
  document.

## Exact Targets

- `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`
- `scripts/extract.py`, `scripts/load_sqlite.py`, `scripts/render.py`
- `templates/*.md.j2` (header lines only)
- `tests/test_scripts.py`, `tests/fixtures/`

## Deliverables

- `Record` gains top-level `created`, `last_updated`, `version` (strings;
  null when the file header lacks them). They move out of
  `document_metadata`, which keeps `owner`, `id_range`, `range_description`.
  `type` becomes `REQ | NFR | ADR | TEST | DESIGN`.
- `artifacts` table gains `created`, `last_updated`, `version` columns;
  `load_sqlite.py` writes them. The separate test-plan path in the index and
  loader goes away: TEST items arrive through the same list as every other
  item.
- `extract.py`:
  - reads `**Version:**` from the header and stamps the four fields on every
    item of the file.
  - `## TEST-<DOM>-<NNNN>:` headings are items of type `TEST`, handled by
    the same heading rule as REQ, NFR and ADR.
  - a file whose header carries `**Document ID:**` and that has no item
    headings is one item of type `DESIGN`: id from that field, title from the
    H1, body the whole document.
  - a file with neither an item heading nor a `**Document ID:**` is a
    validation error naming the file. No row is emitted; the source is
    corrected (REQ-RAP-0006).
  - every id that appears more than once, in one file or across files, is
    reported as one diagnostic naming each file and line. No parsing rule
    works around it.
  - exits non-zero when the validation summary has one or more errors. The
    index and the report are still written, so the fixture can be built and
    the caller still sees the failure. Today it returns 0 regardless.
- Templates print `**Status:**`, `**Created:**`, `**Last Updated:**`,
  `**Version:**` under each item's heading, from the item's own fields.

## Ceilings

- `extract.py` 2,050 lines; `load_sqlite.py` 60; `render.py` 120;
  `record.py` 120; each template 60. No new files except fixtures.

## Acceptance

- `python -m pytest -q tests` passes; a fixture with one REQ file, one test
  plan with two `## TEST-` headings, one design file with `**Document ID:**`,
  one file with no id at all, and one repeated id covers every deliverable.
- Consumer run: `created`, `last_updated` and `version` non-null wherever
  the file header has them; one `TEST` row per `## TEST-` heading; one
  `DESIGN` row per design file that has `**Document ID:**` (4 today);
  every remaining id-less file listed as a validation error (39 design files,
  the schema reference, the HITL files today, fewer as the source is
  corrected); repeated-id diagnostics match the RAP-VAL-1 list until the
  source is corrected; exit code is non-zero until it is.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
