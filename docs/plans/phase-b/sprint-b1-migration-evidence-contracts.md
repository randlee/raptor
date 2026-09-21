# Sprint B1 — Migration Evidence Contracts

## Objective and stack

Publish the executable, consumer-neutral data contract that every later migration boundary must emit and verify.

- `gh-stack` branch: `phase-b/01-migration-evidence-contracts`
- Relation: root sprint; `must_follow develop`
- PR base: `develop`
- Parallel safety: not parallel-safe with B2; B2 consumes these exact types and generated schemas.

## Contract

Add authoritative Pydantic models under `schema/src/raptor_schema/migration/`, public exports, generated v1 JSON Schemas, and model/schema tests. Generated files are exactly `source-content-unit.schema.json`, `reconciliation-ledger.schema.json`, `corpus-lineage.schema.json`, `migration-operation-input.schema.json`, `migration-trust-policy.schema.json`, and `compatibility-evidence.schema.json`. All models forbid unknown fields, accept only supported exact versions, serialize with the existing canonical encoder, and use lowercase SHA-256.

The signatures in this section are the sole field authority. Tables below add
cross-field constraints; later sprints consume these types and may not redeclare
partial or runtime-only variants.

```python
class DerivationRecord(Model):
    target_pointer: JsonPointer
    kind: Literal["configuration", "identity", "source_digest", "generated"]
    authority_path: RepositoryPath | None = None
    authority_evidence_id: EvidenceId | None = None
    authority_sha256: Sha256
    rule_id: RuleId
    rule_version: ExactVersion
    target_value_digest: Sha256

class ReconciliationLedger(Model):
    ledger_version: Literal["1.0.0"]
    repository_id: RepositoryId
    operation_id: OperationId
    operation_input_sha256: Sha256
    trust_policy_sha256: Sha256
    input_revision: str
    input_tree_sha256: Sha256
    sources: tuple[SourceRecord, ...]
    units: tuple[UnitRecord, ...]
    derivations: tuple[DerivationRecord, ...]
    boundary_receipts: tuple[BoundaryReceipt, ...]
    lineage: CorpusLineage | None = None
    staged_tree_sha256: Sha256 | None = None
    compatibility_evidence: tuple[EvidenceId, ...]
    status: Literal["open", "reconciled", "certified", "rejected", "stale"]
```

### Authoritative field and nested-type matrix

All models use `extra="forbid"`. `ExactVersion` is a three-component semantic
version with supported major `1`; `OperationId` matches
`[a-z0-9][a-z0-9._-]{2,127}`; `EvidenceId` and `RuleId` match
`[a-z][a-z0-9._-]{2,127}`; `ToolId` and `AuthorityId` use that same grammar;
`JsonPointer` is empty for the document root or an
RFC 6901 pointer with valid `~0`/`~1` escaping. Every digest is lowercase
SHA-256. `AbsoluteToolPath` is a normalized absolute no-follow regular-file path
recorded after resolution; it is never interpreted relative to the repository.
`AbsoluteToolDirectory` is the equivalent no-follow directory-root type.
Tuples marked non-empty have `min_length=1`; all other tuple fields are required
and emit `[]` when empty. Optional values are omitted when `None`.

| Model | Required fields and constraints | Ordering / omission |
|---|---|---|
| `SourceContentUnit` | `unit_id`, `document_key`, `source_sha256`, `start_byte >= 0`, `end_byte > start_byte`, `kind`, `byte_sha256`, `content_bearing` | units sort by document path then bounds; no optional fields |
| `TransformationRecord` | non-empty unique `source_unit_ids`; `transform_id`, exact `transform_version`, `normalized_source_digest`, `target_pointer`, `target_value_digest` | unit IDs sort by source bounds; records sort by target pointer then rule ID |
| `DerivationRecord` | `target_pointer`, `kind`, `authority_path` xor `authority_evidence_id`, `authority_sha256`, `rule_id`, exact `rule_version`, `target_value_digest` | records sort by target pointer; exactly one authority selector |
| `CanonicalDisposition` | discriminator `disposition="canonical"`; non-empty `transformations`; every target pointer is outside `/artifacts/*/extensions` | transformations use the ordering above |
| `PreservedDisposition` | discriminator `disposition="preserved"`; non-empty `transformations`; every pointer targets a valid namespaced extension | transformations use the ordering above |
| `RejectedDisposition` | discriminator `disposition="rejected"`; `diagnostic_code`; no transformation fields | never valid in reconciled/certified ledger |
| `UnitRecord` | `unit: SourceContentUnit`; exactly one discriminated `disposition` | ordered by source path/bounds |
| `SourceRecord` | `document_key`, `repository_path`, `content_sha256`, `byte_length >= 0`, ordered unique `unit_ids`, `source_name`, `profile_id`, exact `profile_version`, `profile_sha256` | sources sort by path; `unit_ids` preserve byte order |
| `BoundaryReceipt` | `stage`, `receipt_version`, `upstream_receipt_sha256`, `input_sha256`, `output_sha256`, `record_count >= 0`, `evidence_ids` | fixed stage order below; first receipt omits only `upstream_receipt_sha256`; evidence IDs sort |

