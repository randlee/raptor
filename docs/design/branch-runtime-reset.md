# Raptor planning reset: branch-aware runtime and Dolt

Status: proposed; no implementation dispatch or merge is authorized by this plan.
Execution scope and dependencies live in Beads (`rap-phase-c`, `rap-phase-d`,
`rap-phase-e`). This document records owner intent, boundaries and evidence;
it is not a second sprint tracker.

## Owner intent

Captured from the planning conversation on 2026-11-02:

- "every crud operation must target a specified branch"
- "multiple raptor cli clients may be talking to the same server at the same time"
- "we will need an sc-dolt database ... part of sc-runtime package"
- "username/password PER DATABASE stored locally ... settable through the environment"
- "many teams/repos may be stakeholders in requirements"
- "fork, clone are probably outside of what we want to deal w/ initially"
- "the goal isn't to re-invent the wheel"
- "we will need to be able to create a branch, and to merge if there are no conflicts"

These latest scope statements govern earlier suggestions. Initial scope includes
branch creation, safe branch selection and concurrent access, clean native merge,
native conflict/diff evidence, and the earlier push/pull requirement. Fork/clone,
export destination/format policy, a custom diff engine and automated conflict
resolution are excluded. A known SQLite-to-Dolt seed is a separate bootstrap,
not a general database cloning feature.

## Verified starting state

Planning branch base: develop `5b7be27cb66aa8efe36a93674b2d452d38b89951`.
Rust 1.94.1 alignment is merged through PR #89. Phase B is quality-approved and
landed on `integrate/phase-b` at `4bb0d58d497cce30b1cccdd50ebe1a965ad6cffc`;
PR #88 is still open at this investigation. Do not pretend its schema crate is
already on develop. An explicit baseline gate blocks implementation until the
approved import/schema code is integrated and its exact head recorded.
No changes to the consumer documentation repository are part of this work.

