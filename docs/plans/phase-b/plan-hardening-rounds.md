# Phase B Plan-Hardening Rounds

This ledger records review of [`plan-phase-b.md`](plan-phase-b.md) and all Phase B sprint plans. The requirements baseline is `d65599fd3332fcdfa75a63913e6679a0616db065`. A `PASS` here means only that the initial authoring pass is internally complete; implementation remains blocked until the repository's plan-hardening review and final QA gates pass.

| Round | Step | Reviewer | reviewed_commit | status | blocking | important | minor | findings_hash | supersedes | Note |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| 1 | 1 | plan author | WORKTREE | READY_FOR_SCOPE_REVIEW | 0 | 0 | 0 | initial-phase-b-authoring | — | Five-sprint initial plan grounded in requirements commit d65599f and Phase A contracts; no reviewer result claimed. |
| 1 | 1 | arch-ctm | c55471f6f4a34315e77b78ab1447ecdf8870c0ea | PASS | 0 | 0 | 0 | step1-guidelines-pass | initial-phase-b-authoring | Ratified the three open contracts, removed operation/CLI ambiguity, and split overloaded closures into eight production-bounded sprints; the following metadata-only commit records this reviewed content commit. |
| 1 | 2 | plan-scope-reviewer | c4e48421d40413798d1d426d29bdc8548819bd97 | FAIL | 0 | 6 | 0 | cfe785faf5044ea40d6274a00675d95d788a61075c81237d4282653f731d81c0 | step1-guidelines-pass | PB-SCOPE-001..006: complete B1/B6/B8 contracts, identity architecture authority, revision ownership, and B8 split. |
| 2 | 1 | arch-ctm | 86b09830685285a5ec1aed6b159558106d44a5d2 | PASS | 0 | 0 | 0 | step1-r2-correction | cfe785faf5044ea40d6274a00675d95d788a61075c81237d4282653f731d81c0 | Applied all six scope corrections and split non-mutating certification from apply/recovery as B8/B9. |
| 2 | 3 | arch-ctm | 4fb9584520c90a76a10cf13768194a1c3c572e71 | PASS | 0 | 0 | 0 | step3-sprint-scope-handoff | cfe785faf5044ea40d6274a00675d95d788a61075c81237d4282653f731d81c0 | Verified PB-SCOPE-001..006 closure and nine-sprint production boundaries; corrected receipt ordering and validate/apply certification binding. |
| 2 | 2 | plan-scope-reviewer | 4fb9584520c90a76a10cf13768194a1c3c572e71 | FAIL | 0 | 2 | 0 | 8d41c412033f9e6ba129286812b624de9d7b8dd18774bd2aeeb54e68fa2233a0 | step3-sprint-scope-handoff | PB-SCOPE-001 and PB-SCOPE-007: authoritative ledger contract and exact operation-state lifecycle. Hash is over the ordered finding IDs because only the deduplicated triage payload was retained. |
| 2 | 4 | critical-plan-reviewer | 4fb9584520c90a76a10cf13768194a1c3c572e71 | FAIL | 1 | 3 | 0 | 19e4f03370846728b98a9b3cd9ff125fa678644e77ccf9678676e96bba5a152b | step3-sprint-scope-handoff | PLAN-CRIT-001..004: ledger duplication, filesystem removals, tool bundles, and gate workspaces. Hash is over ordered finding IDs because only the deduplicated triage payload was retained. |
| 3 | 3 | arch-ctm | 05ed3987884359ab37ad9f543066372cb0fea48b | CORRECTED_FOR_REREVIEW | 0 | 0 | 0 | 684f746adf12cd6b961fc4fda6dbef24ead4ec4c2a69295b66d6958c2f3f6ba3 | 8d41c412+19e4f033 | Deduplicated six reviewer reports into TRIAGE-001..005 (PB-SCOPE-001 and PLAN-CRIT-001 overlap) and corrected all five contracts without another review claim. |
| 3 | 2 | plan-scope-reviewer | fc0e1d3ae9cb486151f15ca1564c855ea3ebf360 | FAIL | 0 | 1 | 0 | a7c25a215c723765850060adffc6b98a4950affd2fe8d89c0601c96a9c3a0965 | 684f746a | PLAN-SCOPE-008: final compatibility/certification receipt ownership and bindings. Hash is over the retained finding ID. |
| 3 | 4 | critical-plan-reviewer | fc0e1d3ae9cb486151f15ca1564c855ea3ebf360 | FAIL | 0 | 1 | 0 | f2c08a807158cbed78a2f1765231e1d14365eb3eb9105319216b145e5140112b | 684f746a | PLAN-CRIT-005: effective gate-workspace collision invariants and bindings. Hash is over the retained finding ID. Critical cycle 2 of 2 is final. |
| 4 | 5 | arch-ctm | cc30bcab10ead28378a95c1923c47fb36c4011bf | CORRECTED_CAP_TRANSITION | 0 | 0 | 0 | 753ce61bb5af26e0e218553e6d9300c1b0a4aa1b9e7bd5540a462d8ae251b633 | a7c25a21+f2c08a80 | Corrected FINAL-001/002; both reviewer caps are exhausted, so workflow advances to bounded consistency hardening and final QA without another scope/critical review. |
| 4 | 6 | quality-mgr | 8a9c8fedc70d8bfa61a7a2694e4b6c2cf6d6b875 | FAIL | 0 | 2 | 0 | 2fee7793362eb1fc8b93125521c30bec33ccbac3dee5a3a2d63095639d182ae5 | 753ce61b | raptor-QA-PB-001/002: terminal ledger-status producer ambiguity and incomplete REQ-RAP-015 certification/apply traceability. |
| 5 | 5 | arch-ctm | f57a65ff9a4947c6ee7696a1c568082192a36df4 | READY_FOR_FINAL_QA | 0 | 0 | 0 | final-qa-remediation | 2fee7793 | Centralized terminal ledger transitions in B8 and extended REQ-RAP-015 traceability through B8 certification and B9 apply/recovery; no reviewer cycle reopened. |

