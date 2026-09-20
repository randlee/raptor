# Sprint A1 — Canonical Contract, Pydantic Models, and JSON Schema

## Objective

Freeze the Phase A artifact contract in Raptor's own REQ/NFR/ADR documents, then publish a small Python contract for canonical JSON covering all five artifact families, source provenance, references, versioning, deterministic serialization, and generated JSON Schema.

- Branch: `phase-a/01-models-and-json-schema`
- Stack relation: root sprint, `must_follow develop`
- PR base/stack root: `develop`

## Scope boundary

This sprint owns the semantic contract and its executable representation under top-level `schema/`. Raptor-owned REQ/NFR/ADR artifacts are normative inputs and the only origin for examples. Models validate canonical JSON, not a consumer's Markdown conventions. Persistence, plugin packaging, and Markdown rendering remain later closures. `NFR` is canonical and `NFT` is invalid.

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

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A1-D1 | Raptor requirements/NFRs covering all `PA-REQ-*` and `PA-NFR-*` obligations, with stable `REQ-RAP-*` and `NFR-RAP-*` IDs and testable acceptance statements. | `docs/requirements.md` or indexed artifact directory |
| A1-D2 | `ADR-RAP-001` through `ADR-RAP-005`, including context, decision, alternatives, consequences, and enforceable architecture boundary rules. | `docs/adr/` and `docs/architecture.md` |
| A1-D3 | Canonical vocabulary, five-family field inventory, source-profile protocol, diagnostic shape, and ownership matrix classifying canonical, provenance, relationship, presentation-only, and extension data. | public contract documentation |
| A1-D4 | Raptor dogfood corpus manifest mapping every fixture/example to originating `REQ-RAP-*`, `NFR-RAP-*`, or `ADR-RAP-*` artifacts. | corpus manifest consumed by Phase A tests |
| A1-D5 | Installable `schema/` Pydantic v2 package with `SourceDocument`, provenance/location, typed references, shared envelope, and all five discriminated artifact families. | `schema/pyproject.toml`, `schema/src/raptor_schema/models/`, public exports |
| A1-D6 | Strict validation for schema version, IDs/types, duplicate IDs, references, family fields, extension namespace, and unknown fields. | validators and `schema/tests/models/` |
| A1-D7 | Deterministic canonical JSON dump/load API and versioned JSON Schemas generated from Pydantic by one documented command. | `schema/src/raptor_schema/canonical.py`, `schema/json/v1/`, drift test |
| A1-D8 | Positive/negative tests derived only from the Raptor corpus, with origin artifact IDs recorded, plus compatibility documentation for external adapters. | `schema/tests/{models,json_schema}/` and package docs |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A1-AC1 | Every Phase A requirement has one Raptor artifact owner and acceptance statement; ADR-RAP-001..005 are accepted or explicitly superseded. |
| A1-AC2 | The field inventory covers all five families, classifies every field, and leaves no consumer-specific behavior inside the canonical domain. |
| A1-AC3 | Source-profile diagnostics define stable code, severity, message, repository-relative path, and optional location/artifact ID fields. |
| A1-AC4 | Valid representative instances of all five families validate through `SourceDocument` and round-trip through canonical JSON without semantic change. |
| A1-AC5 | Invalid discriminator, unsupported schema version, malformed ID, duplicate artifact ID, unresolved local reference, invalid extension namespace, and unknown canonical field each produce deterministic validation errors. |
| A1-AC6 | Generated schemas accept/reject the same committed cases as Pydantic for JSON-Schema-expressible constraints; Python-only cross-record checks are documented. |
| A1-AC7 | Schema generation is deterministic and CI detects drift between `schema/src/` and `schema/json/v1/`. |
| A1-AC8 | Every fixture resolves through the corpus manifest to Raptor `REQ-RAP-*`, `NFR-RAP-*`, or `ADR-RAP-*`; no generic or external-consumer fixture is present. |
| A1-AC9 | `schema/pyproject.toml` declares supported Python/Pydantic versions, installs in a clean environment, exposes consumer-neutral calls, and requires neither SQLite nor Rust. |
| A1-AC10 | Product paths contain no `NFT`, P3-specific artifact identifier, `p3-documentation` asset, or Rust SQLx dependency. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/models schema/tests/json_schema
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
