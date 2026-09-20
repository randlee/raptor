# Sprint A1 — Canonical Contract, Pydantic Models, and JSON Schema

## Objective

Freeze the Phase A artifact contract in Raptor's own REQ/NFR/ADR documents, then publish a small Python contract for canonical JSON covering all five artifact families, source provenance, references, versioning, deterministic serialization, and generated JSON Schema.

- Branch: `phase-a/01-models-and-json-schema`
- Stack relation: root sprint, `must_follow develop`
- PR base/stack root: `develop`

## Scope boundary

This sprint owns the semantic contract and its executable representation under top-level `schema/`. Raptor-owned REQ/NFR/ADR artifacts are normative inputs and the only origin for examples. Models validate canonical JSON, not a consumer's Markdown conventions. Persistence, plugin packaging, and Markdown rendering remain later closures. `NFR` is canonical and `NFT` is invalid.

Every authoritative deliverable in this sprint must land production-ready for this stated boundary. A deliverable may not be accepted as a shape-only stub or silently carried into A2; intentional non-closure is limited to the section below.

## Public contract and layout

```text
schema/
  pyproject.toml
  src/raptor_schema/
    models/
    canonical.py
  json/v1/
  tests/
    models/
    json_schema/

.raptor/
  identity.json
```

The implementation may refine model module names, but the public type relationship must remain equivalent to:

```python
Artifact = Annotated[
    Requirement
    | NonFunctionalRequirement
    | ArchitectureDecision
    | DesignDocument
    | TestPlan,
    Field(discriminator="artifact_type"),
]

class DocumentKey(BaseModel):
    repository_id: RepositoryId
    document_id: DocumentId

class ArtifactKey(BaseModel):
    repository_id: RepositoryId
    artifact_id: ArtifactId

class OriginProvenance(BaseModel):
    repository_id: RepositoryId
    document_id: DocumentId
    initial_repository_path: RepositoryPath
    original_content_sha256: Sha256
    source_format: Literal["markdown"]
    parser_profile: str
    parser_profile_version: str

class MaterializationProvenance(BaseModel):
    repository_path: RepositoryPath
    content_sha256: Sha256
    operation: Literal["imported", "rendered"]
    parent_content_sha256: Sha256 | None = None
    parser_profile: str
    parser_profile_version: str
    template_set: str | None = None
    template_version: str | None = None

class SourceProvenance(BaseModel):
    origin: OriginProvenance
    materialization: MaterializationProvenance

class SourceDocument(BaseModel):
    schema_version: str
    provenance: SourceProvenance
    artifacts: list[Artifact]

class ReferenceValidationMode(str, Enum):
    STRUCTURAL = "structural"
    DOCUMENT = "document"
    BATCH = "batch"
    STORE = "store"

class ArtifactResolver(Protocol):
    def contains(self, key: ArtifactKey) -> bool: ...

def validate_document(
    value: object, *, reference_mode: ReferenceValidationMode = ReferenceValidationMode.STRUCTURAL,
    resolver: ArtifactResolver | None = None,
) -> SourceDocument: ...
def validate_documents(
    values: Iterable[object], *,
    reference_mode: ReferenceValidationMode = ReferenceValidationMode.BATCH,
    resolver: ArtifactResolver | None = None,
) -> tuple[SourceDocument, ...]: ...
def dump_canonical_json(document: SourceDocument) -> str: ...
def generate_json_schemas(output_dir: Path) -> None: ...
```

Shared artifact fields include stable ID, title, lifecycle status, typed relationships, the documented body/summary fields, and explicit namespaced extensions. Each family owns only its documented payload. Dates, enum values, ordering, omitted optional values, and extension keys have one canonical serialization.

The source-profile boundary is documented in this sprint for later plugin implementation:

```python
class SourceProfile(Protocol):
    profile_id: str
    profile_version: str

    def parse(self, source: SourceInput) -> ParsedDocument: ...
    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]: ...
    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument: ...
    def project_render_input(self, document: SourceDocument) -> dict[str, object]: ...
    def normalize(self, document: SourceDocument) -> ComparableDocument: ...
```

### Source-profile concrete boundary

