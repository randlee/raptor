# Sprint A11 — Reference Extractor Port

## Objective

Move the working reference Markdown extractor into Raptor, write its JSON to
SQLite, and render the same JSON through five sc-compose Jinja templates to
produce the same Markdown as the consumer templates.

- Branch: `phase-a/11-reference-extractor-port`
- Stack relation: `must_follow A10`
- PR-completion trigger: A10 merges first.

The reference checkout is read only. Its source, identifiers, paths,
configuration, templates, and fixture values never enter Raptor. Raptor uses
invented, domain-neutral fixtures only.

## Reference facts and parser contract

The reference index has 783 records. Each record has these ten fields:
`id`, `title`, `type`, `status`, `domain`, `document_metadata`,
`source`, `content`, `relationships`, and `subsections`. Status
spellings are Draft, Proposed, Active, Approved, Deprecated, and Superseded.

| Input | Parser behavior |
|---|---|
| `## REQ|NFR|ADR-<scope>-<four digits>: <title>` | Parse level-two artifacts in source order. |
| `#### TEST...: <title>` | Preserve level-four test headings as ordered test-plan evidence. |
| Bold preamble | Parse metadata before body sections and preserve unknown keys. |
| Nested sections | Preserve title, level, Markdown body, summary/HTML when emitted, source range, and order. |
| Ranges and references | Preserve raw token/context and resolve target document/id only when unique in the repository. |
| Invalid UTF-8, malformed heading/preamble, unsupported status, duplicate heading, bad nested heading, or no artifact | Emit one stable failure-class code and fail closed for that document; never silently skip it. |

The parser is the only built-in grammar. Delete the old native grammar and its
fixtures. Design and test-plan routes use the existing configured family route:
a level-one title, bold preamble with ID/status, and ordered sections; test
plans additionally preserve zero or more level-four TEST headings.

## A1 reversals

| Previous assumption | A11 replacement |
|---|---|
| Native level-three em-dash headings and inline fields. | Use the parser contract above. |
| Three-digit IDs, `TST`, and lower-case lifecycle normalization. | Retain four-digit IDs, TEST headings, and the six source status spellings. |
| Synthetic family fields and repository/artifact-only uniqueness. | The index record is the artifact; identity is document plus artifact ID. |

## Scope boundary

A11 is Python/Pydantic/parser/template work only. It changes the existing
`markdown_to_json.py` and runtime operations, not Rust, SQLx, Dolt, a new
framework, or consumer automation. Update registered agents and templates that
reference the old grammar. A9/A10 callers use the new model and composite key.

The artifact is the index record: ten source fields plus `artifact_type`,
published at schema version `2.0.0` in `schema/json/v2`. No synthetic
family fields are added. Relationships are stored as emitted: raw token and
context with nullable resolved document/id when unique. One relationships table
is sufficient. Replace v1 SQLite `0001` with v2 `0001`; the SQLite database
is regenerated from Markdown and has no migration path.

The five sc-compose Jinja templates receive canonical JSON. For the same JSON,
their Markdown must equal the consumer TEMPLATE Markdown produced by literal
`{{KEY}}` replacement, after LF normalization, one trailing newline, and the
application-date token only. Local invented fixtures mirror the template
structure; A12 performs the consumer-side parity diff.

## Deliverables

| ID | Deliverable | Evidence |
|---|---|---|
| A11-D1 | Port the parser grammar into the existing profile/runtime path; remove the native grammar and fixtures. | Parser tests cover valid documents and every failure class. |
| A11-D2 | Publish the 2.0.0 Pydantic/JSON schema and replacement SQLite 0001 with composite document/artifact identity and emitted relationships. | Model, schema, SQLite, duplicate-ID, and relationship tests. |
| A11-D3 | Replace all five Jinja templates and render from canonical JSON through sc-compose. | Invented five-family fixture parity and Markdown-to-JSON equality. |
| A11-D4 | Update A9/A10 callers, registered agents/templates, documentation, and tests for the replacement parser/model. | Existing ingress/export suites re-run without a wrapper or adapter. |

## Acceptance criteria

| ID | Criterion |
|---|---|
| A11-AC1 | The parser is the only built-in grammar; selected documents import or receive a stable diagnostic. |
| A11-AC2 | Every artifact preserves all ten index fields, source ordering, source status spelling, and missing-versus-empty values. |
| A11-AC3 | Duplicate local IDs in different source documents become separate composite-key rows; emitted relationships retain raw token/context and resolve uniquely when possible. |
| A11-AC4 | SQLite uses replacement v2 0001 DDL; ingress regenerates the database from Markdown with no migration path. |
| A11-AC5 | A9/A10 use the replacement parser/model/key contract and their suites pass. |
| A11-AC6 | All five Jinja templates produce parity Markdown for the same canonical JSON under the three permitted normalizations, then reparse to equal JSON. |
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
| PA-REQ-001–PA-REQ-004 | A11-D1/D2 parser, model, identity, and diagnostics. |
| PA-REQ-005–PA-REQ-008 | A11-D2–D4 SQLite, agents, templates, and reparse tests. |
| REQ-RAP-013–REQ-RAP-015 | A11-D1/D2/D4 configured ingress and SQLite round trip. |
| REQ-RAP-016 | A11-D3 local parity; A12 owns consumer proof. |
| NFR-RAP-008 | Deterministic parser and round-trip tests. |
