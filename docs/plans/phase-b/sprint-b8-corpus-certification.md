# Sprint B8 — Full-Corpus Certification and Validate Activation

## Objective and stack

Compose Phase A routes and B1–B7 evidence into a complete non-mutating
full-corpus certification workflow and activate validate mode through the
existing public round-trip route.

- `gh-stack` branch: `phase-b/08-corpus-certification`
- Relation: `must_follow B7`
- Merge-forward: merge pushed B7 development before every B8 development/fix round; B7 PR merges first.
- Parallel safety: not `parallel_safe`; B8 is the sole certification decision point and B9 consumes its exact record.

## Certification contract

```python
class CertificationPredicate(Model):
    name: Literal[
        "reconciliation", "revision", "input_compatibility",
        "staged_compatibility", "apply_plan_binding",
    ]
    evidence_sha256: Sha256
    passed: bool

class MigrationCertification(Model):
    certification_version: Literal["1.0.0"]
    certification_id: EvidenceId
    operation_id: OperationId
    repository_id: RepositoryId
    operation_mode: Literal["validate", "apply"]
    operation_input_sha256: Sha256
    trust_policy_sha256: Sha256
    ledger_sha256: Sha256
    reconciliation_result_sha256: Sha256
    apply_plan_sha256: Sha256
    input_revision: str
    input_tree_sha256: Sha256
    staged_tree_sha256: Sha256
    final_tree_inventory_sha256: Sha256
    filesystem_mutations_sha256: Sha256
    tool_bundle_set_sha256: Sha256
    gate_workspace_set_sha256: Sha256
    compatibility_evidence_ids: tuple[EvidenceId, ...]
    upstream_receipt_sha256: Sha256
    predicates: tuple[CertificationPredicate, ...]
    diagnostics: tuple[Diagnostic, ...]
    certified_at: AwareDatetime | None
    verdict: Literal["certified", "rejected", "stale"]

class ValidationResult(Model):
    result_version: Literal["1.0.0"]
    operation_id: OperationId
    prepared_mode: Literal["validate", "apply"]
    certification: MigrationCertification
    ledger_path: RepositoryPath
    evidence_directory: RepositoryPath
    stage_root: RepositoryPath
    success: bool

def certify_migration(
    operation: MigrationOperationInput, ledger: ReconciliationLedger,
    reconciliation: ReconciliationResult, apply_plan: CorpusApplyPlan,
    compatibility: tuple[CompatibilityEvidence, ...],
) -> tuple[ReconciliationLedger, MigrationCertification]: ...
def validate_migration(
    repository_root: Path, operation_input: RepositoryPath,
) -> ValidationResult: ...
```

Predicate order is the literal order shown; compatibility IDs sort by corpus
role then trust-policy tool order. `certified` requires all predicates true,
zero diagnostics, and `certified_at`; `rejected` requires at least one false
predicate and diagnostics; later binding drift creates `stale`. Verdict
transitions are one-way `certified -> stale`; rejected/stale records cannot be
re-certified. A rerun creates a new operation/certification. The certification
digest covers all fields including verdict, ordered filesystem puts/deletes,
exact final-tree inventory, tool-bundle/workspace sets, and evidence IDs. A
staged-tree digest alone never authorizes deletion.

Certification returns a newly serialized ledger in `certified`, `rejected`, or
`stale` state together with the matching certification; it never mutates or
silently repairs the B7 ledger. A certified result appends the B1
`certification` receipt whose immediate predecessor is the exact
`compatibility_staged` receipt and whose digest is also recorded in
`MigrationCertification.upstream_receipt_sha256`. Rejected/stale results emit no certification
receipt. Before deciding, B8 reconstructs every input/staged effective workspace
layout from policy and bound trees and requires its version/digest to equal the
corresponding evidence; an absent or mismatched layout binding fails closed.

`validate_migration` accepts either declared intent but is always non-mutating.
For `validate`, it produces a reviewable certification. For `apply`, it reruns
the complete B1–B7 pipeline and produces a distinct apply-mode certification
whose operation-input digest includes `mode="apply"`; B9 requires that exact
unchanged input and certification. It writes only generated operation-state
stage/evidence and never changes source, selected identity, or target SQLite.
The existing
`/raptor:round-trip migration` route and `migration-round-trip` agent call this
shared runtime through the existing runner. `migrate_corpus.py` accepts only
repository root and the literal operation-input path, performs no apply mutation
for either declared intent, serializes the standard envelope, and maps exit
status.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B8-D1 | Complete `MigrationCertification`, predicate, `ValidationResult`, and sole-producer certification-receipt behavior plus verifier. |
| B8-D2 | Non-mutating shared validate orchestration composing existing routes and B1–B7 runtimes. |
| B8-D3 | Existing `/raptor:round-trip migration` agent/router activation for validate mode with identical Claude/Codex behavior. |
| B8-D4 | Validate-only thin `migrate_corpus.py` wrapper and wrapper-thinness enforcement. |
| B8-D5 | Raptor-owned full-corpus validate suite plus temporary neutral external-repository public-hook test. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B8-AC1 | Validate completes all five families, cross-document references, byte units, canonical/SQLite proof, lineage, projection/reparse, exact reconciliation, revision, and input/output gates without target mutation. |
| B8-AC2 | Certification succeeds only with complete current B1–B7 records, exact ordered compatibility receipts, 100% reconciliation, matching Git revision, zero-warning input/output gates, and exact apply-plan bindings for ordered filesystem puts/deletes, final-tree inventory, tool bundles, and effective gate workspaces. |
| B8-AC3 | Every certification field, operation mode, fixed predicate/evidence/receipt ordering, certification-receipt input/output/count/evidence/predecessor binding, put/delete/final-tree/bundle/effective-workspace digest link, and legal/illegal verdict transition has direct tests; changing any upstream byte/digest or omitting a split/combine deletion yields rejected or stale, never certified. |
| B8-AC4 | Validate and apply intent both stop after certification in B8 and have no journal, replacement, SQLite target-write, or recovery behavior; their operation-input/certification digests differ. |
| B8-AC5 | A temporary neutral repository supplies its own profile, templates, operation inputs, validator/build bundle, and corpus; Raptor packages none of its names/assets. |
| B8-AC6 | Claude and Codex resolve the unchanged `/raptor:round-trip` command to the same agent/runtime; plugin/schema/template/vendor inventories remain hash-aligned. |

## Required validation

```sh
python -m pytest schema/tests/migration plugins/raptor/tests/migration/test_certification.py plugins/raptor/tests/migration/test_full_corpus_validate.py
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
python plugins/raptor/scripts/validate_plugin.py --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0'
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
```

The repository operation fixture has mode `validate`; apply-mode certification
is tested only in a temporary repository. Neither can replace content in B8.

## Traceability and non-closure

- B8-D1–D5 own non-mutating PB-REQ-005 certification/validate activation and NFR-RAP-008 full-chain evidence verification.
- No apply, source/identity/target-SQLite replacement, journal mutation/recovery, production external migration, Rust CLI/SQLx, Dolt/MySQL, remote gate, or fleet orchestration.

## Handoff

B9 receives only a current apply-mode `certified` record and its exact immutable
`CorpusApplyPlan`. It may reverify and apply those bindings but may not rerun,
repair, or refresh certification.