```python
@dataclass(frozen=True)
class SourceInput:
    repo_root: Path                 # resolved repository root
    repository_id: RepositoryId
    document_id: DocumentId
    repository_path: PurePosixPath # relative to repo_root
    content: bytes

@dataclass(frozen=True)
class ParsedSection:
    kind: str
    heading: str | None
    body: str
    location: SourceLocation
    attributes: Mapping[str, JsonValue]

@dataclass(frozen=True)
class ParsedDocument:
    source: SourceInput
    frontmatter: Mapping[str, JsonValue]
    sections: tuple[ParsedSection, ...]

@dataclass(frozen=True)
class ComparableDocument:
    schema_version: SchemaVersion
    origin: OriginProvenance
    artifacts: tuple[Artifact, ...]

@dataclass(frozen=True)
class ProfileDescriptor:
    profile_id: str
    profile_version: ProfileVersion
    api_version: Literal["1"]
    entrypoint: str
    module_sha256: Sha256
```

`SourceInput.repository_id` and `document_id` are populated from the repository identity authority defined below; a profile receives them but cannot derive or replace them.

All paths are resolved against `SourceInput.repo_root`; symlink resolution, absolute paths, and `..` escapes outside that root fail with `RAPTOR.PATH.OUTSIDE_ROOT`. Profile resolution is deterministic: an explicit `--profile-path` descriptor wins, then repository-local `.raptor/profiles/<profile-id>/profile.toml`, then the plugin built-in registry. Within the selected source, an exact requested version wins; otherwise a declared `1.x` constraint selects the highest compatible installed version. Duplicate same-precedence versions, constraint mismatch, API mismatch, entrypoint mismatch, or hash mismatch fail respectively with `RAPTOR.PROFILE.AMBIGUOUS`, `.VERSION`, `.API`, `.ENTRYPOINT`, or `.HASH`.

External profile code is trusted local code, never sandboxed implicitly. Loading repository-local or explicit profile code requires `--allow-profile-code`, validates descriptor/module paths and hash, uses no network discovery, and imports only after user trust is explicit. A consumer keeps its descriptor, module, and tests under its own `.raptor/profiles/`; Raptor receives the path at invocation and copies none of those assets into this repository or plugin bundle. `RAPTOR.PROFILE.UNTRUSTED` stops before import when trust is absent. Parse failures, invalid returned types, validation findings, and canonicalization failures use `RAPTOR.PROFILE.PARSE`, `.RETURN_TYPE`, `.VALIDATION`, and `.CANONICALIZE` without exposing tool traces or source secrets.

### Repository identity authority

Each source repository owns `.raptor/identity.json`; it is the only authority for assigning repository and document identity on Markdown import. It has this canonical shape:

```json
{
  "identity_version": "1.0.0",
  "repository_id": "urn:raptor:repo:raptor",
  "documents": {
    "DOC-RAP-001": {"path": "docs/requirements.md"}
  }
}
```

`repository_id` is immutable once registered. Document IDs and paths are unique within the manifest, paths use the repository-relative path grammar, and object keys serialize canonically. Neither repository nor document identity may be inferred from a path, clone URL, Git remote, directory name, content hash, or artifact ID. A clone carries the same committed identity manifest and therefore retains its keys even when its filesystem root changes.

A1 owns only the Pydantic model/generated JSON Schema, canonical serialization, conflict semantics, error-code contract, and Raptor dogfood model/schema tests for this manifest. It does not implement a registration CLI or filesystem mutation. The model defines `RAPTOR.IDENTITY.MISSING` when an operational caller has no manifest, idempotent acceptance of an identical tuple, `RAPTOR.IDENTITY.REPOSITORY_CONFLICT` for changing an existing repository ID, `RAPTOR.IDENTITY.DOCUMENT_CONFLICT` for binding one document ID to two paths, `RAPTOR.IDENTITY.PATH_CONFLICT` for binding two IDs to one path, and `RAPTOR.IDENTITY.REUSE` for reuse from another repository. It never invents an ID. A4 solely implements and tests `identity register --validate/--apply`; A5 composes the established operational identity support for its path-relocation workflow.

### Referential validation modes

Reference validation is explicit and never depends on an ambient repository:

