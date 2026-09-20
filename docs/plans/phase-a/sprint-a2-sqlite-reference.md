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

Every authoritative deliverable in this sprint must land production-ready for this stated boundary. A deliverable may not be accepted as schema-only or test-only work while adapter behavior remains open; intentional non-closure is limited to the section below.

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
class ArtifactStore(ArtifactResolver, Protocol):
    def initialize(self) -> None: ...
    def contains(self, key: ArtifactKey) -> bool: ...
    def put_document(self, document: SourceDocument) -> None: ...
    def put_documents(self, documents: Iterable[SourceDocument]) -> None: ...
    def get_document(self, key: DocumentKey) -> SourceDocument: ...
    def delete_document(self, key: DocumentKey) -> None: ...
    def list_artifact_keys(
        self, *, repository_id: RepositoryId | None = None,
        artifact_type: str | None = None,
    ) -> list[ArtifactKey]: ...

def assert_store_conformance(
    store: ArtifactStore,
    documents: Iterable[SourceDocument],
) -> None: ...
```

The reusable conformance helper is dialect-neutral so later Dolt work can run the same behavioral contract. The SQLite DDL uses normalized identity and relationship columns where integrity/querying requires them and canonical JSON payloads where further normalization would duplicate Pydantic validation.

## Authoritative SQLite logical/DDL contract

`0001_initial.sql` must be equivalent to the following table/key contract; names, primary keys, foreign keys, checks, and uniqueness are normative even if formatting differs:

```sql
CREATE TABLE schema_metadata (
  metadata_key TEXT PRIMARY KEY,
  metadata_value TEXT NOT NULL
);

CREATE TABLE repositories (
  repository_id TEXT PRIMARY KEY
);

CREATE TABLE source_documents (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  current_path TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  origin_json TEXT NOT NULL CHECK (json_valid(origin_json)),
  materialization_json TEXT NOT NULL CHECK (json_valid(materialization_json)),
  PRIMARY KEY (repository_id, document_id),
  UNIQUE (repository_id, current_path),
  FOREIGN KEY (repository_id) REFERENCES repositories(repository_id) ON DELETE RESTRICT
);

CREATE TABLE artifacts (
  repository_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  artifact_type TEXT NOT NULL,
  status TEXT NOT NULL,
  artifact_json TEXT NOT NULL CHECK (json_valid(artifact_json)),
  PRIMARY KEY (repository_id, artifact_id),
  FOREIGN KEY (repository_id) REFERENCES repositories(repository_id) ON DELETE RESTRICT
);

