# Sprint B1 — Migration Evidence Contracts

## Objective and stack

Publish the executable, consumer-neutral data contract that every later migration boundary must emit and verify.

- `gh-stack` branch: `phase-b/01-migration-evidence-contracts`
- Relation: root sprint; `must_follow develop`
- PR base: `develop`
- Parallel safety: not parallel-safe with B2; B2 consumes these exact types and generated schemas.

## Contract

Add authoritative Pydantic models under `schema/src/raptor_schema/migration/`, public exports, generated v1 JSON Schemas, and model/schema tests. Generated files are exactly `source-content-unit.schema.json`, `reconciliation-ledger.schema.json`, `corpus-lineage.schema.json`, `migration-operation-input.schema.json`, `migration-trust-policy.schema.json`, and `compatibility-evidence.schema.json`. All models forbid unknown fields, accept only supported exact versions, serialize with the existing canonical encoder, and use lowercase SHA-256.

```python
class ContentUnitKind(str, Enum):
    FRONTMATTER = "frontmatter"; HEADING = "heading"; PARAGRAPH = "paragraph"
    LIST = "list"; TABLE = "table"; FENCED_CODE = "fenced_code"
    THEMATIC_BREAK = "thematic_break"; LINK_DEFINITION = "link_definition"
    HTML_COMMENT = "html_comment"; BLANK_SEPARATOR = "blank_separator"
    UNSUPPORTED = "unsupported"

class SourceContentUnit(Model):
    unit_id: Sha256; document_key: DocumentKey; source_sha256: Sha256
    start_byte: NonNegativeInt; end_byte: PositiveInt
    kind: ContentUnitKind; byte_sha256: Sha256; content_bearing: bool

class TransformationRecord(Model):
    source_unit_ids: tuple[Sha256, ...]
    transform_id: RuleId; transform_version: ExactVersion
    normalized_source_digest: Sha256; target_pointer: JsonPointer
    target_value_digest: Sha256

class DerivationRecord(Model):
    target_pointer: JsonPointer
    kind: Literal["configuration", "identity", "source_digest", "generated"]
    authority: RepositoryPath | EvidenceId; authority_sha256: Sha256
    rule_id: RuleId; rule_version: ExactVersion; target_value_digest: Sha256

class CorpusLineage(Model):
    lineage_version: ExactVersion; operation_id: OperationId
    documents: tuple[DocumentLineage, ...]
    artifacts: tuple[ArtifactLineage, ...]
    identity_transition: IdentityTransition

class ReconciliationLedger(Model):
    ledger_version: ExactVersion; repository_id: RepositoryId
    operation_input_sha256: Sha256; input_revision: str; input_tree_sha256: Sha256
    sources: tuple[SourceRecord, ...]; units: tuple[UnitRecord, ...]
    derivations: tuple[DerivationRecord, ...]; boundary_receipts: tuple[BoundaryReceipt, ...]
    lineage: CorpusLineage; staged_tree_sha256: Sha256 | None
    compatibility_evidence: tuple[EvidenceId, ...]; status: Literal["open", "reconciled", "certified"]

class MigrationOperationInput(Model): ...
class MigrationTrustPolicy(Model): ...
class CompatibilityEvidence(Model): ...
```

`UnitRecord.disposition` is a discriminated union: `canonical` and `preserved` require non-empty replayable transformations to canonical or namespaced-extension pointers; `rejected` requires a stable diagnostic code and can never appear in an accepted import. Unit IDs use the exact array formula in the migration requirements. Sources are ordered by path, units by `(path,start_byte,end_byte)`, lineage by composite key, tools by declared policy order, and receipts by fixed pipeline stage. Lists with authorial meaning retain order; set-like collections reject duplicates and canonicalize by documented keys.

The operation-input and trust-policy fields are exactly those in the [phase plan](plan-phase-b.md#exact-operation-input-boundary). B1 also models the proposed identity transition and `IdentityManifest` version `2.0.0`, including disjoint active outputs and irreversible retired input IDs, without implementing filesystem mutation. Version 1 loads as an empty retired set. Compatibility evidence binds policy hash, authority, tool/bundle/executable/interpreter identities, argv/environment/working-directory/stdin bindings, input revision/tree, staged tree, timing, exit status, warning/error counts, and stdout/stderr digests.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B1-D1 | Versioned Pydantic models and public APIs for units, dispositions, transformation/derivation records, receipts, ledger, lineage, identity transition, operation input, trust policy, and compatibility evidence. |
| B1-D2 | Generated JSON Schemas under `schema/json/v1/` and drift enforcement from the models. |
| B1-D3 | Canonical digest/order/omission rules and validators for interval shape, pointer namespaces, unique authority, lineage totality, policy roles, exact argv, and state transitions. |
| B1-D4 | Raptor-owned fixtures and mutation tests covering every union branch and version rejection. |
| B1-D5 | Vendored schema refresh and plugin inventory update, with no runtime migration behavior. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B1-AC1 | Every model round-trips through deterministic Pydantic JSON and its generated schema; regeneration produces no diff. |
| B1-AC2 | Unit IDs, tree digests, argument digests, canonical leaf digests, ordering, omission, finite-number handling, and negative-zero normalization match the requirements byte-for-byte. |
| B1-AC3 | Dispositions enforce exactly one branch; accepted-ledger validation rejects unsupported/rejected units, absent pointers, duplicate authority, broken receipt ordering, and non-100% predicates. |
| B1-AC4 | Lineage validates total input-document coverage, exactly-one artifact destination, explicit contributing origins, caller-supplied new IDs, retired-ID non-reuse, and an identity transition digest. |
| B1-AC5 | Operation input accepts only the two documented `.raptor/operation-input/` files and constrained repository-root paths; validate/apply, reference mode, staging, database, template, lineage, ledger, and evidence fields cannot be inferred. |
| B1-AC6 | Trust policy requires exactly one Git revision resolver plus at least one exact validator and site-build tool, exact versions/digests/argv/working-directory roles, and a closed environment allowlist; unknown/floating/shell-like values fail. |
| B1-AC7 | Models remain consumer-neutral and import no parser, plugin runtime, database driver, template engine, subprocess API, external-consumer package, Rust, or Dolt dependency. |

## Required validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest schema/tests/migration schema/tests/json_schema
python -m mypy --strict schema/src/raptor_schema schema/tests/typing/protocol_contract.py
python -m raptor_schema.generate --check --output schema/json/v1
python plugins/raptor/scripts/vendor_schema.py --check
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
rg -n '\bNFT\b|sqlx|dolt://' schema/src/raptor_schema/migration schema/tests/migration && exit 1 || true
```

## Traceability and non-closure

- B1-D1–D5 satisfy PB-REQ-001 and establish NFR-RAP-008 evidence syntax.
- No repository traversal, Markdown parser changes, transformation execution, SQLite write, rendering, external command, or apply behavior.
- No Rust CLI, Dolt/MySQL, remote attestation, consumer asset, or fleet operation.

## Handoff

B2 receives installable models, generated schemas, canonical hash helpers, and the exact operation-input contract. Any missing evidence field is corrected in B1 before B2 continues; B2 may not create runtime-only shadow DTOs.
