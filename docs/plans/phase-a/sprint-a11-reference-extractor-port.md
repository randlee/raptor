# Sprint A11 — Reference Extractor Port

## Objective

Move the working reference Markdown extractor into Raptor, write its JSON to SQLite,
and render it through five sc-compose Jinja templates to produce the source Markdown.

- Branch: `phase-a/11-reference-extractor-port`
- Stack relation: `must_follow A10`
- PR-completion trigger: A10 merges first.

The reference checkout is read only. Its source, identifiers, paths, configuration,
templates, and fixture values never enter Raptor; Raptor uses invented fixtures only.

## Reference facts and parser contract

The reference index has 783 records. Each has `id`, `title`, `type`, `status`,
`domain`, `document_metadata`, `source`, `content`, `relationships`, and `subsections`.
Status spellings are Draft, Proposed, Active, Approved, Deprecated, and Superseded.
The index population is REQ 555, ADR 178, and NFR 50. A design document maps to
one generic record; a test plan maps to one generic record and preserves its
level-four TEST headings in its source Markdown/subsections.

| Input | Parser behavior |
|---|---|
| `## REQ|NFR|ADR-<scope>-<four digits>: <title>` | Parse level-two artifacts in source order. |
| `#### TEST...: <title>` | Preserve level-four test headings as ordered test-plan evidence. |
| Bold preamble | Parse metadata before sections and preserve unknown keys. |
| Nested sections | Preserve title, level, Markdown text, summary/HTML when emitted, source range, and order. |
| Ranges and references | Preserve raw token/context and resolve target document/id only when unique in the repository. |
| Invalid UTF-8, malformed heading/preamble, unsupported status, duplicate heading, bad nested heading, or no artifact | Emit one stable failure-class code and fail closed for that document; never silently skip it. |

The parser is the only built-in grammar. Delete the old native grammar and its
fixtures. Design and test-plan routes use the existing configured family route:
a level-one title, bold preamble with ID/status, and ordered sections; test
plans additionally preserve zero or more level-four TEST headings.

## A1 reversals

| A1 deliverable | Kept | Dropped | Replaced by |
|---|---|---|---|
| A1-D3 | Provenance/diagnostic boundaries | Five-family field matrix | Extractor grammar and generic ten-field record. |
| A1-D4 | Raptor-only fixture-origin rule | Old parser fixture shape | Reference fixture inventory below. |
| A1-D5 | SourceDocument, origin/materialization | Typed family payloads | Generic records plus document envelope. |
| A1-D6 | Version/ID/unknown-field checks | Measurement, family checks, four reference modes | Extractor diagnostics and unique emitted-reference resolution. |
| A1-D8 | Raptor-only test-origin rule | Family compatibility evidence | Extractor, SQLite, render/reparse fixtures. |

## Scope boundary

A11 is Python/Pydantic/parser/template work only. It changes `markdown_to_json.py`
and runtime operations, not Rust, SQLx, Dolt, a framework, or consumer automation.
Update registered agents/templates that reference the old grammar; A9/A10 use
`(repository_id, document_id, artifact_id)` from A9 registered identity.

The artifact is the index record: ten source fields plus `artifact_type`,
published at schema version `2.0.0` in `schema/json/v2`. No synthetic family
fields are added. `SourceDocument` also retains title, preamble, overview, and
all non-item Markdown as ordered verbatim segments, including text before and
between item blocks. SQLite stores those segments in
`documents.non_item_segments_json`; the smaller one-column form preserves their
order and placement. Relationships use one `relationships` table with source
and nullable resolved `(repository_id, document_id, artifact_id)`, emitted
`relation_type`, target token, and context; `referenced_by` is the reverse query.
Replace v1 SQLite `0001` with v2 `0001`; the SQLite database is regenerated from
Markdown and has no migration path.

| Index field | SQLite column | Jinja usage | Markdown construct |
|---|---|---|---|
| SourceDocument envelope | `documents.non_item_segments_json` | `document.segments` | Title, preamble, overview, and text before/between item blocks. |
| `id` | `artifacts.artifact_id` | `artifact.id` | `## ID: Title` item heading. |
| `title` | `artifacts.title` | `artifact.title` | Item heading title. |
| `type` | `artifacts.artifact_type` | `artifact.type` | Selects the family layout. |
| `status` | `artifacts.status` | `artifact.status` | Parsed from the item's bold Status line when present; stored for queries; not rendered separately. |
| `domain` | `artifacts.domain` | `artifact.domain` | Derived from source path; not rendered. |
| `document_metadata` | `documents.metadata_json` | `document.metadata` | Parsed from the preamble segment in the envelope; stored for queries; not rendered separately. |
| `source` | `artifacts.source_json` | `artifact.source` | Source order and item placement. |
| `content` | `artifacts.content_markdown` (verbatim) | `artifact.content` | Item body rendered verbatim after the heading; summary/HTML re-derived on reparse. |
| `relationships` | `relationships` | `artifact.relationships` | Parsed from reference text inside content; stored for queries; not rendered separately. |
| `subsections` | derived from `content_markdown` | re-derived on reparse | Not rendered. |

