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
def reconcile_corpus(
    ledger: ReconciliationLedger, *, source_bytes: SourceBytesResolver,
    authority_inputs: AuthorityResolver,
) -> ReconciliationResult: ...
def prepare_apply_plan(
    result: ReconciliationResult, *, stage_root: RepositoryPath,
) -> CorpusApplyPlan: ...
```

Reconciliation recomputes every receipt and replays byte partitions,
transformations, derivations, canonical/SQLite equality, projection consumption,
render/reparse provenance, and lineage. Success requires every independent
predicate to equal exactly 100%; partial percentages are never rounded.

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
