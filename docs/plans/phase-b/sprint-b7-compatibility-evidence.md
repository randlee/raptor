# Sprint B7 — Trusted Compatibility Evidence

## Objective and stack

Produce Raptor-controlled compatibility evidence for the accepted input and
exact B6 staged output using only policy-pinned revision, validator, and
site-build tools.

- `gh-stack` branch: `phase-b/07-compatibility-evidence`
- Relation: `must_follow B6`
- Merge-forward: merge pushed B6 development before every B7 development/fix round; B6 PR merges first.
- Parallel safety: not `parallel_safe`; B7 consumes B6's immutable tree/ledger and provides B8's compatibility evidence.

## Execution contract

```python
def verify_current_revision(
    *, policy: MigrationTrustPolicy, operation: MigrationOperationInput,
    repository_root: Path,
) -> CompatibilityEvidence: ...

def run_compatibility_gates(
    *, policy: MigrationTrustPolicy, corpus_role: Literal["input", "staged"],
    bound_tree: CorpusTree, operation: MigrationOperationInput,
    ledger: ReconciliationLedger,
) -> tuple[ReconciliationLedger, tuple[CompatibilityEvidence, ...]]: ...
```

`verify_current_revision` is the sole Git invocation boundary. B8 certification
consumes its evidence; B9 calls this same B7 API immediately before apply to
recompute current revision and compares the new evidence with the certification.
No caller constructs Git argv or interprets its output.

For every policy tool and required corpus role, the runtime opens declared
bundle/interpreter components as no-follow handles. It inventories the entire
versioned bundle root and requires exact equality with the sorted B1 member
inventory before copying it into a new private execution directory, fsyncing,
and rehashing it. The relative entrypoint may resolve only within that copy.
Before a gate, the runtime executes the declared version command and requires
the exact expected stdout, empty stderr, and exit zero; its evidence binds the
inventory, entrypoint, command, output, and result digests.

The runtime prepares a fresh private gate workspace for the declared
`repository_root` or `staging_root` role. It overlays the exact bound corpus at
the workspace root, then copies every declared auxiliary input to its distinct
allowlisted workspace path. The canonical no-follow auxiliary inventory must
equal the policy inventory and `workspace_inputs_sha256`; the evidence
`workspace_sha256` additionally binds corpus role, exact bound-tree digest, and
the fixed scratch policy. A read outside the copied
bundle, interpreter, corpus overlay, or auxiliary inventory fails; writes are
confined to a fresh `scratch/` subtree that is never an input or output corpus
member. The shared executor must enforce that filesystem allowlist at process
boundary; a host without the configured isolation capability returns structured
unsupported rather than running the gate. The real repository and immutable B6 stage are read-only handles, not
gate working directories. The runtime verifies exact version, bundle,
entrypoint, interpreter, workspace, argv, environment, working directory, empty
stdin, revision, and tree bindings before invoking with `shell=False`, closed
inherited descriptors, timeout, resource/output limits, and only the policy
environment allowlist.

Raptor captures exit status, start/end time, warning/error counts, and
stdout/stderr digests; it does not accept tool-created evidence. After execution
it rehashes the private bundle, auxiliary inventory, and bound corpus, rejects
mutation, and removes the snapshot only after its own evidence is durable. Raw
output, if retained, lives only below the operation evidence directory and never
appears in agent responses. Remote tools are unsupported.

Each successful role returns a new `reconciled` ledger whose sorted
`compatibility_evidence` IDs append the new immutable records; it never mutates
the input ledger. Gate failure returns terminal rejection/staleness through the
shared B1 lifecycle and cannot preserve a prior certified state.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B7-D1 | Shared compatibility runtime implementing verified private-copy direct execution. |
| B7-D2 | Exact Git revision evidence and input/staged validator plus site-build evidence orchestration. |
| B7-D3 | Timeout, resource/output, descriptor, environment, mutation, retention, and redaction enforcement. |
| B7-D4 | Deterministic compatibility records linked to policy, operation, bundle inventory/version proof, gate-workspace inventory, corpus tree, and reconciled-ledger digests. |
| B7-D5 | Neutral temporary-tool integration and adversarial execution suite without consumer assets in Raptor. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B7-AC1 | Both input and staged trees have Raptor-created evidence from every policy-required validator and site-build gate, with exact revision/policy/tool-bundle inventory/version/workspace/argv/environment/working-directory bindings and zero exit/errors/warnings. |
| B7-AC2 | Missing/extra/substituted/escaping bundle members, wrong version output, shell syntax, prefix/trailing argument match, PATH fallback, undeclared environment or workspace read, stale auxiliary config, mutable/symlinked files, wrong interpreter/hash, inherited stdin/descriptors, timeout, output-limit breach, corpus mutation, and post-run bundle/workspace mutation fail closed. |
| B7-AC3 | Gate writes cannot touch the real repository, immutable stage, or auxiliary inputs; evidence binds the private workspace and exact input/staged overlay to their corpus and workspace tree digests. Tests distinguish the exact input overlay from the exact staged overlay. |
| B7-AC4 | Imported/self-reported, remote, stale, replayed-for-another-tree, partial, or warning-bearing evidence is rejected. |
| B7-AC5 | Evidence and diagnostics contain no secrets or raw tool traces; retained raw output follows the documented operation-state lifecycle. |
| B7-AC6 | External profiles/templates/tool bundles used by tests exist only in temporary neutral repositories and are never packaged as Raptor assets. |
| B7-AC7 | B7 is the sole exact Git revision-verification owner: its public API invokes the one policy-pinned revision tool, compares its commit to `MigrationOperationInput.input_revision`, and emits evidence consumed by B8/B9; no caller recreates argv, execution, parsing, or evidence logic. |

## Required validation

```sh
python -m pytest plugins/raptor/tests/migration/test_compatibility.py plugins/raptor/tests/migration/test_tool_bundle.py plugins/raptor/tests/migration/test_gate_workspace.py
python -m pytest plugins/raptor/tests/runtime plugins/raptor/tests/runner
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
rg -n 'shell\s*=\s*True|os\.system|shell=True' plugins/raptor/runtime plugins/raptor/tests/migration && exit 1 || true
```

## Traceability and non-closure

- B7-D1–D5 satisfy the trusted-execution/evidence portion of PB-REQ-005, REQ-RAP-016, and NFR-RAP-008.
- No certification decision, source replacement, migration CLI/agent activation, consumer migration, remote gate, fleet scheduler, Rust CLI/SQLx, or Dolt/MySQL.

## Handoff

B8 receives exact compatibility records linked to B6's reconciled ledger. It
may verify and compose them but may not invoke an unregistered tool or import a
consumer's self-reported result.
