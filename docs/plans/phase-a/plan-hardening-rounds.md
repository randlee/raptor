# Phase A Plan-Hardening Rounds

This ledger records the reviewer chain for `plan-phase-a.md` and all Phase A sprint plans. `reviewed_commit` may be `WORKTREE` before the first planning commit. Findings hashes are recorded by the coordinating team lead when reviewer results arrive.

| Round | Step | Reviewer | reviewed_commit | status | blocking | important | minor | findings_hash | supersedes | Note |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| 1 | 1 | arch-ctm | 7f4dac70a3bcebaf74f6421b4bb2709cf24085cb | PASS | 0 | 0 | 0 | step1-handoff-reconstructed | — | Initial guidelines pass; structured handoff was reconstructed below because the original coordinator record did not preserve the required Step 1 envelope. |
| 1 | 2 | plan-scope-reviewer | 7f4dac70a3bcebaf74f6421b4bb2709cf24085cb | FAIL | 0 | 3 | 1 | 45c592c0d7d0993ccb282428340a5739d1b3cdabb8b3b35b14cdad43acb66648 | step1-handoff-reconstructed | STEP2-R1: executable field contract, pinned normative reference, targeted Dolt gates; minor A3 routing rename. |
| 1 | 3 | arch-ctm | WORKTREE | READY_FOR_REREVIEW | 0 | 0 | 0 | step2-r1-correction | 45c592c0d7d0993ccb282428340a5739d1b3cdabb8b3b35b14cdad43acb66648 | Applied every STEP2-R1 finding; validation pending coordinator commit/rerun. |
| 2 | 2 | plan-scope-reviewer | fca037aa1473730c6200c056bfb0644564713a8d | PASS | 0 | 0 | 0 | 4c8a230187229ef0217661a3c9353ded5196ace8ec53b7f95cbd4f264d8b5895 | 45c592c0d7d0993ccb282428340a5739d1b3cdabb8b3b35b14cdad43acb66648 | STEP2-R2 scope review passed the then-current four-sprint topology with no findings. |
| 2 | 3 | arch-ctm | 28499639777293f08c555be5098d50bcc48c073b | PASS | 0 | 0 | 0 | 4c8a230187229ef0217661a3c9353ded5196ace8ec53b7f95cbd4f264d8b5895 | 4c8a230187229ef0217661a3c9353ded5196ace8ec53b7f95cbd4f264d8b5895 | Step 3 content and handoff metadata were committed in 2849963; this row identifies the reviewed content commit, not the later metadata-correction commit. |
| 2 | 4 | critical-plan-reviewer | 28499639777293f08c555be5098d50bcc48c073b | FAIL | 1 | 8 | 0 | 2a7d444d84df64c5b62b33ecebbead78a27a8a2607969ae4d8cdc0106f3b494e | 4c8a230187229ef0217661a3c9353ded5196ace8ec53b7f95cbd4f264d8b5895 | CRIT-001..009: handoff metadata, identity, measurement, SQLite, sprint split, profiles, vendor, runner, provenance. |
| 2 | 5 | arch-ctm | WORKTREE | READY_FOR_REREVIEW | 0 | 0 | 0 | critical-r1-correction | 2a7d444d84df64c5b62b33ecebbead78a27a8a2607969ae4d8cdc0106f3b494e | Corrected all critical findings and split plugin foundation/operations/rendering into A3/A4/A5; metadata commit remains pending. |
| 3 | 4 | critical-plan-reviewer | 5ada27ecfda2e7268e4e16d934714294820403f8 | FAIL | 0 | 4 | 0 | 5d751b50a7385e117c09daadaa0905b31b4132147d9a01fe5d55003f9c10a5db | 2a7d444d84df64c5b62b33ecebbead78a27a8a2607969ae4d8cdc0106f3b494e | CRIT-010..013: historical handoff paths/counts, reference-validation modes, first-import identity authority, and removal of path-only storage move. |
| 3 | 5 | arch-ctm | WORKTREE | READY_FOR_REREVIEW | 0 | 0 | 0 | critical-r2-correction | 5d751b50a7385e117c09daadaa0905b31b4132147d9a01fe5d55003f9c10a5db | Corrected CRIT-010..013 without adding or splitting product scope; validation pending coordinator commit/rerun. |
| 4 | 4 | critical-plan-reviewer | 8f5eec9b7bd9b52731f1dff4fa06485dc481bf18 | FAIL | 0 | 2 | 0 | efda24d70b9483b29f7639674dd4d7300d0e589f3879a4067efc4fc084b6c9f7 | 5d751b50a7385e117c09daadaa0905b31b4132147d9a01fe5d55003f9c10a5db | CRIT-014..015: identity execution ownership and false cross-resource atomicity. Third critical-review attempt exhausted the configured cap. |
| 4 | 5 | arch-ctm | WORKTREE | CAP_REACHED_CORRECTIONS_APPLIED | 0 | 0 | 0 | critical-r3-final-correction | efda24d70b9483b29f7639674dd4d7300d0e589f3879a4067efc4fc084b6c9f7 | Applied bounded corrections for CRIT-014..015; the reviewer loop is closed and the corrected plan advances to consistency hardening and QA. |
| 5 | 5 | arch-ctm | WORKTREE | PASS | 0 | 0 | 0 | step5-consistency-handoff | critical-r3-final-correction | Audited committed base abc2fb8; resolved four cross-document consistency findings and prepared the corrected worktree for Step 6 QA without another critical-review cycle. |
| 6 | 6 | quality-mgr | b3c93cbd09c25ffd76db2bd0513728f28ec082af | FAIL | 3 | 1 | 0 | 9c5791c42859b26e3081ab2e7528723a0a4482df8de8a3b5d4ab5e1735252109 | step5-consistency-handoff | Step 6 QA: raptor-QA-001, ARCH-001, ARCH-002, and raptor-QA-002. |
| 6 | 6 | arch-ctm | WORKTREE | READY_FOR_QA_RERUN | 0 | 0 | 0 | step6-qa-fix-handoff | 9c5791c42859b26e3081ab2e7528723a0a4482df8de8a3b5d4ab5e1735252109 | Applied exactly four bounded QA corrections; validation pending QA rerun after coordinator commit. |
| 7 | 6 | quality-mgr | c7e2b02 | PASS | 0 | 0 | 0 | step6-qa-pass | 9c5791c42859b26e3081ab2e7528723a0a4482df8de8a3b5d4ab5e1735252109 | Final requirements and architecture QA passed with all four prior findings closed; PR #6 is implementation-ready. |

