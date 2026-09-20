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

class SourceProvenance(BaseModel):
    repository_path: str
    source_format: Literal["markdown"]
    parser_profile: str
    parser_profile_version: str
    content_sha256: str
    location: SourceLocation | None = None

class SourceDocument(BaseModel):
    schema_version: str
    provenance: SourceProvenance
    artifacts: list[Artifact]

def validate_document(value: object) -> SourceDocument: ...
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

## Authoritative field, type, and constraint contract

The following is the executable minimum contract for A1. Pydantic models and generated schemas may add descriptions but may not rename, weaken, or silently add fields without re-hardening this plan.

### Scalar grammar and enums

These constants are normative executable patterns (the table below references them rather than relying on Markdown-escaped table text):

```python
SCHEMA_VERSION_RE = r"^[1-9][0-9]*\.[0-9]+\.[0-9]+$"
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
| `SourceDocument.provenance` | `SourceProvenance` | required |
| `SourceDocument.artifacts` | ordered `list[Artifact]`, minimum 1; IDs unique within document | required, never omitted |
| `SourceProvenance.repository_path` | normalized repository-relative POSIX path; no absolute path, `.` or `..` segment | required |
| `SourceProvenance.source_format` | literal `markdown` | required |
| `SourceProvenance.parser_profile` | lowercase identifier matching `^[a-z][a-z0-9_-]*$` | required |
| `SourceProvenance.parser_profile_version` | `ProfileVersion` | required |
| `SourceProvenance.content_sha256` | `Sha256` of source bytes | required |
| `SourceProvenance.location` | `SourceLocation` for whole document | optional; omit when `None` |
| `SourceLocation.start_line`, `start_column` | integer `>= 1` | required |
| `SourceLocation.end_line`, `end_column` | integer `>= 1`; end position must not precede start | optional as a pair; both omitted or both present |
| `Diagnostic.code` | uppercase dotted code matching `^[A-Z][A-Z0-9]*(\.[A-Z][A-Z0-9_]*)+$` | required |
| `Diagnostic.severity` | `DiagnosticSeverity` | required |
| `Diagnostic.message` | `NonEmptyText` | required |
| `Diagnostic.repository_path` | same path grammar as provenance | required |
| `Diagnostic.location` | `SourceLocation` | optional; omit when `None` |
| `Diagnostic.artifact_id` | `ArtifactId` | optional; omit when `None` |

### Shared artifact envelope and typed relationships

| Field | Type and constraints | Required/omission |
|---|---|---|
| `artifact_type` | `ArtifactType` discriminator | required |
| `id` | `ArtifactId`; family prefix must be `REQ`, `NFR`, `ADR`, `DES`, or `TST` respectively | required |
| `title` | `Title` | required |
| `status` | `LifecycleStatus` | required |
| `summary` | `NonEmptyText` | optional; omit when `None` |
| `relationships` | `list[ArtifactRelationship]`; duplicate `(relation, target_id, target_uri)` tuples forbidden | required, emit `[]` when empty |
| `extensions` | `dict[ExtensionKey, JsonValue]`; recursive values limited to JSON null/bool/number/string/array/object | required, emit `{}` when empty |
| `source_location` | `SourceLocation` locating the artifact within its source document | optional; omit when `None` |

`ArtifactRelationship` has required `relation: RelationshipType` and exactly one of `target_id: ArtifactId` or absolute `target_uri` using `https`, `http`, or `urn`. A local `target_id` must resolve within the submitted document unless the relationship also declares `external: true`; `external` defaults to `false` and is emitted. `description: NonEmptyText | None` is optional and omitted when `None`.

### Family payloads

| Family | Required payload | Optional payload and constraints |
|---|---|---|
| `Requirement` | `statement: NonEmptyText`; `acceptance_criteria: list[NonEmptyText]` with minimum 1 | `rationale: NonEmptyText | None`; `priority: Priority | None` |
| `NonFunctionalRequirement` | `statement: NonEmptyText`; `quality_attribute: str` matching `^[a-z][a-z0-9_-]*$`; `measurement: Measurement`; `acceptance_criteria: list[NonEmptyText]` with minimum 1 | `rationale: NonEmptyText | None`; `priority: Priority | None` |
| `ArchitectureDecision` | `context: NonEmptyText`; `decision: NonEmptyText`; `consequences: list[NonEmptyText]` with minimum 1 | `alternatives: list[NonEmptyText]`, emitted even when empty |
| `DesignDocument` | `overview: NonEmptyText`; `components: list[DesignComponent]` with minimum 1 | `interfaces: list[DesignInterface]`, emitted even when empty |
| `TestPlan` | `objective: NonEmptyText`; `scope: NonEmptyText`; `test_cases: list[TestCase]` with minimum 1 | `entry_criteria`, `exit_criteria`: `list[NonEmptyText]`, emitted even when empty |

Supporting payload types are fixed as follows:

- `Measurement`: `name: NonEmptyText`, `comparator: Literal["eq", "ne", "lt", "lte", "gt", "gte", "range"]`, `target: str | int | float | bool | list[str | int | float | bool]`, and optional `unit: NonEmptyText`; `range` requires exactly two ordered target values and other comparators require a scalar.
- `DesignComponent`: `name: Title`, `responsibility: NonEmptyText`, `dependencies: list[ArtifactId]`; dependencies are emitted even when empty and contain no duplicates.
- `DesignInterface`: `name: Title`, `description: NonEmptyText`, `participants: list[Title]` with minimum 2.
- `TestCase`: `id` matching `^TC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$`, `title: Title`, `steps: list[NonEmptyText]` with minimum 1, `expected_result: NonEmptyText`, and `verifies: list[ArtifactId]` with minimum 1.

### Canonical ordering, unknown fields, and omission

- All models use `extra="forbid"`; unknown canonical fields fail validation.
- `SourceDocument.artifacts` and authorial lists (`acceptance_criteria`, consequences, alternatives, components, interfaces, test cases, steps, entry/exit criteria) preserve input/source order because order carries presentation or execution meaning.
- `relationships` serialize sorted by `(relation, target_id or "", target_uri or "")`; extension/object keys serialize lexicographically; set-like ID arrays serialize lexicographically after duplicate rejection.
- Canonical JSON uses UTF-8, sorted object keys, compact separators, and a single trailing newline. Numbers use JSON numeric form; NaN and infinities are rejected.
- Fields typed `T | None` are omitted when `None`. Required list/map fields are always emitted, including `[]`/`{}`. Defaults are emitted; no `exclude_defaults` serialization is allowed.
- The discriminator and family-ID prefix are validated together. Unsupported schema major versions, duplicate IDs, unresolved local references, invalid locations, and namespace violations fail before serialization.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A1-D1 | Raptor requirements/NFRs covering all `PA-REQ-*` and `PA-NFR-*` obligations, with stable `REQ-RAP-*` and `NFR-RAP-*` IDs and testable acceptance statements. | `docs/requirements.md` or indexed artifact directory |
| A1-D2 | `ADR-RAP-001` through `ADR-RAP-005`, including context, decision, alternatives, consequences, and enforceable architecture boundary rules. | `docs/adr/` and `docs/architecture.md` |
| A1-D3 | Executable five-family field/type/constraint matrix, source-profile protocol, diagnostic shape, and ownership matrix classifying canonical, provenance, relationship, presentation-only, and extension data. | this authoritative contract and generated-model mapping |
| A1-D4 | Raptor dogfood corpus manifest mapping every fixture/example to originating `REQ-RAP-*`, `NFR-RAP-*`, or `ADR-RAP-*` artifacts. | corpus manifest consumed by Phase A tests |
| A1-D5 | Installable `schema/` Pydantic v2 package with `SourceDocument`, provenance/location, typed references, shared envelope, and all five discriminated artifact families. | `schema/pyproject.toml`, `schema/src/raptor_schema/models/`, public exports |
| A1-D6 | Strict validation for schema version, IDs/types, duplicate IDs, references, family fields, extension namespace, and unknown fields. | validators and `schema/tests/models/` |
| A1-D7 | Deterministic canonical JSON dump/load API and versioned JSON Schemas generated from Pydantic by one documented command. | `schema/src/raptor_schema/canonical.py`, `schema/json/v1/`, drift test |
| A1-D8 | Positive/negative tests derived only from the Raptor corpus, with origin artifact IDs recorded, plus compatibility documentation for external adapters. | `schema/tests/{models,json_schema}/` and package docs |

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

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/models schema/tests/json_schema
python -m pytest schema/tests/models -k 'field_contract or ordering or omission or relationship or diagnostic or location'
python -m raptor_schema.generate --check --output schema/json/v1
git diff --exit-code -- schema/json/v1
rg -n 'REQ-RAP-|NFR-RAP-|ADR-RAP-' docs/requirements.md docs/architecture.md docs/adr
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
