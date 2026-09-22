# Phase B — Three missed fields, round-tripped

Phase A left a gap: information in the Markdown files was not showing up in
rows. The parser missed three header fields, `Created`, `Last Updated` and
`Version`, and kept `Status` only at file level. Phase B adds those three
fields to the record and makes sure they round-trip through every mapping:
SQL to JSON is mechanical, JSON to Markdown is mechanical (an sc-compose
template), Markdown to JSON is parsed. Filling the gap will uncover
non-compliance in the consumer corpus, fixed with minor corrections in that
repository, not with exceptions in the parser.

## The change

| field | source in Markdown | JSON | SQL |
|---|---|---|---|
| created | header `**Created:**` | `created: str` | `created TEXT NOT NULL` |
| last_updated | header `**Last Updated:**` | `last_updated: str` | `last_updated TEXT NOT NULL` |
| version | header `**Version:**` | `version: str` | `version TEXT NOT NULL` |

Required, never null; ISO 8601 as written (REQ-RAP-0009). Also, because
they follow from the same gap: `status` becomes required (item line, else
header); every id declaration becomes a row whatever its prefix, so `TEST`
and `DESIGN` ids land (REQ-RAP-0002); and the range fields (`id_range`,
`range_description`, `relationships.family`) leave the record, since range
is a source-side search convenience and not an item field. Nothing else in
the record changes. Any further schema change is discussed with the
operator first.

A file is only where an id happens to land today. An id is declared by
`## <ID>: <title>` or by `**Document ID:** <ID>`; its type is its prefix;
the header block of whichever file it sits in supplies Status, Created,
Last Updated, Version and Owner. Which ids share a file is irrelevant: a
REQ and an NFR in one file or in two parse the same.

## Gaps closed elsewhere

| Gap | Owner | Where |
|---|---|---|
| Id-less design, schema-reference and HITL files; 30 repeated ids | Consumer repository's architect, task RAP-VAL-1, with the operator directly | Source correction; the parser reports every occurrence and emits no row for an id-less file |
| `hitl/**` excluded and `database/schema` omitted from the scan | Consumer repository's architect, with the operator directly | That repository's `.raptor/` |
| No import skill | Raptor | Proposed Sprint B.6, pending the operator |
| Database pointer in `.raptor/`; product/repository/module scoping | Product | Not in Phase B |

## Sprints

| Sprint | Files | Depends on | Parallel with |
|---|---|---|---|
| B.1 Schema, templates, fixture | `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`, `templates/*.md.j2`, `tests/fixtures/records.json`, `tests/test_record.py` | — | — |
| B.2 Parser reads the fields | `scripts/extract.py`, `tests/test_extract.py` | B.1 | B.3 |
| B.3 Loader writes the columns | `scripts/load_sqlite.py`, `tests/test_load.py` | B.1 | B.2 |
| B.4 Parser diagnostics | `scripts/extract.py`, `tests/test_extract.py` | B.2 | — |
| B.5 Raptor's own documents comply; consumer run | `docs/*.md`, `.raptor/` | B.2, B.3, B.4 | — |

One hand-written fixture, `tests/fixtures/records.json`: six records in
full `Record` shape. B.1 renders it. B.2 proves the parser by round trip:
render, parse, compare for equality. B.3 proves the loader by round trip:
load, read back, compare. B.4 proves diagnostics by mutating rendered files
one defect at a time.

## Rules for every sprint

- **Exactly the named deliverables.** Anything else found is written in the
  completion message for the operator; it is not done.
- **Tight scripts.** Line ceilings are hard limits. `extract.py` ends the
  phase smaller than it starts. New non-test, non-fixture code across the
  whole phase is under 150 lines; the rest is deletion and field plumbing.
- **Very good error reporting, in JSON.** Every problem is one object: file,
  line, rule, id, message, fixed remedy. Every occurrence, whole inventory,
  one pass, no text report. Errors exit non-zero; output still written.
- **No exceptions for one repository.** One document format: header block
  of `**Field:** value` lines, items as `## <ID>: <title>`, or
  `**Document ID:**` for a document without items.
- **Parse options only when they are tool options.** Phase B adds none.

Phase B does not wait on the consumer repository's corrections.
