# Phase A Plan-Hardening Rounds

This ledger records the reviewer chain for `plan-phase-a.md` and all Phase A sprint plans. `reviewed_commit` may be `WORKTREE` before the first planning commit. Findings hashes are recorded by the coordinating team lead when reviewer results arrive.

| Round | Step | Reviewer | reviewed_commit | status | blocking | important | minor | findings_hash | supersedes | Note |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| 1 | 1 | arch-ctm | 7f4dac70a3bcebaf74f6421b4bb2709cf24085cb | PASS | 0 | 0 | 0 | step1-handoff-reconstructed | — | Initial guidelines pass; structured handoff was reconstructed below because the original coordinator record did not preserve the required Step 1 envelope. |
| 1 | 2 | plan-scope-reviewer | 7f4dac70a3bcebaf74f6421b4bb2709cf24085cb | FAIL | 0 | 3 | 1 | 45c592c0d7d0993ccb282428340a5739d1b3cdabb8b3b35b14cdad43acb66648 | step1-handoff-reconstructed | STEP2-R1: executable field contract, pinned normative reference, targeted Dolt gates; minor A3 routing rename. |
| 1 | 3 | arch-ctm | WORKTREE | READY_FOR_REREVIEW | 0 | 0 | 0 | step2-r1-correction | 45c592c0d7d0993ccb282428340a5739d1b3cdabb8b3b35b14cdad43acb66648 | Applied every STEP2-R1 finding; validation pending coordinator commit/rerun. |

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
    "docs/plans/phase-a/sprint-a3-plugin-routing.md",
    "docs/plans/phase-a/sprint-a4-render-and-roundtrip.md"
  ],
  "ready_for_next_step": true,
  "errors": [],
  "tracking_correction": "Envelope reconstructed after commit because the original Step 1 handoff was not preserved in the round ledger; Sprint A3 is renamed by the STEP2-R1 correction."
}
```