| Mode | Resolution set and behavior |
|---|---|
| `structural` | Context-free validation of target discriminator, composite key grammar, and duplicate relationship shape only; target existence is not asserted. This is `validate_document`'s default and the JSON Schema boundary. |
| `document` | Resolve every artifact-bearing field (relationships, component dependencies, and test-case verification keys) against artifact keys in the one submitted `SourceDocument`; a target in another document or repository is unresolved even if it may exist elsewhere. |
| `batch` | Build the complete key set from all submitted documents before resolving, so forward references and cycles within a multi-document/multi-repository batch are valid. Duplicate composite keys fail before resolution. |
| `store` | Resolve against the submitted document/batch overlay plus the supplied `ArtifactResolver`; staged keys shadow the matching stored keys. A resolver is mandatory. |

An unresolved target produces `RAPTOR.REFERENCE.UNRESOLVED` with source `ArtifactKey`, relation, target `ArtifactKey`, selected mode, current `DocumentKey`/path, and JSON pointer or source location. Duplicate submitted keys use `RAPTOR.REFERENCE.DUPLICATE`. A1 tests cover a same-document reference in `document` mode, a forward cyclic batch in `batch` mode, a target supplied by a fake existing-store resolver in `store` mode, and a missing cross-repository target in every resolving mode. Structural mode must accept the last case while preserving its fully qualified target for a later boundary.

## Authoritative field, type, and constraint contract

The following is the executable minimum contract for A1. Pydantic models and generated schemas may add descriptions but may not rename, weaken, or silently add fields without re-hardening this plan.

### Scalar grammar and enums

These constants are normative executable patterns (the table below references them rather than relying on Markdown-escaped table text):

```python
SCHEMA_VERSION_RE = r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$"
REPOSITORY_ID_RE = r"^urn:raptor:repo:[a-z0-9][a-z0-9._-]{2,127}$"
DOCUMENT_ID_RE = r"^DOC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$"
ARTIFACT_ID_RE = r"^(REQ|NFR|ADR|DES|TST)-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$"
SHA256_RE = r"^[0-9a-f]{64}$"
EXTENSION_KEY_RE = r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+$"
PROFILE_ID_RE = r"^[a-z][a-z0-9_-]*$"
DIAGNOSTIC_CODE_RE = r"^[A-Z][A-Z0-9]*(\.[A-Z][A-Z0-9_]*)+$"
TEST_CASE_ID_RE = r"^TC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$"
```

| Type | Executable constraint |
|---|---|
| `SchemaVersion` | string matching `SCHEMA_VERSION_RE`; Phase A accepts major `1` only |
| `ProfileVersion` | semantic-version string matching the same grammar |
| `RepositoryId` | stable identity matching `REPOSITORY_ID_RE`; it is assigned once and does not change with clone URL, checkout, or rename |
| `DocumentId` | repository-scoped stable identity matching `DOCUMENT_ID_RE`; it does not change when the registered path changes |
| `ArtifactId` | string matching `ARTIFACT_ID_RE`; prefix must match `artifact_type` |
| `Title` | trimmed string, 1–200 Unicode scalar values |
| `NonEmptyText` | trimmed string, minimum length 1 |
| `Sha256` | lowercase hexadecimal string matching `SHA256_RE` |
| `ExtensionKey` | lowercase reverse-domain-style key matching `EXTENSION_KEY_RE` |
| `ArtifactType` | `requirement`, `non_functional_requirement`, `architecture_decision`, `design_document`, `test_plan` |
| `LifecycleStatus` | `draft`, `proposed`, `accepted`, `implemented`, `verified`, `deprecated`, `rejected`, `superseded` |
| `DiagnosticSeverity` | `error`, `warning`, `info` |
| `RelationshipType` | `depends_on`, `satisfies`, `implements`, `verifies`, `supersedes`, `relates_to` |
| `Priority` | `critical`, `high`, `medium`, `low` |

### Document, provenance, location, and diagnostics