`BoundaryStage` is exactly `ingress`, `accounting`, `canonical_import`,
`sqlite_import`, `sqlite_export`, `lineage`, `projection`, `render`, `reparse`,
`reconciliation`, `compatibility_input`, `compatibility_staged`, and
`certification`. A receipt may consume only its immediate predecessor; stages
cannot repeat, skip a required predecessor, or follow certification.

The final three receipts have fixed ownership and bindings. Every named digest
below is the lowercase SHA-256 of canonical JSON; evidence tuples use policy
order and the receipt itself is appended after its output exists.

| Stage | Sole producer | `upstream_receipt_sha256` | `input_sha256` | `output_sha256`, count, evidence IDs |
|---|---|---|---|---|
| `compatibility_input` | B7 | digest of the `reconciliation` receipt | array of ledger-before digest, input-tree digest, policy digest, input effective-workspace digests, and tool-bundle-set digest | digest of the ordered input-role evidence records; count equals their length; IDs are exactly those records |
| `compatibility_staged` | B7 | digest of the `compatibility_input` receipt | array of ledger-after-input digest, staged-tree digest, policy digest, staged effective-workspace digests, and tool-bundle-set digest | digest of the ordered staged-role evidence records; count equals their length; IDs are exactly those records |
| `certification` | B8 | digest of the `compatibility_staged` receipt | array of final B7 ledger, reconciliation-result, apply-plan, and complete compatibility-evidence-set digests | digest of the `MigrationCertification`; count equals the fixed certification predicate count; IDs contain only `certification_id` |

B7 appends both compatibility receipts and B8 appends the certification receipt
to newly serialized ledgers. B8 and B9 reject a missing, duplicated, reordered,
or substituted receipt, predecessor, evidence ID, count, input, or output digest.

| Lineage model | Required fields and constraints | Ordering / transition |
|---|---|---|
| `DocumentLineage` | `input_keys` non-empty unique, `output_key`, `output_path`, `primary_input_key` contained in inputs, non-empty unique `contributing_origins` matching inputs | sorted by `output_key`; input keys/origins sort by composite key |
| `ArtifactLineage` | `input_key`, `output_key`; keys must be equal in Phase B; `input_document_key`, `output_document_key` | sorted by input artifact key; each input appears exactly once |
| `RetiredDocument` | `document_id`, `last_path`, non-empty `replacement_document_ids`, `operation_id`, `ledger_sha256` | replacements sort; retirement is irreversible |
| `IdentityTransition` | `before_manifest_sha256`, `after_manifest_sha256`, `active_documents`, `retired_documents` | maps serialize by document ID; active/retired sets are disjoint; v1→v2 or v2→v2 only |
| `CorpusLineage` | `lineage_version`, `operation_id`, non-empty `documents`, non-empty `artifacts`, `identity_transition` | documents/artifacts use the order above; total input coverage and artifact bijection required |

