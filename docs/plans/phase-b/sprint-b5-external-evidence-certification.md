# Sprint B5 — External Evidence and Corpus Certification

## Objective and stack

Close trusted compatibility evidence and the complete validate/apply certification workflow for a one-time Python corpus migration.

- `gh-stack` branch: `phase-b/05-external-evidence-certification`
- Relation: `must_follow B4`
- Merge-forward: merge pushed B4 development before every B5 development/fix round; B4 PR merges first.
- Parallel safety: not parallel-safe; certification binds B4's immutable staged tree and complete upstream ledger.

## Execution and certification contract

Raptor, not the consumer tool, creates compatibility evidence. For every allowlisted validator and site-build gate, and for both the accepted input corpus and exact staged output corpus, the shared runtime:

1. validates the B1 trust policy and canonical policy hash;
2. opens declared bundle/executable/interpreter components as no-follow regular files, copies them into a new private execution directory, fsyncs, and rehashes them;
3. prepares a private working-tree snapshot for the declared `repository_root` or `staging_root` role, overlays the exact bound corpus bytes, and verifies exact version, bundle, executable, interpreter, argv, environment, working-directory, stdin, revision, and tree bindings;
4. invokes directly in that snapshot with `shell=False`, empty stdin, closed inherited descriptors, timeout, resource/output limits, and only the policy environment allowlist, so build outputs cannot mutate the real repository or stage;
5. captures exit status, start/end times, error/warning counts, and stdout/stderr digests without accepting self-reported evidence;
6. rehashes the private bundle and bound corpus after execution, rejects modification, and destroys the snapshot only after the evidence record is durable.

Input and staged-output runs must each contain successful validator and site-build roles with zero errors and zero warnings. Remote tools are unsupported. Raw output may be retained only under the operation evidence directory according to documented retention; evidence and responses never expose secrets or raw tool traces.

`certify_migration()` verifies the complete upstream digest chain, reruns deterministic reconciliations, and emits `MigrationCertification(status="certified")`. Apply then rechecks the current input revision/tree, staged tree, trust policy/tool bytes, certification digest, proposed identity transition, and database receipt immediately before entering the existing recovery journal. Any drift returns a stable stale/conflict error and performs no replacement.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B5-D1 | Shared compatibility runtime implementing verified private-copy direct execution and B1 evidence output. |
| B5-D2 | Input and staged-output validator/site-build gate orchestration with limits, deterministic diagnostics, and evidence retention. |
| B5-D3 | Full-corpus certification verifier and `/raptor:round-trip migration` validate/apply composition through the existing agent and runner. |
| B5-D4 | Thin `migrate_corpus.py` CLI modes for validate, certify, apply, and recover; no orchestration in the script. |
| B5-D5 | Raptor-owned end-to-end corpus plus temporary neutral external-consumer integration proving public hooks without copied assets. |
| B5-D6 | Operator documentation for preparation, validation, evidence review, apply/recovery, and external-consumer handoff. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B5-AC1 | Each exact input and staged tree has Raptor-created evidence from at least one validator and one site-build tool, with exact policy/tool/argv/environment/working-directory bindings and zero exits/errors/warnings. |
| B5-AC2 | Shell syntax, argument prefix/trailing match, PATH fallback, undeclared environment, mutable/symlinked bundle files, wrong interpreter/version/hash, inherited stdin/descriptors, timeout, output-limit breach, bound-corpus mutation, and post-run bundle mutation fail closed; gate writes cannot touch the real repository/stage. |
| B5-AC3 | Imported/self-reported, remote, stale, replayed-for-another-tree, or partially successful evidence never certifies; changing any upstream digest invalidates certification. |
| B5-AC4 | Validate mode completes the full Raptor-owned corpus without changing sources, identity, or SQLite and emits deterministic ledger/evidence/certification candidates. |
| B5-AC5 | Apply accepts only a current certified ledger, replaces only the exact staged bytes, applies the reconciled identity/SQLite transition through recovery, and resumes safely after every injected crash boundary. |
| B5-AC6 | Full-corpus tests cover all five families, cross-document references, Unicode/unit kinds, persistence, one-to-one/split/combine lineage, total projection, reparse, input/output gates, stale evidence, and exact 100% reconciliation. |
| B5-AC7 | A temporary neutral consumer repository supplies its own profile, templates, operation inputs, validator/build bundle, and corpus; Raptor product fixtures/manifests/scripts contain none of its names or assets. |
| B5-AC8 | Both Claude and Codex resolve the unchanged `/raptor:round-trip` command to the same existing migration agent/runtime; scripts remain thin and all plugin/schema/template/vendor inventories pass. |
| B5-AC9 | No Rust CLI/SQLx, Dolt/MySQL, remote gate, fleet scheduler, shell invocation, secret, raw tool trace, or external-consumer fixture is introduced. |

## Required validation

```sh
python -m pytest schema/tests plugins/raptor/tests
python -m pytest plugins/raptor/tests/migration/test_compatibility.py plugins/raptor/tests/migration/test_certification.py plugins/raptor/tests/migration/test_full_corpus.py
python -m mypy --strict schema/src/raptor_schema plugins/raptor/runtime
python plugins/raptor/scripts/validate_plugin.py --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates --check-cli sc-compose --expected-range '>=1.6.1,<2.0.0'
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json --validate
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json --certify
git diff --exit-code -- schema/json/v1 plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
rg -n '\bNFT\b|sqlx|dolt://|subprocess\..*shell\s*=\s*True' schema plugins/raptor && exit 1 || true
```

Apply and crash-recovery tests operate only in temporary repositories. The repository-root commands above use validate/certify fixtures and do not replace working-tree documentation.

## Traceability and non-closure

- B5-D1–D6 satisfy PB-REQ-005 / REQ-RAP-016 and close REQ-RAP-015 and NFR-RAP-008 at full-corpus scope.
- No production migration of an external repository occurs in Raptor CI; consumers run their own pilot and retain their assets.
- No Rust CLI, Dolt/MySQL, remote attestation, continuous synchronization, web service, or multi-repository fleet orchestration.

## Phase handoff

After B5, a consumer may prepare its own repository-local profile/templates/policy/tool bundle, run the documented Python validate/certify workflow, review the canonical evidence, and explicitly apply. The next planning phase may add fleet coordination or Dolt only after a real pilot preserves these contracts.
