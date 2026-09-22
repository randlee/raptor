# Sprint A10 — SQLite Export Proof

## Objective

Prove the durable product path from a selected SQLite document through canonical
Pydantic JSON and sc-compose Markdown rendering, then reparse and compare the
result for every canonical family.

- Branch: `phase-a/10-sqlite-export-proof`
- Stack relation: `must_follow A9`
- Merge-forward trigger: A9 development is pushed; merge A9 into A10 before each development or fix round.
- PR-completion trigger: A9 PR merges first.

## Scope boundary

A10 hardens the existing `export_sqlite.py` and `json_to_markdown.py` thin
wrappers, their runtime export/render operations and report mode, sc-compose
templates, semantic comparator, and SQLite adapter tests. `export_sqlite.py`
hosts SQLite→JSON export and `json_to_markdown.py` hosts JSON→Markdown render;
their shared runtime operation is exercised by proof tests. No new wrapper is
added. A10 does not create a second renderer, a second JSON model, or a Rust
query layer. The SQL projection remains a view of the authoritative
Pydantic/canonical JSON contract.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A10-D1 | Per-family SQLite→canonical JSON export proof using the existing `SQLiteArtifactStore` and `export_sqlite.py`. | REQ, NFR, ADR, design, and test-plan export fixtures. |
| A10-D2 | sc-compose render/reparse comparison that permits only the existing materialization transition. | Canonical path-difference assertions and mutation tests. |
| A10-D3 | Deterministic render and explicit zero-loss report covering schema fields, artifact order, identity, relationships, immutable origin, and materialization provenance. The report reuses and extends the A9 versioned Pydantic report model family; it does not introduce a second report model, and its JSON Schema is generated and drift-gated with that family. | Repeated-render byte comparison, report fixtures, and report-model/schema drift assertions. |
| A10-D4 | SQLite traceability-query fixtures and SQL documentation naming the tables/columns a future agent-facing CLI reads. | Queries through `source_documents`, `document_artifacts`, `artifacts`, and emitted `relationships`. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A10-AC1 | Each REQ, NFR, ADR, design, and test-plan document completes SQLite→JSON→sc-compose→Markdown→JSON with canonical semantic equality after only the documented materialization transition. |
| A10-AC2 | Two renders of identical canonical JSON produce identical Markdown bytes. |
| A10-AC3 | The loss report is zero for every content-bearing field and explicitly includes artifact order, typed/URI relationships, repository/document/artifact identity, immutable origin, and materialization provenance. |
| A10-AC4 | Forward and reverse traceability queries return queryable emitted relationship types represented by canonical JSON. |
| A10-AC5 | `schema/sql/README.md` identifies the traceability tables and columns as the future Rust CLI handoff contract without adding Rust code. |
| A10-AC6 | Markdown is generated only by sc-compose; Python validates, queries, compares, and reports but does not assemble complete Markdown documents. |
| A10-AC7 | The zero-loss report validates through the A9 Pydantic report model family, extends that family only where A10 fields require it, and passes the generated-schema, schema-contract, and deterministic vendor drift gates. |

## Authoritative validation commands

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/schema/src" python3 -m pytest -q \
  schema/tests/storage/test_sqlite_store.py \
  schema/tests/storage/test_sqlite_traceability_queries.py \
  schema/tests/models/test_ingress_report.py \
  schema/tests/json_schema/test_generated_schemas.py \
  plugins/raptor/tests/round_trip/test_round_trip.py \
  plugins/raptor/tests/round_trip/test_sqlite_export_proof.py
which sc-compose && sc-compose --version
python3 plugins/raptor/scripts/validate_plugin.py --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0'
python3 plugins/raptor/scripts/vendor_schema.py --check
```

## Traceability

| Deliverable | Requirements |
|---|---|
| A10-D1, A10-D2 | PA-REQ-005, PA-REQ-007, PA-REQ-008, REQ-RAP-014, REQ-RAP-015 |
| A10-D3 | PA-NFR-004, NFR-RAP-008 |
| A10-D4 | PA-REQ-002, REQ-RAP-015 |

## Risks

| Risk | Mitigation |
|---|---|
| Rendering drops a value that SQLite recovered | Compare reparsed canonical JSON and emit field-level report entries. |
| Relationship data is recoverable but not queryable | Assert direct forward/reverse SQL projections as well as canonical recovery. |
| Template output depends on ambient ordering | Run deterministic byte comparisons from identical JSON. |

## Non-closure

- A10 proves Raptor-owned family fixtures and reusable export behavior; A12 proves the external corpus.
- A10 does not add consumer-specific templates, profiles, or fixtures to Raptor.
- Deferred: byte-unit ledgers, transformation/derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