Every template consumes all ten fields plus the envelope; `artifact.body` and `provenance_block` are removed from template inputs. The five templates are the
sc-compose form of the consumer layouts: level-one title, bold preamble, `---`
rules, `## ID: Title` item blocks, per-item bold Status, and nested `###`/`####`
sections. `render(extract(document))` is byte-equal to the source document
after LF normalization and exactly one trailing newline, then reparses to equal
JSON. Local invented fixtures mirror that layout; A12 repeats the diff in the
consumer checkout.

## Deliverables

| ID | Deliverable | Evidence |
|---|---|---|
| A11-D1 | Port the parser grammar into the existing profile/runtime path; remove the native grammar and fixtures. | Parser tests cover valid documents and every failure class. |
| A11-D2 | Publish the 2.0.0 generic-record schema and replacement SQLite 0001 with repository/document/artifact identity and emitted relationships. | Model, schema, SQLite, duplicate-ID, and relationship tests. |
| A11-D3 | Replace all five Jinja templates with the consumer layout and render from canonical JSON through sc-compose. | Invented fixture byte parity and Markdown-to-JSON equality. |
| A11-D4 | Update A9/A10 callers, registered agents/templates, docs, ci.yml Verify generated schemas/Verify deterministic schema vendor gates to v2, remove the previous generated schema directory, use replacement v2 DDL, and rewrite `schema/sql/README.md` to the single `relationships` table and re-pointed forward/reverse queries. | Existing ingress/export suites re-run after named contract changes; Enforce Phase A5 exclusions is unchanged because `markdown_to_json.py` is modified, not wrapped. |

## Acceptance criteria

| ID | Criterion |
|---|---|
| A11-AC1 | The parser is the only built-in grammar; selected documents import or receive a stable diagnostic. |
| A11-AC2 | Every artifact preserves all ten index fields, source ordering, source status spelling, and missing-versus-empty values. |
| A11-AC3 | Duplicate local IDs become separate `(repository_id, document_id, artifact_id)` rows; emitted relationships retain raw token/context and resolve uniquely when possible. |
| A11-AC4 | SQLite uses replacement v2 0001 DDL; ingress regenerates the database from Markdown with no migration path. |
| A11-AC5 | A9/A10 suites pass after `artifact_relationships` and `artifact_uri_relationships` are replaced by `relationships`, `RelationshipType` is removed, and `traceability_relationships()`/`reverse_typed_relationships()` query emitted relation types forward/reverse. |
| A11-AC6 | Every file in `plugins/raptor/tests/fixtures/reference/` passes byte parity/reparse: REQ range (two items, one Status), ADR, NFR, design, test plan (two TEST headings), and second REQ reusing a local ID. |
| A11-AC7 | No Rust, SQLx, Dolt, new framework, external source assets, or consumer automation is added. |

## Authoritative validation commands

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m pytest -q \
  schema/tests/models/test_reference_contract.py \
  schema/tests/storage/test_sqlite_store.py \
  schema/tests/json_schema/test_generated_schemas.py \
  plugins/raptor/tests/profiles/test_reference_markdown.py \
  plugins/raptor/tests/operations/test_batch_ingress.py \
  plugins/raptor/tests/round_trip/test_reference_template_parity.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime plugins/raptor/scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m raptor_schema.generate --check --output schema/json/v2
git diff --exit-code -- schema/json/v2
python3 plugins/raptor/scripts/vendor_schema.py --check
python3 plugins/raptor/scripts/validate_plugin.py --check-inventory --check-vendor --check-templates
```

## Traceability

| Requirement | A11 evidence |
|---|---|
| PA-REQ-001, PA-REQ-002, PA-REQ-004 | A11-D1/D2 generic record, repository identity, and diagnostics. |
| PA-REQ-005–PA-REQ-008 | A11-D2–D4 SQLite, agents, templates, and reparse tests. |
| REQ-RAP-013–REQ-RAP-015 | A11-D1/D2/D4 configured ingress and SQLite round trip. |
| REQ-RAP-016 | A11-D3 local parity; A12 owns consumer proof. |
| NFR-RAP-008 | Deterministic parser and round-trip tests. |