Cycle caps:

- `plan_scope_review_cycle_limit`: 3
- `critical_review_cycle_limit`: 3

Completion requires `quality-mgr` PASS plus either reviewer PASS or `CAP_REACHED_CORRECTIONS_APPLIED` after the final findings were addressed. Each later row must supersede the applicable prior finding set; repeated reviewer output against the same commit with the same findings hash is a stale replay, not a new round.

Critical review reached its configured cycle cap after STEP4-R3. The final author correction below records the applied findings and closes that reviewer loop without claiming a reviewer PASS. Per the corrected plan-hardening semantics, the cap bounds editorial churn and the corrected plan advances to consistency hardening and `quality-mgr` QA.

## Reconstructed Step 1 handoff

The original Step 1 work was committed, but the coordinator handoff omitted the required preserved JSON envelope. This reconstruction corrects that tracking deficiency and is the input superseded by STEP2-R1; it does not claim a new review cycle.

```json
{
  "status": "PASS",
  "mode": "plan-hardening-guidelines-pass",
  "round_id": "STEP1-R1",
  "round_index": 1,
  "reviewed_commit": "7f4dac70a3bcebaf74f6421b4bb2709cf24085cb",
  "previous_reviewed_commit": "",
  "iterations": 4,
  "docs_modified": [
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/plan-hardening-rounds.md"
  ],
  "docs_created": [
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a2-sqlite-reference.md",
    "docs/plans/phase-a/sprint-a3-plugin-ingest.md",
    "docs/plans/phase-a/sprint-a4-render-and-roundtrip.md"
  ],
  "ready_for_next_step": true,
  "errors": [],
  "tracking_correction": "Envelope reconstructed after commit because the original Step 1 handoff was not preserved in the round ledger."
}
```

