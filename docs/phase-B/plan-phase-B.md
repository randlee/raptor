# Phase B — Close the gaps between the corpus and the fixture

Phase A produced a SQLite fixture from one Markdown corpus. Comparing that
fixture against `docs/requirements.md` shows the gaps below. Phase B is one
schema change to three scripts, split into sprints that each touch their own
files so they can be built and tested independently. The other gaps are
closed where they belong.

| Gap | Requirement | Owner | Where |
|---|---|---|---|
| Status, Created, Last Updated, Version are file-level, not per item | REQ-RAP-0002 | Raptor | B.1 contract, B.2 parse, B.4 load and render |
| Test cases (`## TEST-` headings) and design documents (`**Document ID:**`) never reach SQLite | REQ-RAP-0002 | Raptor | B.1, B.2, B.4 |
| `id_range`, `range_description` and `relationships.family` are stored on every item row | Operator rule: only item fields become columns | Raptor | B.1 drops them; B.2 stops producing them. Range headers in the source are a human search convenience; Raptor neither reads, stores nor validates them |
| Extractor reports almost nothing: error count hard-coded to zero, dirty values silently defaulted, no duplicate check, text report truncated | REQ-RAP-0006 | Raptor | B.3 |
| Explicit project root ignores `.raptor/raptor.toml` | REQ-RAP-0008 | Raptor | B.2 |
| Raptor's own `docs/` has four documents with no header block and no id, and its test fixture lacks three header fields | REQ-RAP-0006 | Raptor (documents, operator-lead) | B.1 fixtures; B.5 own documents |
| 39 of 43 design files, the schema reference and the HITL files carry no id; id-less documents are not allowed | REQ-RAP-0006 | Consumer repository's architect, task RAP-VAL-1, with the operator directly | Assign ids in the source; Raptor reports each id-less file and emits no row |
| 30 ids repeated in the corpus | REQ-RAP-0006 | Consumer repository's architect, with the operator directly | Source correction; Raptor reports each repeat |
| `hitl/**` excluded and `database/schema` omitted from the scan inventory | REQ-RAP-0008 | Consumer repository's architect, with the operator directly | `.raptor/sources.toml`, `.raptor/routing.toml` in that repository |
| No import skill: the three scripts are run by hand | REQ-RAP-0006 | Raptor | Proposed Sprint B.6, pending the operator |
| Database pointer (URL, or path / environment variable for test) not declared in `.raptor/` | REQ-RAP-0008 | Product | Not in Phase B |
| Product, repository and module scoping | REQ-RAP-0004 | Product | Not in Phase B. Not columns on an item: one requirement may relate to every repository and module, or to one module in one repository. Schema additions beyond fields present in the consumer Markdown are discussed with the operator first. |

## Sprints

| Sprint | Files | Depends on | Runs in parallel with |
|---|---|---|---|
| B.1 Schema contract and fixtures | `schema/record.py`, `schema/record.schema.json`, `schema/schema.sql`, `tests/test_record.py`, `tests/fixtures/**` | — | — |
| B.2 Extractor: parse to the contract | `scripts/extract.py`, `tests/test_extract.py` | B.1 | B.4 |
| B.3 Extractor: validate and report | `scripts/extract.py`, `tests/test_extract.py` | B.2 (same file) | B.4 |
| B.4 Loader and templates | `scripts/load_sqlite.py`, `templates/*.md.j2`, `tests/test_scripts.py` | B.1 | B.2, B.3 |
| B.5 Raptor's own documents comply; consumer run | `docs/*.md`, `.raptor/sources.toml` | B.2, B.3, B.4 | — |

B.1 defines the contract: the model, the SQL, and Markdown fixtures that
comply with it, with the exact JSON each fixture must produce. B.2 and B.4
are built against those fixtures independently. B.3 follows B.2 because both
edit `extract.py`. B.5 is document and configuration work plus the run over
the consumer corpus; no script changes.

## Rules for every sprint

- **Exactly the named deliverables.** A sprint changes the files and
  functions it names and nothing else. Anything else found along the way is
  written in the completion message for the operator; it is not done.
- **Tight scripts.** Every line ceiling is a hard limit; a sprint that needs
  more explains why in its completion message before exceeding it.
- **Very good error reporting, in JSON.** Dirty source is expected. Every
  problem the extractor finds is one object an agent can act on: file, line,
  rule, id, message, fixed remedy. Every occurrence, nothing truncated, the
  whole inventory in one pass. No text report: the readers are agents. A run
  with errors exits non-zero and still writes its outputs.
- **No exceptions for one repository.** The scripts know one document
  format: a header block of `**Field:** value` lines, items as `## <ID>:
  <title>` headings, or a `**Document ID:**` for a document without items.
  A source that deviates is reported and corrected at the source.
- **Parse options only when they are tool options.** An ingress setting in
  `.raptor/` is acceptable when it would make sense for any repository. A
  setting that exists to accept one repository's inconsistency is not. New
  options are discussed with the operator first. Phase B adds none.
- **Only fields present in the source Markdown become columns.** Any other
  schema change is discussed with the operator first.

Phase B does not wait on the consumer repository's corrections. Until the
source is corrected, the extractor lists its problems and exits non-zero;
when the source is corrected, the list is empty and nothing in Raptor changes.
