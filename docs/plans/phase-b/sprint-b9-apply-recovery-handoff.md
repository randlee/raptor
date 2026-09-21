# Sprint B9 — Certified Apply, Recovery, and Pilot Handoff

## Objective and stack

Apply only a current B8 certification through a bounded journal, prove restart
recovery, and publish the consumer-owned pilot handoff.

- `gh-stack` branch: `phase-b/09-apply-recovery-handoff`
- Relation: `must_follow B8`
- Merge-forward: merge pushed B8 development before every B9 development/fix round; B8 PR merges first.
- Parallel safety: not `parallel_safe`; B9 alone mutates certified output, identity, and target SQLite state.

## Apply and recovery contract

```python
class JournalState(str, Enum):
    PREPARED = "prepared"
    OUTPUTS_COMMITTING = "outputs_committing"
    OUTPUTS_COMMITTED = "outputs_committed"
    IDENTITY_COMMITTED = "identity_committed"
    DB_PENDING = "db_pending"
    COMPLETE = "complete"
    ROLLED_BACK = "rolled_back"
    CONFLICT = "conflict"

class JournalPathEntry(Model):
    final_path: RepositoryPath
    stage_path: RepositoryPath
    backup_path: RepositoryPath
    before_absent: bool
    before_sha256: Sha256 | None
    after_sha256: Sha256
    byte_length: NonNegativeInt
    committed: bool

class MigrationJournal(Model):
    journal_version: Literal["1.0.0"]
    operation_id: OperationId
    certification_sha256: Sha256
    apply_plan_sha256: Sha256
    ledger_sha256: Sha256
    input_revision: str
    input_tree_sha256: Sha256
    staged_tree_sha256: Sha256
    output_entries: tuple[JournalPathEntry, ...]
    identity_entry: JournalPathEntry
    database_path: RepositoryPath
    sqlite_mutations_sha256: Sha256
    state: JournalState

class ApplyRecoveryResult(Model):
    result_version: Literal["1.0.0"]
    operation_id: OperationId
    certification_sha256: Sha256
    apply_plan_sha256: Sha256
    prior_state: JournalState | None
    final_state: JournalState
    applied_output_paths: tuple[RepositoryPath, ...]
    identity_sha256: Sha256 | None
    database_sha256: Sha256 | None
    diagnostics: tuple[Diagnostic, ...]
    status: Literal["applied", "recovered", "pending", "rolled_back", "conflict"]

def apply_certified_migration(
    repository_root: Path, operation_input: RepositoryPath,
    certification: MigrationCertification,
) -> ApplyRecoveryResult: ...
def recover_migration(
    repository_root: Path, operation_id: OperationId,
) -> ApplyRecoveryResult: ...
```

`JournalPathEntry` requires `before_sha256` exactly when `before_absent=false`;
stage/backup paths must be the operation-scoped siblings of `final_path` and
cannot alias another entry. Entries sort by
final path. State transitions are only:
`prepared -> outputs_committing -> outputs_committed -> identity_committed -> db_pending -> complete`;
pre-identity failures may transition to `rolled_back`; hash/state ambiguity at
any point transitions to terminal `conflict`. Recovery from identity-committed
or db-pending rolls forward; completed/rolled-back/conflict journals are
terminal. Result output paths sort; hashes are required for applied/recovered,
database may be absent only while pending/rolled back, and diagnostics are
required for pending/rolled-back/conflict.

Before the journal starts, apply calls B7's `verify_current_revision` API and
rechecks the returned Git revision evidence, input/staged
trees, trust/tool bytes, certification, apply plan, identity transition, and
database before hash. It replaces each certified output at its own rename
boundary in sorted order, then the selected identity file, then idempotent
SQLite puts/deletes. It never claims cross-resource atomicity or performs a
path-only move. Recovery cannot alter operation inputs or create a new plan.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B9-D1 | Complete migration journal, path-entry, and apply/recovery result contracts with state validation. |
| B9-D2 | Certified apply runtime extending the existing bounded journal across output set, selected identity, and SQLite mutation plan. |
| B9-D3 | Restart recovery, idempotent SQLite retry/delete, rollback/roll-forward, lock, stale, and conflict handling. |
| B9-D4 | Apply/recover route/CLI behavior through the existing agent/runtime; scripts remain thin. |
| B9-D5 | Failure-injection suite and consumer-owned pilot preparation/review/apply/recover handoff documentation. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B9-AC1 | Apply accepts only an unchanged mode-`apply` operation input plus its current B8 apply-mode `certified` record whose complete digest chain and target before-state reverify immediately before mutation, including a fresh call to B7's sole revision-verification API. A validate-mode certification is never reusable for apply. |
| B9-AC2 | Journal/result tests cover every required field, ordered path inventory, legal/illegal state transition, result status, omission rule, stale binding, and conflict diagnostic. |
| B9-AC3 | Only certified staged bytes are installed; the selected IdentityManifest 2.0 transition and exact B6 SQLite mutation set follow in documented order. |
| B9-AC4 | Failure injection before/after every marker and rename proves pre-identity rollback, post-identity roll-forward, db-pending retry, completed replay idempotence, lock exclusion, and terminal conflict without guessing. |
| B9-AC5 | The apply/recovery wrapper and existing agent contain no transformation, certification, registry, journal-policy, or database logic outside shared runtime. |
| B9-AC6 | Operator docs keep all consumer profiles/templates/tool bundles/fixtures/scripts in the consumer repository and require evidence review plus explicit mode change before apply. |
| B9-AC7 | No production external migration occurs in Raptor CI, and no Rust CLI/SQLx, Dolt/MySQL, remote gate, service, or fleet orchestration is introduced. |

## Required validation

```sh
python -m pytest plugins/raptor/tests/migration/test_apply.py plugins/raptor/tests/migration/test_recovery.py plugins/raptor/tests/recovery
python -m pytest plugins/raptor/tests/migration/test_full_corpus_apply.py
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
python plugins/raptor/scripts/validate_plugin.py --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
```

All apply/recovery tests use temporary repositories; no repository-root apply
command appears in the validation block.

## Traceability and non-closure

- B9-D1–D5 close PB-REQ-005 / REQ-RAP-016 apply enforcement and NFR-RAP-008 recovery/audit behavior.
- No Raptor-owned consumer asset or production pilot execution; the handoff is a neutral contract only.
- No Rust CLI/SQLx, Dolt/MySQL, remote attestation, synchronization service, or fleet orchestration.

## Phase handoff

After B9, a consumer prepares its repository-local assets, runs B8 with validate
intent, and reviews the certification. To apply, it creates an apply-mode
operation input and reruns B8 non-mutating certification; B9 consumes that exact
unchanged input/certification and provides recovery by operation ID. Later fleet
or Dolt work must consume these contracts without weakening them.