## Step 3 critical-review handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-sprint-scope",
  "round_id": "STEP3-R1",
  "round_index": 1,
  "reviewed_commit": "28499639777293f08c555be5098d50bcc48c073b",
  "previous_reviewed_commit": "fca037aa1473730c6200c056bfb0644564713a8d",
  "findings_hash": "4c8a230187229ef0217661a3c9353ded5196ace8ec53b7f95cbd4f264d8b5895",
  "metadata_commit": null,
  "metadata_commit_note": "The commit containing this corrected metadata necessarily follows the reviewed content commit and is intentionally not self-referential.",
  "iterations": 1,
  "findings_resolved": 2,
  "final_finding_count": 0,
  "sprint_splits_added": 0,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a2-sqlite-reference.md",
    "docs/plans/phase-a/sprint-a3-plugin-routing.md",
    "docs/plans/phase-a/sprint-a4-render-and-roundtrip.md"
  ],
  "docs_created": [],
  "ready_for_next_step": true,
  "errors": []
}
```

## Critical-review correction handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-consistency",
  "round_id": "STEP4-R1-CORRECTION",
  "round_index": 1,
  "reviewed_commit": "WORKTREE",
  "previous_reviewed_commit": "28499639777293f08c555be5098d50bcc48c073b",
  "findings_hash": "2a7d444d84df64c5b62b33ecebbead78a27a8a2607969ae4d8cdc0106f3b494e",
  "metadata_commit": null,
  "iterations": 1,
  "findings_resolved": 9,
  "final_finding_count": 0,
  "sprint_splits_added": 1,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a2-sqlite-reference.md"
  ],
  "docs_created": [
    "docs/plans/phase-a/sprint-a3-plugin-foundation.md",
    "docs/plans/phase-a/sprint-a4-plugin-operations.md",
    "docs/plans/phase-a/sprint-a5-render-and-roundtrip.md"
  ],
  "docs_removed_or_renamed": [
    "docs/plans/phase-a/sprint-a3-plugin-routing.md",
    "docs/plans/phase-a/sprint-a4-render-and-roundtrip.md"
  ],
  "rename_history": [
    "STEP2-R1: sprint-a3-plugin-ingest.md -> sprint-a3-plugin-routing.md",
    "STEP4-R1 correction: sprint-a3-plugin-routing.md -> sprint-a3-plugin-foundation.md",
    "STEP4-R1 correction: sprint-a4-render-and-roundtrip.md -> sprint-a5-render-and-roundtrip.md; new sprint-a4-plugin-operations.md"
  ],
  "ready_for_critical_rereview": true,
  "errors": []
}
```