| Operation/trust model | Required fields and constraints | Ordering / omission |
|---|---|---|
| `MigrationOperationInput` | exact fields from the phase-plan table; `repository_manifest` and `trust_policy_path` are literals; `staging_root`, `ledger_path`, and `evidence_directory` must equal the paths derived from `operation_id`; `lineage_path` optional | unknown fields fail; `lineage_path` omitted for generated one-to-one |
| `ToolBundle` | `bundle_version`, `source`, `root`, non-empty `members`, relative `entrypoint`, non-empty `version_argv`, exact `expected_version_stdout`, `bundle_sha256` | members sort by path; entrypoint occurs exactly once; no members are optional |
| `GateWorkspaceInput` | `source_path`, `workspace_path`, `role`, `byte_length`, `content_sha256` | inputs sort by workspace path; source/workspace paths are unique |
| `TrustTool` | `role`, `tool_id`, exact `tool_version`, `bundle`, optional interpreter pair, exact non-empty `argv`, `working_directory_role`, environment map, `workspace_inputs`, `workspace_inputs_sha256` | policy order is authorial invocation order; interpreter omitted for native executable; environment keys and workspace inputs sort |
| `MigrationTrustPolicy` | `policy_version`, `authority_id`, non-empty `tools`; exactly one revision tool and at least one validator/site-build tool | duplicate role/tool IDs fail; tools retain declared order |
| `CompatibilityEvidence` | `evidence_version`, `evidence_id`, `operation_id`, `corpus_role`, `policy_sha256`, authority/tool identity, bundle/inventory/entrypoint/version-verification digests, `workspace_sha256`, normalized argv/environment/working-directory bindings, revision/tree bindings, UTC times, result counts/digests, `upstream_receipt_sha256` | `staged_tree_sha256` omitted only for input role; times must be ordered; results sort by corpus role then policy tool order |

The public operation/trust/evidence signatures are exact, not illustrative:

```python
class TemplateSetSelection(Model):
    name: str  # [a-z][a-z0-9_-]{0,63}
    version: ExactVersion
    manifest_sha256: Sha256

class MigrationOperationInput(Model):
    operation_version: Literal["1.0.0"]
    operation_id: OperationId
    mode: Literal["validate", "apply"]
    input_revision: str
    repository_manifest: Literal[".raptor/raptor.toml"]
    database_path: RepositoryPath
    reference_mode: Literal["batch", "store"]
    staging_root: RepositoryPath
    template_set: TemplateSetSelection  # name, exact version, manifest_sha256
    trust_policy_path: Literal[".raptor/operation-input/trust-policy.json"]
    lineage_path: RepositoryPath | None = None
    ledger_path: RepositoryPath
    evidence_directory: RepositoryPath

class ToolBundleMember(Model):
    path: RepositoryPath
    byte_length: NonNegativeInt
    content_sha256: Sha256
    role: Literal["entrypoint", "support"]

class ToolBundle(Model):
    bundle_version: Literal["1.0.0"]
    source: Literal["repository", "absolute"]
    root: RepositoryPath | AbsoluteToolDirectory
    members: tuple[ToolBundleMember, ...]
    entrypoint: RepositoryPath
    version_argv: tuple[str, ...]
    expected_version_stdout: str
    bundle_sha256: Sha256

class GateWorkspaceInput(Model):
    source_path: RepositoryPath
    workspace_path: RepositoryPath
    role: Literal["configuration", "support", "fixture"]
    byte_length: NonNegativeInt
    content_sha256: Sha256

class TrustTool(Model):
    role: Literal["revision", "validator", "site_build"]
    tool_id: ToolId
    tool_version: ExactVersion
    bundle: ToolBundle
    interpreter_path: AbsoluteToolPath | None = None
    interpreter_sha256: Sha256 | None = None
    argv: tuple[str, ...]
    working_directory_role: Literal["repository_root", "staging_root"]
    environment: dict[str, str]
    workspace_inputs: tuple[GateWorkspaceInput, ...]
    workspace_inputs_sha256: Sha256

class MigrationTrustPolicy(Model):
    policy_version: Literal["1.0.0"]
    authority_id: AuthorityId
    tools: tuple[TrustTool, ...]

class CompatibilityEvidence(Model):
    evidence_version: Literal["1.0.0"]
    evidence_id: EvidenceId
    operation_id: OperationId
    corpus_role: Literal["input", "staged"]
    policy_sha256: Sha256
    authority_id: AuthorityId
    tool_role: Literal["revision", "validator", "site_build"]
    tool_id: ToolId
    tool_version: ExactVersion
    tool_bundle_source: Literal["repository", "absolute"]
    tool_bundle_root: RepositoryPath | AbsoluteToolDirectory
    tool_bundle_sha256: Sha256
    tool_bundle_inventory_sha256: Sha256
    entrypoint: RepositoryPath
    entrypoint_sha256: Sha256
    version_verification_sha256: Sha256
    interpreter_path: AbsoluteToolPath | None = None
    interpreter_sha256: Sha256 | None = None
    argv_sha256: Sha256
    environment_sha256: Sha256
    workspace_layout_version: Literal["1.0.0"]
    workspace_sha256: Sha256
    working_directory_role: Literal["repository_root", "staging_root"]
    input_revision: str
    input_tree_sha256: Sha256
    staged_tree_sha256: Sha256 | None = None
    started_at: AwareDatetime
    ended_at: AwareDatetime
    exit_status: int
    error_count: NonNegativeInt
    warning_count: NonNegativeInt
    stdout_sha256: Sha256
    stderr_sha256: Sha256
    upstream_receipt_sha256: Sha256
```