| Model/field | Type and constraints | Required/omission |
|---|---|---|
| `SourceDocument.schema_version` | `SchemaVersion` | required |
| `SourceDocument.provenance` | `SourceProvenance(origin, materialization)` | required |
| `SourceDocument.artifacts` | ordered `list[Artifact]`, minimum 1; `(repository_id, artifact.id)` unique | required, never omitted |
| `OriginProvenance.repository_id` | `RepositoryId` | required; immutable |
| `OriginProvenance.document_id` | `DocumentId`, unique within repository | required; immutable |
| `OriginProvenance.initial_repository_path` | normalized repository-relative POSIX path; no absolute path, `.` or `..` segment | required; immutable |
| `OriginProvenance.original_content_sha256` | `Sha256` of first imported source bytes | required; immutable |
| `OriginProvenance.source_format` | literal `markdown` | required; immutable |
| `OriginProvenance.parser_profile`, `parser_profile_version` | `PROFILE_ID_RE`, `ProfileVersion` used for first import | required; immutable |
| `MaterializationProvenance.repository_path` | current normalized repository-relative output/input path | required; may change only through the A5 render-to-new-path transition |
| `MaterializationProvenance.content_sha256` | hash recomputed from current bytes | required |
| `MaterializationProvenance.operation` | `imported` or `rendered` | required |
| `MaterializationProvenance.parent_content_sha256` | prior materialization hash | required for `rendered`; omitted for first import |
| `MaterializationProvenance.parser_profile`, `parser_profile_version` | profile used to parse current bytes | required |
| `MaterializationProvenance.template_set`, `template_version` | render template identity | required for `rendered`; omitted for `imported` |
| `SourceLocation.start_line`, `start_column` | integer `>= 1` | required |
| `SourceLocation.end_line`, `end_column` | integer `>= 1`; end position must not precede start | optional as a pair; both omitted or both present |
| `Diagnostic.code` | uppercase dotted code matching `^[A-Z][A-Z0-9]*(\.[A-Z][A-Z0-9_]*)+$` | required |
| `Diagnostic.severity` | `DiagnosticSeverity` | required |
| `Diagnostic.message` | `NonEmptyText` | required |
| `Diagnostic.repository_id`, `document_id` | composite `DocumentKey` identifying the affected source | required |
| `Diagnostic.repository_path` | current materialization path grammar | required |
| `Diagnostic.location` | `SourceLocation` | optional; omit when `None` |
| `Diagnostic.artifact_key` | `ArtifactKey` | optional; omit when `None` |

### Shared artifact envelope and typed relationships

| Field | Type and constraints | Required/omission |
|---|---|---|
| `artifact_type` | `ArtifactType` discriminator | required |
| `id` | `ArtifactId`; family prefix must be `REQ`, `NFR`, `ADR`, `DES`, or `TST` respectively | required |
| `title` | `Title` | required |
| `status` | `LifecycleStatus` | required |
| `summary` | `NonEmptyText` | optional; omit when `None` |
| `relationships` | `list[ArtifactRelationship]`; duplicate `(relation, target_kind, target)` tuples forbidden | required, emit `[]` when empty |
| `extensions` | `dict[ExtensionKey, JsonValue]`; recursive values limited to JSON null/bool/number/string/array/object | required, emit `{}` when empty |
| `source_location` | `SourceLocation` locating the artifact within its source document | optional; omit when `None` |

Canonical identity is always composite: `DocumentKey = (repository_id, document_id)` and `ArtifactKey = (repository_id, artifact_id)`. The artifact envelope carries the repository-scoped `id`; its owning repository is `SourceDocument.provenance.origin.repository_id`. An `ArtifactRelationship` is a discriminated union with `relation`, optional `description`, and exactly one target:

- `ArtifactTarget(target_kind="artifact", repository_id, artifact_id)`, which must resolve to an `ArtifactKey` in the submitted database/import batch; or
- `UriTarget(target_kind="uri", target_uri)`, an absolute `https`, `http`, or `urn` URI.

There is no ambient/current-repository shortcut in canonical JSON: even same-repository artifact targets serialize `repository_id`. This prevents collisions when one database holds many repositories.

### Family payloads

| Family | Required payload | Optional payload and constraints |
|---|---|---|
| `Requirement` | `statement: NonEmptyText`; `acceptance_criteria: list[NonEmptyText]` with minimum 1 | `rationale: NonEmptyText | None`; `priority: Priority | None` |
| `NonFunctionalRequirement` | `statement: NonEmptyText`; `quality_attribute: str` matching `^[a-z][a-z0-9_-]*$`; `measurement: Measurement`; `acceptance_criteria: list[NonEmptyText]` with minimum 1 | `rationale: NonEmptyText | None`; `priority: Priority | None` |
| `ArchitectureDecision` | `context: NonEmptyText`; `decision: NonEmptyText`; `consequences: list[NonEmptyText]` with minimum 1 | `alternatives: list[NonEmptyText]`, emitted even when empty |
| `DesignDocument` | `overview: NonEmptyText`; `components: list[DesignComponent]` with minimum 1 | `interfaces: list[DesignInterface]`, emitted even when empty |
| `TestPlan` | `objective: NonEmptyText`; `scope: NonEmptyText`; `test_cases: list[TestCase]` with minimum 1 | `entry_criteria`, `exit_criteria`: `list[NonEmptyText]`, emitted even when empty |

