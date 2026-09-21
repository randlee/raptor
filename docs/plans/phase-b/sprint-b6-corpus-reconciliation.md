# Sprint B6 — Corpus Reconciliation

## Objective and stack

Replay every proof through B5, require exactly 100% accounting, and freeze the
reconciled output/identity/database changes as an immutable apply plan.

- `gh-stack` branch: `phase-b/06-corpus-reconciliation`
- Relation: `must_follow B5`
- Merge-forward: merge pushed B5 development before every B6 development/fix round; B5 PR merges first.
- Parallel safety: not `parallel_safe`; B6 consumes every prior receipt and produces B7's exact staged tree and reconciled ledger.

## Reconciliation contract

```python
class SourceBytesResolver(Protocol):
    def read(
        self, *, document_key: DocumentKey, repository_path: RepositoryPath,
        expected_sha256: Sha256,
    ) -> bytes: ...

class AuthorityResolver(Protocol):
    def read_path(
        self, *, repository_path: RepositoryPath, expected_sha256: Sha256,
    ) -> bytes: ...
    def read_evidence(
        self, *, evidence_id: EvidenceId, expected_sha256: Sha256,
    ) -> JsonValue: ...

def reconcile_corpus(
    ledger: ReconciliationLedger, *, source_bytes: SourceBytesResolver,
    authority_inputs: AuthorityResolver,
) -> ReconciliationResult: ...
def prepare_apply_plan(
    result: ReconciliationResult, *, stage_root: RepositoryPath,
) -> CorpusApplyPlan: ...
```

Resolvers may read only paths/IDs already present in the validated B2 snapshot
or B1 derivation records. They reject symlinks, control/state paths, unexpected
file type/size/hash, undeclared evidence, and any lookup whose composite key and
path disagree. They have no ambient repository/store fallback and perform no
writes.

```python
class PredicateResult(Model):
    predicate: Literal[
        "byte_coverage", "unit_disposition", "canonical_authority",
        "persistence", "projection", "render_reparse", "provenance", "lineage",
    ]
    passed: bool
    numerator: NonNegativeInt
    denominator: PositiveInt
    receipt_sha256: Sha256

class ReconciliationResult(Model):
    result_version: Literal["1.0.0"]
    operation_id: OperationId
    ledger_sha256: Sha256
    operation_input_sha256: Sha256
    declared_input_revision: str
    input_tree_sha256: Sha256
    staged_tree_sha256: Sha256
    predicates: tuple[PredicateResult, ...]
    diagnostics: tuple[Diagnostic, ...]
    status: Literal["reconciled", "rejected", "stale"]

class StageEntry(Model):
    repository_path: RepositoryPath
    byte_length: NonNegativeInt
    content_sha256: Sha256

class SQLiteMutation(Model):
    action: Literal["put", "delete"]
    document_key: DocumentKey
    expected_before_sha256: Sha256 | None
    after_sha256: Sha256 | None
    canonical_json: str | None

class CorpusApplyPlan(Model):
    plan_version: Literal["1.0.0"]
    operation_id: OperationId
    operation_input_sha256: Sha256
    reconciliation_result_sha256: Sha256
    ledger_sha256: Sha256
    declared_input_revision: str
    input_tree_sha256: Sha256
    staged_tree_sha256: Sha256
    stage_root: RepositoryPath
    stage_entries: tuple[StageEntry, ...]
    identity_path: RepositoryPath
    identity_before_sha256: Sha256
    identity_after_sha256: Sha256
    identity_stage_sha256: Sha256
    database_path: RepositoryPath
    database_before_sha256: Sha256 | None
    sqlite_mutations: tuple[SQLiteMutation, ...]
    status: Literal["ready", "stale"]
```

