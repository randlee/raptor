# Sprint A2 — SQLite Reference Persistence

## Objective

Express the A1 semantic model as a minimal logical SQL schema and Python reference adapter that stores and recovers validated canonical documents in SQLite without losing semantics or provenance.

- Branch: `phase-a/02-sqlite-reference`
- Stack relation: `must_follow A1`
- Merge-forward trigger: A1 development is pushed; merge A1 into A2 before every development/fix round.
- PR-completion trigger: A1 PR merges first.

## Scope boundary

There is one semantic/logical Raptor schema: the A1 models and canonical JSON contract. SQL DDL and adapters are independent dialect projections of that contract, not competing domain schemas. Phase A implements only SQLite under `schema/sql/sqlite/` and a `sqlite3` adapter under `schema/src/raptor_schema/`. A later phase may add `schema/sql/dolt/` and a Dolt adapter after conformance is proven; A2 must not create an empty Dolt placeholder.

The implementation uses Python's standard `sqlite3` unless a reviewed requirement proves otherwise. It is not a general ORM, service, migration framework, server driver, or Rust SQLx layer.

## Layout and public contract

```text
schema/
  sql/sqlite/0001_initial.sql
  src/raptor_schema/
    storage/
      sqlite.py
  tests/storage/
```

```python
class ArtifactStore(Protocol):
    def initialize(self) -> None: ...
    def put_document(self, document: SourceDocument) -> None: ...
    def get_document(self, repository_path: str) -> SourceDocument: ...
    def list_artifact_ids(self, *, artifact_type: str | None = None) -> list[str]: ...

def assert_store_conformance(
    store: ArtifactStore,
    documents: Iterable[SourceDocument],
) -> None: ...
```

The reusable conformance helper is dialect-neutral so later Dolt work can run the same behavioral contract. The SQLite DDL uses normalized identity and relationship columns where integrity/querying requires them and canonical JSON payloads where further normalization would duplicate Pydantic validation.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A2-D1 | Versioned SQLite DDL for source documents, canonical artifacts, document membership/location, typed relationships, and schema metadata, with keys, uniqueness, and referential integrity. | `schema/sql/sqlite/0001_initial.sql` |
| A2-D2 | Small `sqlite3` adapter implementing initialize, transactional put/replace, load, and ID/type listing against A1 models. | `schema/src/raptor_schema/storage/sqlite.py` and public export |
| A2-D3 | Model-to-row mapping documenting authoritative model fields, indexed relational projections, canonical JSON ownership, null/delete/update behavior, and dialect-neutral versus SQLite-specific concerns. | persistence documentation |
| A2-D4 | Reusable dialect-neutral persistence conformance tests callable later against Dolt and callable now by external consumers with their own validated `SourceDocument`. | helper under `schema/tests/storage/` and Raptor-only executions |
| A2-D5 | SQLite tests covering clean/idempotent initialization, rollback, replacement behavior, foreign keys, relationship recovery, and unsupported schema version. | `schema/tests/storage/` |
| A2-D6 | Exact semantic recovery test for all five families and provenance using A1 Raptor fixtures. | canonical comparison evidence |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A2-AC1 | Clean in-memory and file-backed SQLite databases initialize deterministically from `0001_initial.sql` with foreign-key enforcement enabled. |
| A2-AC2 | Storing then loading any valid A1 `SourceDocument` produces the same normalized canonical model, including meaningful order/locations, relationships, extensions, and provenance. |
| A2-AC3 | A failed multi-artifact write leaves no partial document, artifact, or relationship state. |
| A2-AC4 | Replacing the same source document has explicit tested semantics and cannot create duplicate identities or dangling relations. |
| A2-AC5 | Checked-in SQLite DDL is the dialect authority; tests reject adapter assumptions absent from DDL and unsupported database schema versions. |
| A2-AC6 | The conformance helper depends on `ArtifactStore`, not SQLite internals, and external callers can run it with their own models while Raptor tests remain Raptor-owned. |
| A2-AC7 | No SQLAlchemy, server process, MySQL/Dolt code or placeholder, Rust SQLx dependency, or consumer-specific table/column is introduced. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/storage
python -m pytest schema/tests/storage -k 'round_trip or rollback or foreign_key or schema_version or conformance'
rg -n 'CREATE TABLE|FOREIGN KEY|UNIQUE' schema/sql/sqlite/0001_initial.sql
test ! -e schema/sql/dolt
rg -n '\b(sqlalchemy|sqlx|mysql|dolt)\b|p3-documentation|REQ-P3-|NFR-P3-|ADR-P3-|\bNFT\b' schema/src schema/tests schema/sql/sqlite && exit 1 || true
```

Tests create temporary databases and never commit generated database files.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A2-D1, A2-D2 | PA-REQ-005, PA-NFR-003, PA-NFR-005 |
| A2-D3, A2-D6 | PA-REQ-002, PA-NFR-004 |
| A2-D4, A2-D5 | PA-REQ-005, PA-NFR-001, PA-NFR-006 |
| A2-D6 | PA-REQ-001, PA-REQ-009 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Full normalization duplicates every Pydantic field | normalize identity, membership, and relations only; keep one versioned canonical payload for complete recovery. |
| JSON payloads bypass validation | accept and return `SourceDocument`, validating on both boundaries; expose no public raw insert. |
| SQLite details distort the logical contract | isolate dialect DDL/adapter and exercise a dialect-neutral conformance suite. |
| Premature Dolt planning creates dead structure | add no Dolt directory or placeholder until a later sprint owns executable Dolt conformance. |

## Non-closure

- No Dolt/MySQL DDL, adapter, directory placeholder, server, branching workflow, or operational migration.
- No Rust database dependency or SQLx implementation.
- No bulk importer, CLI service, web API, or consumer migration.
- No source-profile parser or renderer.

## Handoff to A3

A3 receives the stable A1 model API and A2 `ArtifactStore` contract. Plugin scripts may invoke them but may not embed alternate validation or SQL. Missing canonical or persistence behavior is fixed in A1/A2 and merged forward before A3 continues.
