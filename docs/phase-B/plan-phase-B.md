# Phase B — Close the gaps between the corpus and the fixture

Phase A produced a SQLite fixture from one Markdown corpus. Comparing that
fixture against `docs/requirements.md` shows the gaps below. Phase B is one
sprint of Raptor code; the other gaps are closed where they belong.

| Gap | Requirement | Owner | Where |
|---|---|---|---|
| Status, Created, Last Updated, Version are file-level, not per item | REQ-RAP-0002 | Raptor | Sprint B.1 |
| Test cases (`## TEST-` headings) and design documents (`**Document ID:**`) never reach SQLite | REQ-RAP-0002 | Raptor | Sprint B.1 |
| 39 of 43 design files, the schema reference and the HITL files carry no id; id-less documents are not allowed | REQ-RAP-0006 | Consumer repository's architect, task RAP-VAL-1 | Assign ids in the source; Raptor reports each id-less file as a validation error and emits no row |
| 30 ids repeated in the corpus (title headings, in-file repeats, cross-file collisions) | REQ-RAP-0006 | Consumer repository's architect, task RAP-VAL-1 | Source correction; Raptor only reports each repeat as a diagnostic |
| `id_range` and `range_description` are stored on every item row | Operator rule: only item fields become columns | Raptor | Sprint B.1 drops them. Range headers in the source are a human search convenience; Raptor neither stores nor validates them |
| `hitl/**` excluded and `database/schema` omitted from the scan inventory | REQ-RAP-0008 | Consumer repository's architect, task RAP-VAL-1 | `.raptor/sources.toml`, `.raptor/routing.toml` in that repository |
| No import skill: the three scripts are run by hand, the extractor's error count is hard-coded to zero and it exits 0, so dirty source passes silently | REQ-RAP-0006 | Raptor | Exit code in Sprint B.1; the skill that runs extract, load and render and stops on any error is a proposed Sprint B.2, pending the operator |
| Database pointer (URL, or path / environment variable for test) not declared in `.raptor/` | REQ-RAP-0008 | Product | Not in Phase B |
| Product, repository and module scoping | REQ-RAP-0004 | Product | Not in Phase B. Not columns on an item: one requirement may relate to every repository and module, or to one module in one repository. Schema additions beyond fields present in the consumer Markdown are discussed with the operator first. |

## Principles for Phase B code

- **Tight scripts.** Three scripts, no framework. Every line ceiling in a
  sprint document is a hard limit; a sprint that needs more explains why.
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
  `.raptor/` is acceptable when it would make sense for any repository
  (for example which folders to scan, which artifact type a folder routes
  to). A setting that exists to accept one repository's inconsistency is
  not. New options are discussed with the operator first.

Sprint B.1 does not wait on RAP-VAL-1. Until the source is corrected, the
fixture carries the repeated ids and the extractor lists them; when the
source is corrected, the list is empty and nothing in Raptor changes.