Predicate results appear once in the literal order shown and `reconciled`
requires every `passed=true` with numerator equal to denominator. Diagnostics
sort by document/path/code/pointer and are empty only for `reconciled`.
`stage_entries` sort by path and exactly cover the staged tree. SQLite mutations
sort by `DocumentKey`; `put` requires `after_sha256` and canonical JSON while
`delete` requires both absent; `expected_before_sha256` is omitted only for a
new document. The identity stage bytes hash to `identity_stage_sha256` and equal
the proposed B4 `after_manifest_sha256`. `ready -> stale` is the only plan state
transition; stale plans are immutable and never become ready again.

Reconciliation treats `input_revision` as the declared, not yet tool-verified,
binding and recomputes every other available receipt. It replays byte partitions,
transformations, derivations, canonical/SQLite equality, projection consumption,
render/reparse provenance, and lineage. Success requires every independent
predicate owned through B6 to equal exactly 100%; partial percentages are never
rounded. B7 later verifies the revision and adds compatibility predicates.

`prepare_apply_plan` writes only below the operation state root. It freezes the
exact staged output inventory/tree digest, proposed IdentityManifest 2.0 bytes,
and idempotent SQLite put/delete set, all linked to the reconciled ledger. It is
not authorization and exposes no source replacement. Any later byte or digest
change invalidates the plan.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B6-D1 | Exact reconciliation runtime replaying byte, unit, authority, persistence, projection, reparse, provenance, and lineage predicates. |
| B6-D2 | Deterministic diagnostic set for every failed predicate and stale/reordered/missing receipt. |
| B6-D3 | Immutable operation-state stage containing output tree, identity bytes, SQLite mutation set, and their digests. |
| B6-D4 | Versioned `CorpusApplyPlan` that binds stage, identity transition, database receipt, ledger, and operation inputs without applying them. |
| B6-D5 | Positive and adversarial reconciliation/stage mutation suite. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B6-AC1 | Reconciliation succeeds only when byte coverage, dispositions, canonical authority, persistence, leaf recovery, provenance transitions, and lineage are each exactly 100%. |
| B6-AC2 | Missing, stale, reordered, duplicated, or mutated source/authority/receipt/lineage/render values produce stable path-qualified failures and no target mutation. |
| B6-AC3 | The staged tree contains exactly the B5 output inventory and bytes; stages/backups/control data are excluded from its canonical tree digest. |
| B6-AC4 | Proposed identity bytes and SQLite mutation set agree exactly with B4 lineage and preserve unrelated records; no path-only move exists. |
| B6-AC5 | Validate-mode stage creation changes no source Markdown, selected identity file, or target SQLite database and is idempotent for the same operation/digests. |
| B6-AC6 | Changing any staged byte or apply-plan binding invalidates reconciliation and cannot be repaired without a new upstream run. |
| B6-AC7 | B6 records the declared revision in the result/apply plan but invokes no Git executable and produces no revision evidence; only B7 may perform that verification. |
| B6-AC8 | Resolver tests reject every undeclared key/path/evidence lookup, symlink/control path, and hash mismatch; result/apply-plan tests cover all required fields, fixed predicate/mutation/inventory ordering, put/delete shape, exact digest bindings, and irreversible ready-to-stale transition. |

## Required validation

```sh
python -m pytest schema/tests/migration plugins/raptor/tests/migration/test_reconciliation.py plugins/raptor/tests/migration/test_apply_plan.py
python -m pytest schema/tests/storage plugins/raptor/tests/provenance
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
rg -n 'move_document|path_only_move' schema/src plugins/raptor/runtime && exit 1 || true
```

## Traceability and non-closure

- B6-D1–D5 close PB-REQ-004 and REQ-RAP-015 through immutable reconciled-stage scope.
- No source/identity/target-database apply, recovery journal execution, migration CLI/agent activation, compatibility gate, certification, consumer asset, Rust CLI/SQLx, or Dolt/MySQL.

## Handoff

B7 receives an immutable staged tree, apply plan, and reconciled ledger. It runs
compatibility gates against those exact bytes and cannot regenerate, repair,
rerender, or remap them.
