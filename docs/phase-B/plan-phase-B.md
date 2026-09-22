# Phase B — Close the gaps between the corpus and the fixture

Phase A produced a SQLite fixture from one Markdown corpus. Comparing that
fixture against `docs/requirements.md` shows the gaps below. Phase B is one
sprint of Raptor code; the other gaps are closed where they belong.

| Gap | Requirement | Owner | Where |
|---|---|---|---|
| Status, Created, Last Updated, Version are file-level, not per item | REQ-RAP-0002 | Raptor | Sprint B.1 |
| Test cases (`## TEST-` headings) and design documents (`**Document ID:**`) never reach SQLite | REQ-RAP-0002 | Raptor | Sprint B.1 |
| 39 of 43 design files, the schema reference and the HITL files carry no id; id-less documents are not allowed | REQ-RAP-0006 | Consumer repository's architect, task RAP-VAL-1 | Assign ids in the source; Raptor reports each id-less file as a validation error and emits no row |
| 30 ids repeated in the corpus (title headings, in-file repeats, cross-file collisions); one ID Range claimed by two files | REQ-RAP-0006 | Consumer repository's architect, task RAP-VAL-1 | Source correction; Raptor only reports each repeat as a diagnostic |
| `hitl/**` excluded and `database/schema` omitted from the scan inventory | REQ-RAP-0008 | Consumer repository's architect, task RAP-VAL-1 | `.raptor/sources.toml`, `.raptor/routing.toml` in that repository |
| No import skill: the three scripts are run by hand and the extractor exits 0 on validation errors, so dirty source can pass silently | REQ-RAP-0006 | Raptor | Exit code in Sprint B.1; the skill that runs extract, load and render and stops on any error is a proposed Sprint B.2, pending the operator |
| Database pointer (URL, or path / environment variable for test) not declared in `.raptor/` | REQ-RAP-0008 | Product | Not in Phase B |
| Product, repository and module scoping | REQ-RAP-0004 | Product | Not in Phase B. Not columns on an item: one requirement may relate to every repository and module, or to one module in one repository. Schema additions beyond fields present in the consumer Markdown are discussed with the operator first. |

Sprint B.1 does not wait on RAP-VAL-1. Until the source is corrected, the
fixture carries the repeated ids and the extractor lists them; when the
source is corrected, the list is empty and nothing in Raptor changes.