`argv` is non-empty and every string is non-empty, exact, and placeholder-free.
Interpreter path/digest are present or omitted together. `store` mode requires
an existing target database. All operation-derived state paths must match
`operation_id`; `lineage_path`, when present, stays below
`.raptor/operation-input/` and is required for split/combine.

`ToolBundle.root` is selected by the tagged `source`: `repository` requires a
normalized repository-relative root outside `.git/` and generated state;
`absolute` requires `AbsoluteToolDirectory`. Inventory walks the root without
following links and must equal `members` exactly—missing, extra, substituted,
non-regular, duplicate, or escaping members fail. `bundle_sha256` hashes the
canonical array `[path, byte_length, content_sha256, role]`. The entrypoint is a
relative member with role `entrypoint`. Version verification executes the copied
entrypoint with exactly `version_argv`, empty stdin, the policy environment, and
no shell; success requires exit zero, empty stderr, and stdout bytes equal to
UTF-8 `expected_version_stdout`. `version_verification_sha256` binds command,
expected/actual output, and result.

Gate auxiliary inputs are explicit policy data, never authorized-corpus members.
Each no-follow regular source is copied to its distinct relative
`workspace_path`; their canonical `[workspace_path, role, byte_length,
content_sha256]` array hashes to `workspace_inputs_sha256`. A gate execution's
effective layout is the sorted canonical array containing every corpus-overlay
file as `[path, "corpus", byte_length, content_sha256]`, every auxiliary input
as `[workspace_path, "auxiliary:<role>", byte_length, content_sha256]`, and the
reserved entry `["scratch/", "scratch", 0, null]`. `workspace_sha256` hashes
`["1.0.0", corpus_role, bound_tree_sha256, effective_layout]`, distinguishing
the exact input and staged overlays. Auxiliary paths must be unique and
pairwise ancestor/descendant-disjoint from one another, every corpus-overlay
path, and reserved `scratch/`; corpus paths also cannot equal or descend from
`scratch/`. Validation occurs before any directory or file is materialized.
Paths under `.git/`,
`.raptor/state/`, operation stages, backups, and destinations are forbidden.

`ReconciliationLedger` has no implicit fields: it requires `ledger_version`,
`repository_id`, `operation_id`, `operation_input_sha256`, `trust_policy_sha256`,
`input_revision`, `input_tree_sha256`, ordered non-empty `sources`, ordered
`units`, ordered `derivations`, ordered `boundary_receipts`, optional `lineage`,
optional `staged_tree_sha256`, ordered `compatibility_evidence`, and
`status`. Status ownership is exact: B2 constructs `open`; B3–B5 may replace
ledger content while preserving `open`; B6 alone performs successful
`open -> reconciled`; B7 may replace compatibility evidence/receipts while
preserving `reconciled`; and B8 alone produces every terminal ledger mutation.
The complete legal transition set is B6 `open -> reconciled`, B8
`open -> rejected|stale`, B8 `reconciled -> certified|rejected|stale`, and B8
`certified -> stale`. No other transition or status producer is legal.
`lineage` is omitted until B4 and required from `reconciled` onward; units are
empty only before B3. `staged_tree_sha256` is required from `reconciled` onward;
compatibility IDs are empty in `open`, may be populated in `reconciled`, and are non-empty in
`certified`. `rejected` and `stale` are terminal—rerun creates a new
ledger/operation ID. B6 rejection/staleness and B7 gate failure are typed outcome
records with diagnostics, not ledger statuses: they return the input ledger
unchanged for B8 to finalize. B8 terminalizes a failed open/reconciled ledger or
certifies a successful reconciled ledger through its sole public transition API.
Every downstream digest consumes the canonical digest of the complete prior ledger.