CREATE TABLE document_artifacts (
  repository_id TEXT NOT NULL,
  document_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  PRIMARY KEY (repository_id, document_id, artifact_id),
  UNIQUE (repository_id, artifact_id),
  UNIQUE (repository_id, document_id, ordinal),
  FOREIGN KEY (repository_id, document_id)
    REFERENCES source_documents(repository_id, document_id) ON DELETE CASCADE,
  FOREIGN KEY (repository_id, artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE RESTRICT
);

CREATE TABLE artifact_relationships (
  source_repository_id TEXT NOT NULL,
  source_artifact_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  target_repository_id TEXT NOT NULL,
  target_artifact_id TEXT NOT NULL,
  description TEXT,
  PRIMARY KEY (
    source_repository_id, source_artifact_id, relation,
    target_repository_id, target_artifact_id
  ),
  FOREIGN KEY (source_repository_id, source_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE CASCADE,
  FOREIGN KEY (target_repository_id, target_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE RESTRICT
);

CREATE TABLE artifact_uri_relationships (
  source_repository_id TEXT NOT NULL,
  source_artifact_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  target_uri TEXT NOT NULL,
  description TEXT,
  PRIMARY KEY (source_repository_id, source_artifact_id, relation, target_uri),
  FOREIGN KEY (source_repository_id, source_artifact_id)
    REFERENCES artifacts(repository_id, artifact_id) ON DELETE CASCADE
);
```

`schema_metadata` contains exactly one supported database schema-version entry and one canonical model schema-version entry; initialization rejects conflicting values. `origin_json`, `materialization_json`, and `artifact_json` own the complete canonical model values. Scalar columns, membership, ordinals, and relationship tables are indexed integrity/query projections that must equal the JSON on every write and are verified before returning a model; they are never an alternate model authority.

One database may contain many repositories. All document/artifact/membership/reference keys are composite with `repository_id`; no query or adapter method identifies a document or artifact by path or local ID alone.

Replacement is a single transaction keyed by `DocumentKey`: validate the whole incoming document in A1 `store` mode against an overlay of its staged keys plus existing store keys; upsert its repository; remove the old source relationship projections/membership/artifacts that are no longer present; insert/update canonical JSON and projections; then commit. `put_documents` validates the complete staged set using `batch` semantics overlaid on the store and performs the work atomically, so forward/cyclic/cross-repository references can resolve after all target artifacts are staged. Unresolved targets fail with A1's identity-qualified `RAPTOR.REFERENCE.UNRESOLVED`; no transaction begins or all work rolls back. Removing an artifact targeted by another document fails with `RAPTOR.STORAGE.REFERENCE_CONFLICT` rather than cascading. Deleting a document uses the same restriction.

There is deliberately no path-only move API. A current-path change is accepted only as a normal transactional `put_document` of the same `DocumentKey` after A5 has rendered to the new path and updated `.raptor/identity.json`; the incoming model must preserve immutable origin and carry a valid rendered materialization transition whose parent hash is the stored current hash. Any direct/ambiguous path-only change or imported-materialization rewrite fails `RAPTOR.STORAGE.PROVENANCE_TRANSITION`. The transactional put updates `source_documents.current_path` and materialization JSON while preserving composite identity, membership, and relationships. A path collision within one repository fails; identical paths/IDs across different repository IDs are valid.

`get_document` performs A1 structural validation and verifies JSON/projection equality; database foreign keys and the relationship projection establish stored target existence. It does not silently select a weaker or ambient reference-resolution mode.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A2-D1 | Versioned SQLite DDL for source documents, canonical artifacts, document membership/location, typed relationships, and schema metadata, with keys, uniqueness, and referential integrity. | `schema/sql/sqlite/0001_initial.sql` |
| A2-D2 | Small `sqlite3` adapter implementing initialize, transactional put/replace, load, and ID/type listing against A1 models. | `schema/src/raptor_schema/storage/sqlite.py` and public export |
| A2-D3 | Model-to-row mapping documenting authoritative model fields, indexed relational projections, canonical JSON ownership, null/delete/update behavior, and dialect-neutral versus SQLite-specific concerns. | persistence documentation |
| A2-D4 | Reusable dialect-neutral persistence conformance tests callable later against Dolt and callable now by external consumers with their own validated `SourceDocument`. | helper under `schema/tests/storage/` and Raptor-only executions |
| A2-D5 | SQLite tests covering clean/idempotent initialization, rollback, replacement behavior, foreign keys, relationship recovery, and unsupported schema version. | `schema/tests/storage/` |
| A2-D6 | Exact semantic recovery test for all five families and provenance using A1 Raptor fixtures. | canonical comparison evidence |
| A2-D7 | Multi-repository composite-key, replace/delete/rendered-path-update, inbound-reference restriction, JSON/projection ownership, and metadata-version contract. | DDL, adapter behavior, and conformance tests |

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
| A2-AC8 | Same local document/artifact IDs and paths coexist under different repository IDs without collision; no path-only/local-ID-only storage API exists. |
| A2-AC9 | DDL contains every normative table/key/FK/check and JSON ownership rule; corrupt projection/JSON disagreement is detected before model return. |
| A2-AC10 | Replace/delete/rendered-path-update tests cover retained IDs, removed artifacts, inbound reference conflicts, path collision, rollback, immutable origin, valid A5 transition, and rejection of ambiguous path-only changes. |
| A2-AC11 | `put_document` uses store-backed resolution and `put_documents` uses batch-plus-store overlay resolution; tests cover same-document, staged cyclic batch, existing-store, and missing cross-repository targets with rollback. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/storage
python -m pytest schema/tests/storage -k 'round_trip or multi_repository or replacement or delete or rendered_path_update or reference_mode or rollback or foreign_key or projection or schema_version or conformance'
rg -n 'CREATE TABLE|FOREIGN KEY|UNIQUE' schema/sql/sqlite/0001_initial.sql
test ! -e schema/sql/dolt
rg -n '\b(sqlalchemy|sqlx|mysqlclient|pymysql|mysql-connector|doltpy)\b|p3-documentation|REQ-P3-|NFR-P3-|ADR-P3-|\bNFT\b' schema/src schema/tests schema/sql/sqlite schema/pyproject.toml && exit 1 || true
rg -n '^\s*(from|import)\s+(dolt|doltpy|mysql)|dolt://|mysql://' schema/src && exit 1 || true
```

Tests create temporary databases and never commit generated database files.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A2-D1, A2-D2 | PA-REQ-005, PA-NFR-003, PA-NFR-005 |
| A2-D3, A2-D6 | PA-REQ-002, PA-NFR-004 |
| A2-D4, A2-D5 | PA-REQ-005, PA-NFR-001, PA-NFR-006 |
| A2-D6 | PA-REQ-001, PA-REQ-009 |
| A2-D7 | PA-REQ-002, PA-REQ-005, PA-NFR-004, PA-NFR-005 |

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

A3 receives the stable A1 model API and A2 `ArtifactStore` contract for deterministic vendoring/bootstrap and clean-environment verification; it adds no transformation routes. A4 operation scripts may invoke these APIs but may not embed alternate validation or SQL. Missing canonical or persistence behavior is fixed in A1/A2 and merged forward before children continue.