## Critical-review round 2 correction handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-consistency",
  "round_id": "STEP4-R2-CORRECTION",
  "round_index": 2,
  "reviewed_commit": "WORKTREE",
  "previous_reviewed_commit": "5ada27ecfda2e7268e4e16d934714294820403f8",
  "findings_hash": "5d751b50a7385e117c09daadaa0905b31b4132147d9a01fe5d55003f9c10a5db",
  "metadata_commit": null,
  "iterations": 1,
  "findings_resolved": 4,
  "final_finding_count": 0,
  "sprint_splits_added": 0,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a2-sqlite-reference.md",
    "docs/plans/phase-a/sprint-a4-plugin-operations.md",
    "docs/plans/phase-a/sprint-a5-render-and-roundtrip.md"
  ],
  "docs_created": [],
  "docs_removed_or_renamed": [],
  "ready_for_critical_rereview": true,
  "errors": []
}
```

## Final critical correction at cycle cap

```json
{
  "status": "CAP_REACHED_CORRECTIONS_APPLIED",
  "mode": "plan-hardening-consistency",
  "round_id": "STEP4-R3-FINAL-CORRECTION",
  "round_index": 3,
  "reviewed_commit": "WORKTREE",
  "previous_reviewed_commit": "8f5eec9b7bd9b52731f1dff4fa06485dc481bf18",
  "findings_hash": "efda24d70b9483b29f7639674dd4d7300d0e589f3879a4067efc4fc084b6c9f7",
  "reviewer_verdict": "FAIL",
  "reviewer_pass_claimed": false,
  "critical_review_cycle_cap": 3,
  "critical_review_cycle_cap_exhausted": true,
  "corrections_applied": 2,
  "sprint_splits_added": 0,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a4-plugin-operations.md",
    "docs/plans/phase-a/sprint-a5-render-and-roundtrip.md"
  ],
  "docs_created": [],
  "docs_removed_or_renamed": [],
  "ready_for_critical_rereview": false,
  "next_action": "Proceed to Step 5 consistency hardening, then Step 6 quality-mgr QA without another critical-review cycle.",
  "errors": []
}
```

## Step 5 consistency-hardening handoff

```json
{
  "status": "PASS",
  "mode": "plan-hardening-consistency",
  "round_id": "STEP5-R1",
  "round_index": 1,
  "reviewed_commit": "WORKTREE",
  "previous_reviewed_commit": "abc2fb8b7bd375d8901722e47093b7d05a730cb8",
  "iterations": 2,
  "findings_resolved": 4,
  "final_finding_count": 0,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a2-sqlite-reference.md",
    "docs/plans/phase-a/sprint-a4-plugin-operations.md",
    "docs/plans/phase-a/sprint-a5-render-and-roundtrip.md"
  ],
  "docs_created": [],
  "ready_for_next_step": true,
  "next_step": "Step 6 quality-mgr QA",
  "critical_reviewer_relaunched": false,
  "errors": []
}
```

## Step 6 QA-fix handoff

```json
{
  "status": "PASS",
  "mode": "plan-qa-fix",
  "round_id": "STEP6-R1-CORRECTION",
  "round_index": 1,
  "reviewed_commit": "WORKTREE",
  "previous_reviewed_commit": "b3c93cbd09c25ffd76db2bd0513728f28ec082af",
  "findings_hash": "9c5791c42859b26e3081ab2e7528723a0a4482df8de8a3b5d4ab5e1735252109",
  "qa_verdict": "FAIL",
  "qa_counts": {"blocking": 3, "important": 1, "minor": 0},
  "findings_resolved": [
    "raptor-QA-001",
    "ARCH-001",
    "ARCH-002",
    "raptor-QA-002"
  ],
  "final_finding_count_by_author_check": 0,
  "docs_modified": [
    "docs/plans/phase-a/plan-hardening-rounds.md",
    "docs/plans/phase-a/plan-phase-a.md",
    "docs/plans/phase-a/sprint-a1-models-and-json-schema.md",
    "docs/plans/phase-a/sprint-a3-plugin-foundation.md",
    "docs/plans/phase-a/sprint-a4-plugin-operations.md",
    "docs/plans/phase-a/sprint-a5-render-and-roundtrip.md"
  ],
  "docs_created": [],
  "scope_expanded": false,
  "ready_for_qa_rerun": true,
  "errors": []
}
```

## Step 6 final QA result

```json
{
  "sprint": "Phase A",
  "task": "final-plan-qa-rerun",
  "branch": "plans/phase-a",
  "commit": "c7e2b02",
  "pr": 6,
  "verdict": "PASS",
  "findings": {"blocking": 0, "important": 0, "minor": 0},
  "reviewers": {
    "req-qa": {"verdict": "PASS", "blocking": 0, "important": 0, "minor": 0},
    "arch-qa": {"verdict": "PASS", "blocking": 0, "important": 0, "minor": 0}
  },
  "closed_findings": [
    "raptor-QA-001",
    "ARCH-001",
    "ARCH-002",
    "raptor-QA-002"
  ],
  "merge_readiness": "ready",
  "errors": []
}
```
