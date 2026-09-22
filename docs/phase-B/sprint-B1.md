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
  null when the file header lacks them). `created` and `last_updated` are
  ISO 8601 (REQ-RAP-0009); the source headers are date-only `YYYY-MM-DD`
  and are stored as written, never given a time or zone. They move out of
  `document_metadata`, which keeps `owner` only. `id_range` and
  `range_description` are dropped: a range is a document-level search
  convenience in one source repository, not a field of an item, and most
  repositories have no such header. Raptor neither reads, stores, prints
  nor validates it: the `**ID Range:**` lines in the three templates, the
  two fields in `record.py` and `record.schema.json`, and the range parsing
  in `extract.py` all go.
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
    reported as one diagnostic per occurrence naming file and line. No
    parsing rule works around it.
  - error reporting is rewritten to one format: `file:line: RULE id message`,
    one line per occurrence, grouped by file, complete. Today the
    `validation` block is hard-coded to zero errors, the only check is the
    record model (a failure aborts the run without writing the index), and
    the text report truncates to 10 files and 5 errors each. All of that
    goes. The same entries are in the index's `validation` block.
    Rules in this sprint: `MISSING_ID` (no item heading and no Document ID),
    `DUPLICATE_ID`, `MISSING_HEADER_FIELD` (Status, Created, Last Updated,
    Version, Owner), `INVALID_DATE` (Created or Last Updated not ISO 8601,
    for example the literal `YYYY-MM-DD`). Nothing else.
  - exits non-zero when the validation summary has one or more errors. The
    index and the report are still written, so the fixture can be built and
    the caller still sees the failure. Today it returns 0 regardless.
  - adds no ingress parse options. If one proves necessary it is proposed
    as an option any repository could use and discussed with the operator
    before it is added.
- Templates print `**Status:**`, `**Created:**`, `**Last Updated:**`,
  `**Version:**` under each item's heading, from the item's own fields.

## Ceilings

- `extract.py` 2,050 lines; `load_sqlite.py` 60; `render.py` 120;
  `record.py` 120; each template 60. No new files except fixtures.

## Acceptance

- `python -m pytest -q tests` passes; a fixture with one REQ file, one test
  plan with two `## TEST-` headings, one design file with `**Document ID:**`,
  one file with no id at all, one file missing a header field, and one
  repeated id covers every deliverable. The test asserts the exact report
  lines for each dirty file and the non-zero exit code.
- Consumer run: `created`, `last_updated` and `version` non-null wherever
  the file header has them; one `TEST` row per `## TEST-` heading; one
  `DESIGN` row per design file that has `**Document ID:**` (4 today);
  every remaining id-less file listed as a validation error (39 design files,
  the schema reference, the HITL files today, fewer as the source is
  corrected); repeated-id diagnostics match the RAP-VAL-1 list until the
  source is corrected; exit code is non-zero until it is.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
