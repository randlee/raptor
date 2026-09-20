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

Cycle caps:

- `plan_scope_review_cycle_limit`: 3
- `critical_review_cycle_limit`: 3

Completion requires PASS from `plan-scope-reviewer`, `critical-plan-reviewer`, and `quality-mgr`. Each later row must supersede the applicable prior finding set; repeated reviewer output against the same commit with the same findings hash is a stale replay, not a new round.

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