## Initial author handoff

```json
{
  "status": "READY_FOR_SCOPE_REVIEW",
  "mode": "plan-hardening-initial-authoring",
  "round_id": "STEP1-R1",
  "round_index": 1,
  "requirements_commit": "d65599fd3332fcdfa75a63913e6679a0616db065",
  "reviewed_commit": "c55471f6f4a34315e77b78ab1447ecdf8870c0ea",
  "sprint_count": 5,
  "topology": [
    "B1 migration evidence contracts",
    "B2 manifest-driven corpus ingress",
    "B3 lossless byte and persistence proof",
    "B4 projection, lineage, and reconciliation",
    "B5 external evidence and corpus certification"
  ],
  "docs_created": [
    "docs/plans/phase-b/plan-phase-b.md",
    "docs/plans/phase-b/sprint-b1-migration-evidence-contracts.md",
    "docs/plans/phase-b/sprint-b2-manifest-corpus-ingress.md",
    "docs/plans/phase-b/sprint-b3-lossless-byte-persistence-proof.md",
    "docs/plans/phase-b/sprint-b4-projection-lineage-reconciliation.md",
    "docs/plans/phase-b/sprint-b5-external-evidence-certification.md",
    "docs/plans/phase-b/plan-hardening-rounds.md"
  ],
  "ready_for_next_step": true,
  "next_step": "plan scope review",
  "errors": []
}
```

## Review limits

- `plan_scope_review_cycle_limit`: 3.
- `critical_review_cycle_limit`: 2.
- Every reviewer row records the exact reviewed commit and findings hash; a metadata commit following reviewed content is not self-referential.
- Corrections supersede the exact prior finding set and do not claim reviewer PASS.
- Final implementation readiness requires requirements QA and architecture QA PASS after reviewer convergence or an explicitly recorded cap outcome with all final findings corrected.

## Parallel review round 1 deduplication and correction

The authoritative deduplicated triage is the five-item set whose canonical file
hash is `684f746adf12cd6b961fc4fda6dbef24ead4ec4c2a69295b66d6958c2f3f6ba3`:

| Triage ID | Reviewer findings | Correction owner | Resolution |
|---|---|---|---|
| TRIAGE-001 | PB-SCOPE-001, PLAN-CRIT-001 | B1 | One exact derivation/ledger model, lifecycle, producer ownership, omission/order rules, and digest chain. |
| TRIAGE-002 | PB-SCOPE-007 | B9 | One operation locator/layout with separate validation/apply state, collision, retention, cleanup, and recovery rules. |
| TRIAGE-003 | PLAN-CRIT-002 | B6/B8/B9 | Certified ordered filesystem puts/deletes, absence-or-digest preconditions, final-tree inventory, rollback, and roll-forward. |
| TRIAGE-004 | PLAN-CRIT-003 | B1/B7 | Versioned bundle root/source, complete inventory/digest, relative entrypoint, deterministic version proof, and adversarial checks. |
| TRIAGE-005 | PLAN-CRIT-004 | B1/B7/B8/B9 | Versioned auxiliary workspace inventory/digest, exact overlays, write isolation, certification, and apply revalidation. |

The scope reviewer reported two important findings. The parallel critical review
reported one blocking and three important findings. TRIAGE-001 is their sole
overlap, so five unique corrections supersede six raw reports. This author
correction records no reviewer PASS and starts no additional review.

```json
{
  "status": "PASS",
  "mode": "plan-hardening-sprint-scope",
  "reviewed_commit": "05ed3987884359ab37ad9f543066372cb0fea48b",
  "previous": "4fb9584520c90a76a10cf13768194a1c3c572e71",
  "findings_resolved": 5,
  "files_changed": [
    "docs/configuration.md",
    "docs/requirements-migration.md",
    "docs/plans/phase-b/plan-hardening-rounds.md",
    "docs/plans/phase-b/plan-phase-b.md",
    "docs/plans/phase-b/sprint-b1-migration-evidence-contracts.md",
    "docs/plans/phase-b/sprint-b6-corpus-reconciliation.md",
    "docs/plans/phase-b/sprint-b7-compatibility-evidence.md",
    "docs/plans/phase-b/sprint-b8-corpus-certification.md",
    "docs/plans/phase-b/sprint-b9-apply-recovery-handoff.md"
  ],
  "ready_for_next_step": true
}
```

## Final capped-review correction and consistency handoff

Scope cycle 3 reported PLAN-SCOPE-008 and critical cycle 2 reported
PLAN-CRIT-005, each important and neither blocking. The critical review limit is
now exhausted; scope is also at its configured third cycle. FINAL-001 assigns
the last three receipts to B7/B8 with exact predecessor/input/output/count and
evidence bindings. FINAL-002 defines the versioned effective workspace layout,
pre-materialization collision rejection, evidence binding, certification, and
apply revalidation. These author corrections do not claim reviewer PASS and
must proceed directly through consistency checks and final QA.

```json
{
  "status": "PASS",
  "mode": "plan-hardening-consistency-handoff",
  "reviewed_commit": "cc30bcab10ead28378a95c1923c47fb36c4011bf",
  "previous": "fc0e1d3ae9cb486151f15ca1564c855ea3ebf360",
  "findings_resolved": 2,
  "ready_for_qa": true
}
```

## Final QA remediation handoff

raptor-QA-PB-001 is resolved by the exact B1 status-owner matrix: B6 alone may
advance `open -> reconciled`, B7 preserves `reconciled`, and B8's public
transition API is the sole producer of every terminal ledger status. B6/B7
failure states remain typed outcomes until B8 terminalizes them.
raptor-QA-PB-002 is resolved by tracing REQ-RAP-015 through B8 certification
binding and B9 certified apply/recovery in addition to B3–B6 proof generation.
No scope or critical review is reopened.

```json
{
  "status": "PASS",
  "mode": "plan-hardening-final-qa-remediation",
  "reviewed_commit": "f57a65ff9a4947c6ee7696a1c568082192a36df4",
  "previous": "8a9c8fedc70d8bfa61a7a2694e4b6c2cf6d6b875",
  "findings_resolved": 2,
  "ready_for_qa": true
}
```

