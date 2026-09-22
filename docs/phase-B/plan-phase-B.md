# Phase B — Fill the gaps between the Markdown and the rows

Phase A left gaps: information present in the Markdown files was not
showing up in rows. Status, Created, Last Updated, Version and Owner were
kept at file level instead of on each item; TEST items and design documents
never became rows; computed things (HTML, summaries, path-derived domains,
section lines, subsection indexes) were stored as if they were information;
and the parser reported almost nothing, so a file that failed to land in a
row failed silently. Phase B fills those gaps with the schema below. Doing
so will uncover non-compliance in the consumer corpus, which is fixed with
minor corrections in that repository, not with exceptions in the parser.

A REQ, NFR, ADR, TEST or DESIGN item is information. That information maps
to a schema, expressed once as SQL and once as JSON with the same field
names. SQL to JSON is mechanical. JSON to Markdown is mechanical: an
sc-compose template. Markdown to JSON is parsed, and is the only place with
judgement in it; its output includes every problem it found.

## The schema

| field | source in Markdown | SQL |
|---|---|---|
| id | `## <ID>: <title>` heading, or `**Document ID:**` | TEXT PRIMARY KEY |
| type | id prefix: REQ, NFR, ADR, TEST; DESIGN for a Document ID file | TEXT NOT NULL |
| title | the heading, or the H1 of a Document ID file | TEXT NOT NULL |
| status | item `**Status:**` line, else header `**Status:**` | TEXT NOT NULL |
| created | header `**Created:**` | TEXT NOT NULL |
| last_updated | header `**Last Updated:**` | TEXT NOT NULL |
| version | header `**Version:**` | TEXT NOT NULL |
| owner | header `**Owner:**` | TEXT NOT NULL |
| body | the item's Markdown below its heading, verbatim | TEXT NOT NULL |
| references | ids mentioned in the body | table `relationships(source_id, target_id, context)` |

Nothing computed is stored. Dates are ISO 8601 as written (REQ-RAP-0009).
Range headers in the source are a human search convenience: not read, not
stored, not validated. Product, repository and module scoping (REQ-RAP-0004)
is a Product decision and is not in Phase B. Any field beyond this table is
discussed with the operator first.

## Gaps closed elsewhere

| Gap | Owner | Where |
|---|---|---|
| 39 of 43 design files, the schema reference and the HITL files carry no id; 30 ids repeated | Consumer repository's architect, task RAP-VAL-1, with the operator directly | Source correction; the parser reports every occurrence and emits no row for an id-less file |
| `hitl/**` excluded and `database/schema` omitted from the scan | Consumer repository's architect, with the operator directly | That repository's `.raptor/` |
| No import skill; scripts run by hand | Raptor | Proposed Sprint B.6, pending the operator |
| Database pointer not declared in `.raptor/` | Product | Not in Phase B |

## Sprints

| Sprint | Files | Depends on | Parallel with |
|---|---|---|---|
| B.1 Schema and the two mechanical mappings | `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`, `scripts/render.py`, `templates/*.md.j2`, `tests/fixtures/records.json`, `tests/test_record.py` | — | — |
| B.2 Parser: Markdown to JSON | `scripts/extract.py`, `tests/test_extract.py` | B.1 | B.3 |
| B.3 Loader: JSON to SQL and back | `scripts/load_sqlite.py`, `tests/test_load.py` | B.1 | B.2 |
| B.4 Parser: diagnostics | `scripts/extract.py`, `tests/test_extract.py` | B.2 | — |
| B.5 Raptor's own documents comply; consumer run | `docs/*.md`, `.raptor/` | B.2, B.3, B.4 | — |

The one hand-written fixture is `tests/fixtures/records.json`: six records in
schema shape. B.1 proves render and SQL against it. B.2 proves the parser
by round trip: render the records, parse the Markdown, compare for equality.
B.3 proves the loader by round trip: load, read back, compare. B.4 proves
diagnostics by mutating rendered files one defect at a time.

## Rules for every sprint

- **Exactly the named deliverables.** A sprint changes the files and
  functions it names and nothing else. Anything else found is written in the
  completion message for the operator; it is not done.
- **Tight scripts.** Line ceilings are hard limits.
- **Very good error reporting, in JSON.** Dirty source is expected. Every
  problem is one object an agent can act on: file, line, rule, id, message,
  fixed remedy. Every occurrence, whole inventory, one pass, no text report.
  A run with errors exits non-zero and still writes its output.
- **No exceptions for one repository.** One document format: header block of
  `**Field:** value` lines, items as `## <ID>: <title>`, or `**Document ID:**`
  for a document without items. Deviations are reported and fixed at source.
- **Parse options only when they are tool options.** Phase B adds none.

Phase B does not wait on the consumer repository's corrections.