Supporting payload types are fixed as follows.

`Measurement` uses strict Pydantic scalar types (`StrictStr`, `StrictInt`, `StrictFloat`, `StrictBool`); Python `bool` is never accepted as an integer. Comparator/target rules are authoritative:

| Comparator | Target shape | Allowed target types | Additional rule |
|---|---|---|---|
| `eq`, `ne` | scalar | strict string, integer, finite float, or boolean | `unit` allowed only for integer/float |
| `lt`, `lte`, `gt`, `gte` | scalar | strict integer or finite float | boolean/string rejected; `unit` optional |
| `range` | array of exactly two values | both strict integers or both finite floats | homogeneous type, boolean rejected, lower `<=` upper |

Every float must be finite; NaN and positive/negative infinity fail before canonicalization. Mixed integer/float ranges fail rather than coercing. Generated JSON Schema expresses comparator-dependent scalar/array shape, allowed JSON types, exact range length, and homogeneous range branches with `oneOf`/`if`/`then`. Pydantic-only validators enforce strict Python bool-versus-int distinction, finiteness, homogeneous runtime types, and lower/upper ordering; the schema/Python distinction is listed beside generated schemas and tested against shared cases.

- `Measurement` also requires `name: NonEmptyText` and optional `unit: NonEmptyText` under the matrix above.
- `DesignComponent`: `name: Title`, `responsibility: NonEmptyText`, `dependencies: list[ArtifactKey]`; dependencies are emitted even when empty and contain no duplicates.
- `DesignInterface`: `name: Title`, `description: NonEmptyText`, `participants: list[Title]` with minimum 2.
- `TestCase`: `id` matching `^TC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$`, `title: Title`, `steps: list[NonEmptyText]` with minimum 1, `expected_result: NonEmptyText`, and `verifies: list[ArtifactKey]` with minimum 1.

### Canonical ordering, unknown fields, and omission

- All models use `extra="forbid"`; unknown canonical fields fail validation.
- `SourceDocument.artifacts` and authorial lists (`acceptance_criteria`, consequences, alternatives, components, interfaces, test cases, steps, entry/exit criteria) preserve input/source order because order carries presentation or execution meaning.
- `relationships` serialize sorted by `(relation, target_kind, repository_id or "", artifact_id or "", target_uri or "")`; extension/object keys serialize lexicographically; set-like ID arrays serialize lexicographically after duplicate rejection.
- Canonical JSON uses UTF-8, sorted object keys, compact separators, and a single trailing newline. Strict integers and floats retain their JSON type; `-0.0` canonicalizes to `0.0`; finite floats use the shortest round-trippable decimal representation; NaN and infinities are rejected.
- Fields typed `T | None` are omitted when `None`. Required list/map fields are always emitted, including `[]`/`{}`. Defaults are emitted; no `exclude_defaults` serialization is allowed.
- The discriminator and family-ID prefix are validated together. Unsupported schema major versions, duplicate IDs, unresolved local references, invalid locations, and namespace violations fail before serialization.

### Origin and materialization transition/equality matrix

| Operation | Immutable origin | Materialization/output path | Hash behavior | Equality behavior |
|---|---|---|---|---|
| first import | create from repository identity, stable document ID, initial path/hash/profile | same path/hash, `operation=imported` | compute both hashes from input bytes | canonical artifacts and origin establish baseline |
| SQLite store/load | byte-identical model values | unchanged | no recomputation | full model equality required |
| render to same path | preserve origin byte-for-byte | requested path, `operation=rendered`, parent hash, template identity | compute new hash from atomically written bytes | artifact semantics and origin equal; materialization transition validated, not expected equal |
| render to new path | preserve origin including initial path | new repository-relative path registered for the same document by A5 | compute new hash; parent is prior hash | document/artifact composite keys unchanged; manifest binding and current path change together before normal store put |
| reparse rendered bytes | preserve serialized origin; reject attempted origin rewrite | current render path/profile and recomputed byte hash | recomputed hash must equal stored materialization hash | locations may be recomputed; artifact semantic fields, relationships, extensions, and origin must equal |

