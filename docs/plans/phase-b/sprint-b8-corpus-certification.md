# Sprint B8 — Full-Corpus Certification

## Objective and stack

Compose the existing Phase A routes and B1–B7 evidence into the complete
one-time migration validate/apply/recover workflow and external-consumer handoff.

- `gh-stack` branch: `phase-b/08-corpus-certification`
- Relation: `must_follow B7`
- Merge-forward: merge pushed B7 development before every B8 development/fix round; B7 PR merges first.
- Parallel safety: not `parallel_safe`; B8 is the sole final decision and mutation point for every upstream record.

## Certification contract

```python
def certify_migration(
    operation: MigrationOperationInput, ledger: ReconciliationLedger,
    compatibility: tuple[CompatibilityEvidence, ...],
) -> MigrationCertification: ...
def execute_migration(
    repository_root: Path, operation_input: RepositoryPath,
) -> MigrationResult: ...
```

`execute_migration` is the one public runtime entry point. The operation input's
`mode` is authoritative: `validate` runs the complete pipeline and emits a
certification candidate without changing source, selected identity, or target
SQLite; `apply` accepts only a current certified ledger/evidence chain. It
rechecks every upstream digest, exact revision/tree, staged tree, trust policy,
tool evidence, proposed identity transition, and database receipt. Drift returns
a stable stale/conflict error and never silently refreshes evidence.

Apply extends the existing journal to replace the B6 output set and selected
identity file at their own rename boundaries, then performs ordinary idempotent
SQLite puts/deletes. Marker states bind the complete file inventory/hashes,
identity transition, database receipt, certification, and ledger. Recovery rolls
back before identity commit and rolls forward afterward; path-only moves remain
forbidden.

The existing `/raptor:round-trip migration` route and focused
`migration-round-trip` agent call this shared runtime through the existing
runner. `migrate_corpus.py` only parses repository root and the literal operation
input path, serializes the standard envelope, and maps exit status. Recovery is
an explicit `--recover <operation-id>` wrapper action over the same journal; it
cannot create a new migration or change operation inputs.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B8-D1 | Full-chain certification verifier and versioned `MigrationCertification`. |
| B8-D2 | Shared validate/apply orchestration plus existing-journal extension and bounded restart recovery. |
| B8-D3 | Existing `/raptor:round-trip migration` agent/router activation with identical Claude/Codex behavior. |
| B8-D4 | Thin `migrate_corpus.py` operation/recovery wrapper and wrapper-thinness enforcement. |
| B8-D5 | Raptor-owned end-to-end corpus plus temporary neutral external-repository public-hook test. |
| B8-D6 | Operator documentation for preparation, evidence review, apply/recovery, and consumer-owned pilot handoff. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B8-AC1 | Validate mode completes all five families, cross-document references, byte units, canonical/SQLite proof, lineage, projection/reparse, exact reconciliation, and input/output gates without changing source, selected identity, or target SQLite. |
| B8-AC2 | Certification succeeds only with complete current B1–B7 records, exactly 100% reconciliation, and successful zero-warning input/output gates; changing any upstream byte/digest invalidates it. |
| B8-AC3 | Apply rechecks revision, input/staged trees, policy/tool bytes, certification, identity transition, and database receipt immediately before replacing only certified staged bytes. |
| B8-AC4 | Failure injection at every journal boundary proves rollback/roll-forward, selected identity-path use, staged-tree binding, idempotent SQLite retry/delete, lock exclusion, and no cross-resource atomicity claim. |
| B8-AC5 | A temporary neutral repository supplies its own profile, templates, operation inputs, validator/build bundle, and corpus; Raptor invokes public hooks and packages none of those names/assets. |
| B8-AC6 | Claude and Codex resolve the unchanged `/raptor:round-trip` command to the same agent/runtime; skills, agents, scripts, templates, schema vendor, manifests, and inventories remain complete and hash-aligned. |
| B8-AC7 | Scripts contain no transformation/orchestration logic, and no Rust CLI/SQLx, Dolt/MySQL, remote gate, fleet scheduler, shell invocation, secret, or raw tool trace is introduced. |

## Required validation

```sh
python -m pytest schema/tests plugins/raptor/tests
python -m pytest plugins/raptor/tests/migration/test_certification.py plugins/raptor/tests/migration/test_full_corpus.py plugins/raptor/tests/recovery
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
python plugins/raptor/scripts/validate_plugin.py --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0'
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
```

Apply/recovery tests operate only in temporary repositories. The repository-root
command uses a `validate` operation input and does not replace working-tree docs.

## Traceability and non-closure

- B8-D1–D6 close PB-REQ-005, REQ-RAP-016, and NFR-RAP-008 at full-corpus scope.
- No production migration of an external repository occurs in Raptor CI; consumers retain and run their own assets.
- No Rust CLI/SQLx, Dolt/MySQL, remote attestation, continuous synchronization, service, or fleet orchestration.

## Phase handoff

After B8, a consumer may prepare its own repository-local assets, run the Python
validate workflow, review Raptor's canonical evidence, switch the explicit
operation input to apply, and recover by operation ID if interrupted. A later
phase may add fleet coordination or Dolt only without weakening these contracts.
