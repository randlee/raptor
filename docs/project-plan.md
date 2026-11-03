# Project Plan

The product is described in `docs/requirements.md` and `docs/adr/`. Work is
ordered so the import fixture exists before any product code is written.

| Step | Scope | State |
|---|---|---|
| Phase A | Import scripts: record model, extractor, skills, templates (`docs/plans/phase-a/`) | Done |
| Phase B | Schema in Rust (`crates/raptor-schema`), Python importer generic over it, REQ/NFR and ADR columns, grouped diagnostics for the consumer corpus; six sprints (`docs/plans/phase-b/`) | Quality-approved on integration; PR #88 to develop remains open |
| Phase C | sc-runtime daemon, CLI and explicit branch context; Beads `rap-phase-c` | Proposed; plan review and Phase B baseline gate required |
| Phase D | Branch-aware Dolt store and native operations, SQLite seed and read-only snapshots; Beads `rap-phase-d` | Proposed; depends on C and shared sc-dolt artifact |
| Phase E | Change provenance and multi-repository stakeholder/impact evidence; Beads `rap-phase-e` | Proposed; depends on D |

Only the operator adds steps to this table.

The planning reset is grounded in [owner intent and source evidence](design/branch-runtime-reset.md).
Future sprint descriptions and dependencies are authoritative in Beads; the
tracked phase JSONL files list their membership and hard prerequisites.
The shared SDK work is tracked separately as `run-sc-dolt` in sc-runtime.
No product implementation is started by these proposed plans.