`UnitRecord.disposition` is the union above. Unit IDs use the exact array formula
in the migration requirements. Lists with authorial meaning retain order;
set-like projections use the explicit sort keys above and reject duplicates.

The operation-input and trust-policy fields are exactly those in the [phase plan](plan-phase-b.md#exact-operation-input-boundary). B1 also models the proposed identity transition and `IdentityManifest` version `2.0.0`, including disjoint active outputs and irreversible retired input IDs, without implementing filesystem mutation. Version 1 loads as an empty retired set. Compatibility evidence binds policy hash, authority, bundle source/inventory, entrypoint/version proof, optional interpreter, workspace, argv/environment/working-directory/stdin, input/staged trees, timing, exit status, warning/error counts, and stdout/stderr digests.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B1-D1 | Versioned Pydantic models and public APIs for units, dispositions, transformation/derivation records, receipts, ledger, lineage, identity transition, operation input, tool bundles, gate workspaces, trust policy, and compatibility evidence. |
| B1-D2 | Generated JSON Schemas under `schema/json/v1/` and drift enforcement from the models. |
| B1-D3 | Canonical digest/order/omission rules and validators for interval shape, pointer namespaces, unique authority, lineage totality, policy roles, exact argv, effective workspace layouts, final receipt ownership, and state transitions. |
| B1-D4 | Raptor-owned fixtures and mutation tests covering every union branch and version rejection. |
| B1-D5 | Vendored schema refresh and plugin inventory update, with no runtime migration behavior. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B1-AC1 | Every model round-trips through deterministic Pydantic JSON and its generated schema; regeneration produces no diff. |
| B1-AC2 | Unit IDs, tree digests, argument digests, canonical leaf digests, ordering, omission, finite-number handling, and negative-zero normalization match the requirements byte-for-byte. |
| B1-AC3 | Dispositions enforce exactly one branch; accepted-ledger validation rejects unsupported/rejected units, absent pointers, duplicate authority, broken receipt ordering, and non-100% predicates. |
| B1-AC4 | Lineage validates total input-document coverage, exactly-one artifact destination, explicit contributing origins, caller-supplied new IDs, retired-ID non-reuse, and an identity transition digest. |
| B1-AC5 | The loader accepts only `.raptor/operation-input/migration.json` and its literal `.raptor/operation-input/trust-policy.json`; the operation state paths derive only from `operation_id`. Validate/apply, reference mode, database, template, lineage, ledger, and evidence fields cannot be inferred. |
| B1-AC6 | Trust policy requires exactly one Git revision resolver plus at least one exact validator and site-build tool, complete no-follow bundle/workspace inventories, relative entrypoints, deterministic version verification, exact versions/digests/argv/working-directory roles, and a closed environment allowlist. Tests reject missing/extra/substituted/escaping members, undeclared workspace inputs, and unknown/floating/shell-like values. Identity model tests prove v1 read compatibility and the v2 active/retired disjointness, irreversible-retirement, and no-reuse rules. |
| B1-AC7 | Models remain consumer-neutral and import no parser, plugin runtime, database driver, template engine, subprocess API, external-consumer package, Rust, or Dolt dependency. |
| B1-AC8 | Field-matrix tests cover every required/optional field, discriminator, cardinality, ordering rule, digest link, version rejection, all three final receipt producers/input-output/count/evidence/predecessor bindings, the exact B2/B6/B7/B8 status-owner matrix and every legal/illegal ledger transition, and effective-layout equality/ancestor/descendant/scratch collisions before materialization. |

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

- B1-D1–D5 and B1-AC1–AC8 satisfy PB-REQ-001 and establish NFR-RAP-008 evidence syntax.
- No repository traversal, Markdown parser changes, transformation execution, SQLite write, rendering, external command, or apply behavior.
- No Rust CLI, Dolt/MySQL, remote attestation, consumer asset, or fleet operation.

## Handoff

B2 receives installable models, generated schemas, canonical hash helpers, and the exact operation-input contract. Any missing evidence field is corrected in B1 before B2 continues; B2 may not create runtime-only shadow DTOs.