## Step 1 guidelines-pass handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-guidelines-pass",
  "round_id": "STEP1-R1",
  "round_index": 1,
  "reviewed_commit": "c4e48421d40413798d1d426d29bdc8548819bd97",
  "previous_reviewed_commit": "6aaa882cef56cd75140a6861b2f2ff1264c32820",
  "iterations": 2,
  "sprint_count": 8,
  "docs_modified": [
    "docs/plans/phase-b/plan-phase-b.md",
    "docs/plans/phase-b/plan-hardening-rounds.md",
    "docs/plans/phase-b/sprint-b1-migration-evidence-contracts.md",
    "docs/plans/phase-b/sprint-b2-manifest-corpus-ingress.md",
    "docs/plans/phase-b/sprint-b3-lossless-byte-persistence-proof.md"
  ],
  "docs_created": [
    "docs/plans/phase-b/sprint-b4-corpus-lineage.md",
    "docs/plans/phase-b/sprint-b5-projection-render-reparse.md",
    "docs/plans/phase-b/sprint-b6-corpus-reconciliation.md",
    "docs/plans/phase-b/sprint-b7-compatibility-evidence.md",
    "docs/plans/phase-b/sprint-b8-corpus-certification.md"
  ],
  "docs_removed_or_renamed": [
    "docs/plans/phase-b/sprint-b4-projection-lineage-reconciliation.md",
    "docs/plans/phase-b/sprint-b5-external-evidence-certification.md"
  ],
  "ready_for_next_step": true,
  "errors": []
}
```

## Step 3 sprint-scope handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-sprint-scope",
  "round_id": "STEP-3-R1",
  "round_index": 1,
  "reviewed_commit": "4fb9584520c90a76a10cf13768194a1c3c572e71",
  "previous_reviewed_commit": "86b09830685285a5ec1aed6b159558106d44a5d2",
  "findings_hash": "cfe785faf5044ea40d6274a00675d95d788a61075c81237d4282653f731d81c0",
  "iterations": 2,
  "findings_resolved": 6,
  "final_finding_count": 0,
  "sprint_splits_added": 1,
  "docs_modified": [
    "docs/plans/phase-b/plan-hardening-rounds.md",
    "docs/plans/phase-b/plan-phase-b.md",
    "docs/plans/phase-b/sprint-b1-migration-evidence-contracts.md",
    "docs/plans/phase-b/sprint-b8-corpus-certification.md",
    "docs/plans/phase-b/sprint-b9-apply-recovery-handoff.md"
  ],
  "docs_created": [],
  "ready_for_next_step": true,
  "errors": []
}
```

## Step 1 round 2 correction handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-guidelines-pass",
  "round_id": "STEP1-R2",
  "round_index": 2,
  "reviewed_commit": "86b09830685285a5ec1aed6b159558106d44a5d2",
  "previous_reviewed_commit": "c4e48421d40413798d1d426d29bdc8548819bd97",
  "findings_hash": "cfe785faf5044ea40d6274a00675d95d788a61075c81237d4282653f731d81c0",
  "iterations": 1,
  "findings_resolved": [
    "PB-SCOPE-001",
    "PB-SCOPE-002",
    "PB-SCOPE-003",
    "PB-SCOPE-004",
    "PB-SCOPE-005",
    "PB-SCOPE-006"
  ],
  "sprint_count": 9,
  "docs_modified": [
    "docs/plans/phase-b/plan-phase-b.md",
    "docs/plans/phase-b/plan-hardening-rounds.md",
    "docs/plans/phase-b/sprint-b1-migration-evidence-contracts.md",
    "docs/plans/phase-b/sprint-b2-manifest-corpus-ingress.md",
    "docs/plans/phase-b/sprint-b6-corpus-reconciliation.md",
    "docs/plans/phase-b/sprint-b7-compatibility-evidence.md",
    "docs/plans/phase-b/sprint-b8-corpus-certification.md"
  ],
  "docs_created": [
    "docs/plans/phase-b/sprint-b9-apply-recovery-handoff.md"
  ],
  "ready_for_next_step": true,
  "errors": []
}
```