`source_location` and diagnostic locations are transport positions: after rendering they must be valid for the new bytes but need not equal the prior positions. Semantic comparison excludes only current materialization path/hash, operation/template fields, and transport locations from direct equality; it separately proves the transition rules above. Repository/document/artifact keys and immutable origin are never excluded.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A1-D1 | Raptor requirements/NFRs covering all `PA-REQ-*` and `PA-NFR-*` obligations, with stable `REQ-RAP-*` and `NFR-RAP-*` IDs and testable acceptance statements. | `docs/requirements.md` or indexed artifact directory |
| A1-D2 | `ADR-RAP-001` through `ADR-RAP-005`, including context, decision, alternatives, consequences, and enforceable architecture boundary rules. | `docs/adr/` and `docs/architecture.md` |
| A1-D3 | Executable five-family field/type/constraint matrix, source-profile protocol, diagnostic shape, and ownership matrix classifying canonical, provenance, relationship, presentation-only, and extension data. | this authoritative contract and generated-model mapping |
| A1-D4 | Raptor dogfood corpus manifest mapping every fixture/example to originating `REQ-RAP-*`, `NFR-RAP-*`, or `ADR-RAP-*` artifacts. | corpus manifest consumed by Phase A tests |
| A1-D5 | Installable `schema/` Pydantic v2 package with `SourceDocument`, provenance/location, typed references, shared envelope, and all five discriminated artifact families. | `schema/pyproject.toml`, `schema/src/raptor_schema/models/`, public exports |
| A1-D6 | Strict validation for schema version, IDs/types, duplicate IDs, four explicit reference modes, family fields, extension namespace, and unknown fields. | validators and `schema/tests/models/` |
| A1-D7 | Deterministic canonical JSON dump/load API and versioned JSON Schemas generated from Pydantic by one documented command. | `schema/src/raptor_schema/canonical.py`, `schema/json/v1/`, drift test |
| A1-D8 | Positive/negative tests derived only from the Raptor corpus, with origin artifact IDs recorded, plus compatibility documentation for external adapters. | `schema/tests/{models,json_schema}/` and package docs |
| A1-D9 | Concrete source-profile types, deterministic trusted discovery/loading/version contract, identity-manifest model/schema and conflict semantics, multi-repository composite identity, and origin/materialization transition rules. | public models/generated schema and model contract tests; no registration executable |
| A1-D10 | Raptor's own registered repository/document identities for its dogfood corpus and model/schema validation cases. | `.raptor/identity.json` mapped to Raptor `REQ-RAP-*`/`NFR-RAP-*`/`ADR-RAP-*` sources |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A1-AC1 | Every Phase A requirement has one Raptor artifact owner and acceptance statement; ADR-RAP-001..005 are accepted or explicitly superseded. |
| A1-AC2 | Every model field maps one-to-one to the authoritative field/type/constraint matrix, including lifecycle, typed relationships, locations, diagnostics, extensions, grammar, ordering, and omission rules; no consumer-specific field is present. |
| A1-AC3 | `Diagnostic`, `SourceLocation`, provenance, and relationship positive/negative cases exercise every listed structural and cross-field constraint. |
| A1-AC4 | Valid representative instances of all five family payloads validate through `SourceDocument` and round-trip through canonical JSON with the specified ordering and omission behavior. |
| A1-AC5 | Invalid discriminator/prefix, version, ID, duplicate, reference, location, relationship target, extension namespace, unknown field, ordering duplicate, and family constraint each produce deterministic validation errors. |
| A1-AC6 | Generated schemas accept/reject the same committed cases as Pydantic for JSON-Schema-expressible constraints; Python-only cross-record checks are documented. |
| A1-AC7 | Schema generation is deterministic and CI detects drift between `schema/src/` and `schema/json/v1/`. |
| A1-AC8 | Every fixture resolves through the corpus manifest to Raptor `REQ-RAP-*`, `NFR-RAP-*`, or `ADR-RAP-*`; no generic or external-consumer fixture is present. |
| A1-AC9 | `schema/pyproject.toml` declares supported Python/Pydantic versions, installs in a clean environment, exposes consumer-neutral calls, and requires neither SQLite nor Rust. |
| A1-AC10 | Product paths contain no `NFT`, P3-specific artifact identifier, `p3-documentation` asset, or Rust SQLx dependency. |
| A1-AC11 | Two repositories may use the same local artifact/document IDs without collision; all references, diagnostics, comparisons, and serialization retain the stable repository namespace. |
| A1-AC12 | Measurement cases cover every comparator/type cell, mixed/homogeneous ranges, bool-versus-int, finite/non-finite floats, canonical numeric output, and the documented JSON Schema/Python validation split. |
| A1-AC13 | Profile resolution tests cover precedence, exact/major version selection, ambiguity, API/entrypoint/hash mismatch, root/symlink escapes, explicit trust, and a temporary consumer-owned profile outside Raptor assets. |
| A1-AC14 | Provenance tests prove immutable origin preservation and every materialization transition, including same/new output paths, recomputed hashes, parent hash, template identity, and transport-location inequality. |
| A1-AC15 | The structural/document/batch/store reference API has deterministic mode-specific tests for same-document resolution, batch cycles, existing-store resolution, and missing cross-repository targets with fully qualified diagnostics. |
| A1-AC16 | Model/schema tests prove `.raptor/identity.json` shape, canonical serialization, stable IDs independent of clone/root path, identical-tuple idempotence, repository/document/path conflict and reuse diagnostics, missing-manifest diagnostic contract, and Raptor dogfood validity; A1 contains no register CLI or filesystem-mutation test. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/models schema/tests/json_schema
python -m pytest schema/tests/models -k 'field_contract or identity or reference_mode or measurement or provenance or profile or ordering or omission or relationship or diagnostic or location'
python -m raptor_schema.generate --check --output schema/json/v1
git diff --exit-code -- schema/json/v1
rg -n 'REQ-RAP-|NFR-RAP-|ADR-RAP-' docs/requirements.md docs/architecture.md docs/adr
python -m json.tool .raptor/identity.json >/dev/null
rg -n '\bNFT\b|p3-documentation|REQ-P3-|NFR-P3-|ADR-P3-|REQ-GEN-|NFR-GEN-|ADR-GEN-' schema docs/requirements.md docs/architecture.md docs/adr && exit 1 || true
rg -n 'sqlx' Cargo.toml crates && exit 1 || true
```

Manual review verifies field classification, decision alternatives, traceability, and fixture origins. Final paths must match the declared `schema/` layout; the PR may refine only module filenames below those boundaries.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A1-D1, A1-D2 | PA-REQ-001, PA-NFR-001, PA-NFR-002, PA-NFR-003 |
| A1-D3 | PA-REQ-002, PA-REQ-004, PA-NFR-005 |
| A1-D4, A1-D8 | PA-REQ-009, PA-NFR-001, PA-NFR-002 |
| A1-D5, A1-D6 | PA-REQ-001, PA-REQ-002, PA-NFR-005 |
| A1-D7 | PA-REQ-003, PA-NFR-004 |
| A1-D9 | PA-REQ-002, PA-REQ-004, PA-NFR-001, PA-NFR-004, PA-NFR-005 |
| A1-D10 | PA-REQ-002, PA-REQ-009, PA-NFR-004 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Combining contract and models encourages premature code | approve REQ/NFR/ADR inventory and ADR decisions before finalizing model fields within the same PR. |
| One giant permissive model hides family errors | use a discriminated union with family-specific required fields and forbid unknown canonical fields. |
| Checked-in schemas become a second authority | generate only from models and enforce a no-diff drift test. |
| Consumer conventions leak through examples | admit only corpus entries mapped to Raptor-owned identifiers and repository-neutral vocabulary. |
| Cross-record Pydantic rules are not expressible in JSON Schema | document the distinction and test both layers against the same cases. |

## Non-closure

- No Markdown parser or executable consumer profile.
- No SQLite DDL, storage adapter, or `schema/sql/` directory.
- No plugin manifest, runtime script, or sc-compose template.
- No external-consumer fixture, adapter, or compatibility suite.
- No Dolt/MySQL or Rust SQLx implementation.

## Handoff to A2

A2 starts only after A1 is pushed and merged forward. It consumes the public validation/dump/load API, generated schema version, source/provenance contract, and Raptor fixtures. It may not recreate model fields in a persistence DTO. Any missing model behavior is corrected in A1 before A2 continues.
