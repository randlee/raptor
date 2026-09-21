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
def run_compatibility_gates(
    *, policy: MigrationTrustPolicy, corpus_role: Literal["input", "staged"],
    bound_tree: CorpusTree, operation: MigrationOperationInput,
) -> tuple[CompatibilityEvidence, ...]: ...
```

For every policy tool and required corpus role, the runtime opens declared
bundle/executable/interpreter components as no-follow regular files, copies them
into a new private execution directory, fsyncs, and rehashes them. It prepares a
private working-tree snapshot for the declared `repository_root` or
`staging_root` role and overlays the exact bound corpus bytes. It verifies exact
version, bundle, executable, interpreter, argv, environment, working directory,
empty stdin, revision, and tree bindings before invoking with `shell=False`,
closed inherited descriptors, timeout, resource/output limits, and only the
policy environment allowlist.

Raptor captures exit status, start/end time, warning/error counts, and
stdout/stderr digests; it does not accept tool-created evidence. After execution
it rehashes the private bundle and bound corpus, rejects mutation, and removes
the snapshot only after its own evidence is durable. Raw output, if retained,
lives only below the operation evidence directory and never appears in agent
responses. Remote tools are unsupported.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B7-D1 | Shared compatibility runtime implementing verified private-copy direct execution. |
| B7-D2 | Exact Git revision evidence and input/staged validator plus site-build evidence orchestration. |
| B7-D3 | Timeout, resource/output, descriptor, environment, mutation, retention, and redaction enforcement. |
| B7-D4 | Deterministic compatibility records linked to policy, operation, corpus tree, and reconciled-ledger digests. |
| B7-D5 | Neutral temporary-tool integration and adversarial execution suite without consumer assets in Raptor. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B7-AC1 | Both input and staged trees have Raptor-created evidence from every policy-required validator and site-build gate, with exact revision/policy/tool/argv/environment/working-directory bindings and zero exit/errors/warnings. |
| B7-AC2 | Shell syntax, prefix/trailing argument match, PATH fallback, undeclared environment, mutable/symlinked files, wrong interpreter/version/hash, inherited stdin/descriptors, timeout, output-limit breach, corpus mutation, and post-run bundle mutation fail closed. |
| B7-AC3 | Gate writes cannot touch the real repository or stage; evidence binds the private snapshot role to the exact input/staged corpus tree. |
| B7-AC4 | Imported/self-reported, remote, stale, replayed-for-another-tree, partial, or warning-bearing evidence is rejected. |
| B7-AC5 | Evidence and diagnostics contain no secrets or raw tool traces; retained raw output follows the documented operation-state lifecycle. |
| B7-AC6 | External profiles/templates/tool bundles used by tests exist only in temporary neutral repositories and are never packaged as Raptor assets. |

## Required validation

```sh
python -m pytest plugins/raptor/tests/migration/test_compatibility.py
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