The shared SDK proposal is authored separately in sc-runtime, based on
`026907bf4033685cd61aa09d2d81e243e8e8b0b1`, tracked by `run-sc-dolt`.
Dolt source baseline: v2.6.2, `46d8805d8556599eb0a6472892e67e3bb1e0de03`.
Its source/test evidence covers the registered SQL API, not an obligation to wrap
every upstream operation. See [the pinned SDK evidence](https://github.com/randlee/sc-runtime/blob/bda2c5775e79e6c4be0001ab7bfbf329334c6f5f/docs/research/dolt-v2.6.2/README.md) for pinned claims and probe logs.

## Boundary decisions

1. Keep `raptor-schema` authoritative for records, fields and scalar rules.
   Python remains import-only. Preserve strict duplicate rejection.
2. Add the existing sc-runtime SDK to an application-owned Raptor daemon.
   Keep CLI transport thin and core/domain code separate from HTTP assembly.
3. Put generic Dolt branch/session/native-operation capability in shared
   `sc-dolt`. Raptor owns its tables, record SQL and operation semantics.
4. Resolve branch in the client, proposed precedence: explicit option, environment,
   then selected `.raptor/` connection configuration. Missing branch is an error;
   main must be selected explicitly even when it is the bootstrap target.
5. Send the resolved database/branch with each request. A daemon's environment
   is not another client's branch selection. Branch scopes must not leak across
   reused connections, principals, credentials or requests.
6. SQL credentials are keyed by named connection/server/database/principal, with
   per-database local storage and environment override support. Keep providers
   replaceable; neither this plan nor sc-dolt invents a secret manager.
7. Resolve client-side secret overrides before the request. Local daemon transport
   may use its protected socket; remote secret forwarding requires an authenticated
   encrypted channel and is never silently sent over plain remote TCP. Do not
   log request secrets, database URLs containing passwords, or raw credential errors.
8. Authenticate SQL access independently from human, agent/session, team and repo
   attribution. An asserted author/team is not proof of database identity.
9. Dolt is authoritative. SQLite is a disposable read-only local snapshot keyed
   by server/database/branch/commit, never a bidirectional working copy.
10. All record mutations target Dolt. Offline operation supports reads and fails
    writes explicitly. Internal refresh may build a new SQLite snapshot, but
    clients never mutate a published snapshot or write it back to Dolt.
11. Create branches and perform native fast-forward/clean three-way merges.
    On conflict, return native diff/conflict information for operator action.
    Do not force, resolve automatically, or invent rollback compensation.
12. Keep generic operation/commit provenance in sc-dolt's results. Raptor owns
    versioned stakeholder mappings and requirement impact evidence.

## Evidence implications

Native SQL session selection and per-connection checkout are supported. Shared
same-branch working sets are not independent private client workspaces.
SQL transaction commit and Dolt history commit differ unless intentionally wired.
A clean native merge can publish before the caller issues SQL rollback; rollback
cannot undo that published commit. Native conflict cleanup and dirty-target
protection were exercised with a checksum-verified v2.6.2 binary in isolated
servers. No Rust SQLx wire proof was run yet; its acceptance is an explicit gate.
Preview is advisory, can race with branch advancement, and does not enumerate
all constraint failures. Actual merge results remain authoritative.
Remote SQL procedures may share server-managed credentials. The provider must
report that limitation, not mutate process environment for concurrent clients.
Author/committer metadata is attribution, not authenticated human identity.

## Next phases and usable outcomes

| Phase | Outcome | Work that can run alongside it |
| --- | --- | --- |
| C | Real sc-runtime daemon, JSON CLI, configuration and branch-context validation | shared sc-dolt implementation in its own repository |
| D | Branch-aware Raptor CRUD, native branch/merge/diff/push/pull, known SQLite seed and read-only branch snapshots | Dolt store and SQLite snapshot implementation after one shared contract |
| E | Human/agent/team/repo provenance and versioned many-to-many stakeholder/impact evidence | provenance and stakeholder implementations after their shared contract |

Phase C does not claim a Dolt product store or leave placeholder CRUD endpoints.
Its real endpoint validates canonical records through the Phase B crate and
reports resolved public context without exposing credentials. Phase D supplies
CRUD and the Dolt store. Phase E makes cross-repository change investigation a
complete product behavior rather than labeling every stakeholder as impacted.

## Evidence and acceptance spine

- SDK first proves actual Rust SQLx/MySQL interoperability against pinned Dolt.
- Two simultaneous clients use the same ID with different values on two branches;
  pool reuse must preserve isolation and leave main unchanged.
- A known validated SQLite fixture seeds an explicitly selected empty Dolt main;
  preserve IDs, nested content and ordering inside records, then commit and prove
  complete record equality. Existing target data is never silently overwritten.
- A cache refresh reads one immutable commit, builds and validates a fresh SQLite
  file, and publishes its reference atomically. Failed refresh preserves the
  previous complete snapshot; active readers retain a valid snapshot on Windows
  and Unix. Branch switches cannot serve another branch's cache.
- Native branch create, fast-forward and clean three-way merge succeed. Row,
  schema and constraint conflicts return evidence and no conflict-bearing merge
  commit. Assert working-state cleanup, not only unchanged HEAD.
- Lost responses after a possible publication are uncertain outcomes, not automatic
  retry permission. Reconcile operation/commit evidence before another mutation.
- Native push/pull identifies local branch, remote and ref and preserves permission
  errors. Conflicts are reported through Dolt. No force flag is implicit.
- Core repository A changes a requirement; repository B's stakeholder relationship
  at that revision and linked test/issue evidence reconstruct the investigation.
  Actor repository, stakeholder repository and authenticated SQL account remain
  distinct. No repository ownership columns are added to requirement records.
- All feature closure runs through the real CLI/daemon/store composition and
  preserves existing schema, import, strict-duplicate and round-trip tests.

## Review boundary

Plans are proposed/open, not completed code. Development remains blocked by
plan review and named baseline/artifact gates. Integration branch choices and
source package pins must be recorded before dispatch. SDK publication and final
phase landing require their normal maintainer/operator authorization.

## Recorded planning readiness

The three phase indexes and Beads containers validate. The installed sprint-group
pour currently refuses QA nodes missing the required `reviewers_round1` field.
No group nodes were created. This observed workflow mismatch is tracked as
`rap-plan-pour-qa-contract`; it blocks plan review/dispatch and is not bypassed by
weakening validation or hand-forging execution nodes. Baseline and SDK artifact
gates also remain explicit. This is a proposed plan, not implementation approval.
