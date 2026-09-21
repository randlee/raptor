# Phase B — Lossless Corpus Migration Verification

## Status and authority

- Status: initial plan, ready for plan-hardening review; no implementation sprint starts until the review ledger reaches its required QA gate.
- Requirements baseline: commit `d65599fd3332fcdfa75a63913e6679a0616db065`, especially [`requirements-migration.md`](../../requirements-migration.md).
- Source of truth: this file owns phase scope and sequencing. Each linked sprint is authoritative for its deliverables, acceptance criteria, validation, and non-closure.
- Delivery model: one `gh-stack` PR per sprint, rooted at `develop`, with parent development merged forward before every child development or fix round and parent PRs merged first.
- Runtime boundary: Python one-time migration readiness only. Phase B extends the existing schema package and shared Raptor plugin runtime; it does not create a Rust CLI or a Dolt path.

## Outcome

Phase B turns the existing single-document semantic round trip into an auditable, fail-closed corpus certification workflow:

```text
repository root + explicit operation inputs
  -> manifest-selected authorized corpus
  -> versioned byte units + canonicalization proofs
  -> existing canonical JSON and SQLite store
  -> total canonical-leaf projection
  -> existing sc-compose rendering + reparse
  -> lineage-aware reconciliation
  -> Raptor-invoked validator/site-build evidence
  -> validate report or recoverable apply
```

Success is not “the command completed.” Success means every authorized input byte, every canonical leaf, every persistence transition, every output artifact, and every external gate is represented by linked canonical evidence whose hashes recompute from the exact inputs. Any missing, stale, reordered, unsupported, or mismatched boundary record prevents apply.

## Phase requirements

| ID | Requirement | Source |
|---|---|---|
| PB-REQ-001 | Publish versioned executable types and generated schemas for source units, transformations, derivations, lineage, reconciliation ledger, operation input, trust policy, and compatibility evidence. | normative definitions; NFR-RAP-008 |
| PB-REQ-002 | Resolve one deterministic authorized corpus from the repository root using only the root manifest and its selected scan, routing, identity, and profile declarations. | REQ-RAP-013 |
| PB-REQ-003 | Prove contiguous byte-unit accounting and deterministic transformation/derivation authority through canonical JSON and SQLite export. | REQ-RAP-015; NFR-RAP-008 |
| PB-REQ-004 | Prove total canonical-leaf projection, sc-compose-only document assembly, render/reparse equivalence, and versioned one-to-one/split/combine lineage reconciliation. | REQ-RAP-014; REQ-RAP-015 |
| PB-REQ-005 | Invoke trusted external validation and site-build gates for both input and exact staged output, then certify the complete corpus before apply. | REQ-RAP-016; NFR-RAP-008 |

## Reused Phase A foundation

Phase B reuses rather than replans:

- Pydantic authority and generated JSON Schema under `schema/`;
- `RepositoryConfigManifest`, scan/routing/identity models, canonical models, canonical JSON encoding, reference modes, provenance rules, and `ArtifactStore`;
- the SQLite DDL and standard-library `sqlite3` adapter;
- the shared `plugins/raptor/runtime/` implementation boundary and thin `scripts/` wrappers;
- the four public skills `/raptor:import`, `/raptor:export`, `/raptor:validate`, and `/raptor:round-trip`, their existing focused agents/runner, fenced response envelope, client parity, vendoring, and inventory gates;
- hash-verified template-set loading, sc-compose `>=1.6.1,<2.0.0`, templates, rendering, and recovery journal.

Phase B may extend these public contracts only where the migration requirements require new evidence or corpus behavior. It must not duplicate canonical models, SQL, route logic, templates, client adapters, or agent logic.

## Exact operation-input boundary

The caller creates two strict, non-source JSON inputs beneath the repository root and passes the migration input path explicitly:

```text
.raptor/operation-input/migration.json
.raptor/operation-input/trust-policy.json
```

They are operator inputs, not repository configuration or authorized corpus content; scan and tree-digest logic always excludes `.raptor/`. Unknown fields, symlinks, path escapes, floating versions, environment interpolation, and conventional fallbacks are errors. `migration.json` contains exactly:

| Field | Contract |
|---|---|
| `operation_version` | exact supported semantic version, initially `1.0.0` |
| `operation_id` | caller-supplied stable lowercase token matching `[a-z0-9][a-z0-9._-]{2,127}` |
| `mode` | `validate` or `apply`; validate is non-mutating |
| `input_revision` | exact caller-declared source-control revision; runtime also hashes the authorized corpus |
| `repository_manifest` | literal `.raptor/raptor.toml` in v1 |
| `database_path` | normalized repository-relative SQLite path |
| `reference_mode` | `batch` or `store`; `store` requires an existing initialized database |
| `staging_root` | literal `.raptor/state/migrations/<operation_id>/validation/stage/tree` in v1 |
| `template_set` | exact `name`, `version`, and manifest SHA-256 |
| `trust_policy_path` | literal `.raptor/operation-input/trust-policy.json` in v1 |
| `lineage_path` | optional explicit canonical JSON input for split/combine; omitted means generated one-to-one lineage |
| `ledger_path` | literal `.raptor/state/migrations/<operation_id>/validation/ledger.json` in v1 |
| `evidence_directory` | literal `.raptor/state/migrations/<operation_id>/evidence` in v1 |

`trust-policy.json` is a `MigrationTrustPolicy` with `policy_version`, `authority_id`, and non-empty `tools`. Each tool has one role (`revision`, `validator`, or `site_build`), stable `tool_id`, exact `tool_version`, a versioned tagged bundle root/source, complete canonical no-follow member inventory and digest, relative entrypoint, deterministic version command and exact expected output, optional interpreter pair, exact argv array, working-directory role (`repository_root` or `staging_root`), versioned environment allowlist, and a complete auxiliary gate-workspace input inventory/digest. Exactly one revision resolver and at least one tool of each gate role are required for certification. The Phase B revision resolver invokes a policy-pinned Git executable directly to obtain the exact commit; non-Git repositories are outside Phase B. Path arguments are already explicit normalized values in the policy; placeholders are unsupported. No shell, glob, regex, prefix match, trailing argument, ambient `PATH`, undeclared bundle member, undeclared workspace read, or undeclared environment variable is accepted.

No credentials are needed for the Phase B SQLite path. A future destination that needs credentials requires a separate versioned secret-reference contract; secrets never enter these JSON documents or evidence.

## Evidence chain and mutation rule

Every boundary record is canonical JSON and includes the digest of the upstream record it consumed:

```text
operation input -> ingress snapshot -> byte/unit ledger -> canonical import
  -> SQLite receipt -> canonical export -> projection receipt -> staged tree
  -> reparse/reconciliation -> input/output compatibility evidence
  -> certification
```

Validate mode may write only generated stage/evidence data below
`.raptor/state/migrations/<operation_id>/`; it never changes source Markdown,
identity, or the target SQLite database. SQLite proof runs against a private
database in that state root, initialized from or copied from the target as the
selected reference mode requires. Apply uses B9's operation-scoped migration journal
and idempotent writes to `database_path`. Certification binds the ordered
filesystem put/delete set with absence-or-digest preconditions and the exact
post-apply tree inventory; staged bytes alone never authorize a deletion. Apply
revalidates the current revision, authorized input tree, staged tree, policy,
complete tool-bundle inventories/version outputs, gate-workspace inputs, and
complete evidence chain
immediately before replacement. A changed binding makes the prepared run stale;
apply does not silently rerun or refresh evidence.

The operation-state layout and lifecycle are exactly those in
[`docs/configuration.md`](../../configuration.md#generated-runtime-state). B6
seals the validation stage and apply plan; B7/B8 add evidence/certification and
advance only the typed ledger state; only B9
creates `apply/` and journal-indexed destination siblings. Recovery locates by
operation ID alone and never scans for a plausible journal.

## Step 1 contract decisions

The guidelines pass ratifies three contracts rather than leaving them to
implementation:

1. Phase B is Git-only. B2 records the declared revision; B7 alone resolves and
   verifies it with the policy-pinned Git tool. Other sprints consume the B7
   revision evidence and never recreate that boundary. Another source-control
   system requires a later versioned resolver.
2. Split/combine requires `IdentityManifest` `2.0.0` retired-document records.
   This is necessary to prevent reuse after an input document ceases to be an
   active output.
3. Version 1 accepts only `.raptor/operation-input/migration.json` and the
   literal trust-policy path it names. Generated stages and evidence live only
   below the matching operation state root. Fixed locations make exclusion,
   recovery, and audit behavior deterministic.

## Lineage and identity policy

One-to-one output retains its `DocumentKey`. Split/combine is supported only with an explicit `CorpusLineage` and proposed identity transition:

- every input `DocumentKey` maps to one or more output keys;
- every input `ArtifactKey` maps to exactly one output key, preserving the artifact key and content;
- every output document declares its contributing input documents and one primary origin; all contributing immutable origins remain in lineage evidence and in the rendered machine-readable lineage projection;
- a reused document ID must retain its original immutable origin; every new output document ID is caller-supplied in the lineage input and appears in the proposed identity manifest—no ID is path-derived;
- input IDs not retained as outputs become explicit retired entries in the versioned identity transition, including last path, replacement IDs, operation ID, and ledger digest; retired IDs cannot be reused;
- apply performs the certified ordered filesystem puts/deletes with rollback before identity commit and deterministic roll-forward afterward, atomically replaces the manifest-selected identity file at its own journal boundary, verifies the exact final tree, then uses ordinary idempotent SQLite puts/deletes according to the reconciled lineage. It never calls a path-only move API.

B1 evolves `IdentityManifest` to identity version `2.0.0`: active `documents`
retain their Phase A shape, and `retired_documents` maps each retired document ID
to `last_path`, non-empty `replacement_document_ids`, `operation_id`, and
`ledger_sha256`. Version 1 manifests load as having no retired entries; they are
written as version 2 only by a validated B4 identity transition. Active and
retired IDs are disjoint, and retirement is irreversible.

B1 defines the evidence/transition models. B4 implements lineage planning, B5 renders the plan, B6 reconciles it, B8 certifies it, and B9 applies it. Until B9 merges, split/combine apply returns a structured unsupported error; no earlier sprint may partially mutate source/identity/database state.

## Sprint stack

| Sprint | Plan | Branch | Relation | Production closure |
|---|---|---|---|---|
| B1 | [Migration evidence contracts](sprint-b1-migration-evidence-contracts.md) | `phase-b/01-migration-evidence-contracts` | root; `must_follow develop` | Versioned ledger, lineage, trust, compatibility, identity-transition, and operation-input types/schemas. |
| B2 | [Manifest-driven corpus ingress](sprint-b2-manifest-corpus-ingress.md) | `phase-b/02-manifest-corpus-ingress` | `must_follow B1` | Deterministic repository-root inventory, profile declaration closure, selected identity propagation, and initial evidence. |
| B3 | [Lossless byte and persistence proof](sprint-b3-lossless-byte-persistence-proof.md) | `phase-b/03-lossless-byte-persistence-proof` | `must_follow B2` | Complete byte units, transformation/derivation proofs, and canonical JSON/SQLite receipts. |
| B4 | [Corpus lineage planning](sprint-b4-corpus-lineage.md) | `phase-b/04-corpus-lineage` | `must_follow B3` | One-to-one/split/combine output allocation and IdentityManifest 2.0 transition. |
| B5 | [Projection, render, and reparse](sprint-b5-projection-render-reparse.md) | `phase-b/05-projection-render-reparse` | `must_follow B4` | Total leaf/lineage projection and sc-compose-only render/reparse proof. |
| B6 | [Corpus reconciliation](sprint-b6-corpus-reconciliation.md) | `phase-b/06-corpus-reconciliation` | `must_follow B5` | Exact 100% reconciliation, immutable stage, and apply mutation plan. |
| B7 | [Trusted compatibility evidence](sprint-b7-compatibility-evidence.md) | `phase-b/07-compatibility-evidence` | `must_follow B6` | Policy-pinned input/output validator and site-build execution evidence. |
| B8 | [Full-corpus certification](sprint-b8-corpus-certification.md) | `phase-b/08-corpus-certification` | `must_follow B7` | Non-mutating certification and validate-mode public activation. |
| B9 | [Certified apply and recovery](sprint-b9-apply-recovery-handoff.md) | `phase-b/09-apply-recovery-handoff` | `must_follow B8` | Journaled apply/recovery and consumer-owned pilot handoff. |

All relations are `must_follow`: each child consumes a versioned public contract and evidence digest produced by its parent. None is `parallel_safe` because adjacent sprints intersect the same ledger schema and orchestration path. Parent development is merged forward when pushed, not after QA; PR completion remains parent-first.

## Ownership and file boundaries

Expected extension points are:

```text
schema/src/raptor_schema/migration/
schema/json/v1/*migration*.schema.json
schema/tests/migration/
plugins/raptor/runtime/{corpus,accounting,reconciliation,compatibility,migration}.py
plugins/raptor/scripts/migrate_corpus.py
plugins/raptor/tests/migration/
```

Names below these boundaries may be refined in the owning sprint, but ownership may not move into skills, agents, templates, or scripts. Schema models remain consumer-neutral. Runtime modules perform orchestration and transformation. `migrate_corpus.py` is a thin argument/envelope/exit-code wrapper. Existing `/raptor:round-trip migration` and `migration-round-trip` agent compose the runtime; Phase B adds no fifth public skill or monolithic replacement agent.

## Traceability

| Requirement | Owning sprint(s) | Phase-close evidence |
|---|---|---|
| PB-REQ-001 | B1 | installable types, generated schemas, canonical fixtures, drift tests |
| PB-REQ-002 / REQ-RAP-013 | B2 | deterministic inventory and pre-parse rejection suite |
| PB-REQ-003 | B3 | byte coverage, transform/derivation replay, SQLite receipt tests |
| PB-REQ-004 / REQ-RAP-014 | B4, B5 | lineage-aware leaf inventory and sc-compose render/reparse trace |
| PB-REQ-003, PB-REQ-004 / REQ-RAP-015 | B3–B9 | exact 100% ledger and lineage through B6, B8 certification binding, and B9 certified apply/rollback/roll-forward verification |
| PB-REQ-005 / REQ-RAP-016 | B7–B9 | Raptor-captured compatibility records, certification, and apply enforcement |
| NFR-RAP-008 | B1–B9 | digest-linked boundary records and fail-closed apply/recovery tests |

## Phase acceptance

Phase B is complete only when:

1. All nine stacked PRs satisfy their sprint acceptance criteria and merge in order.
2. One Raptor-owned multi-document corpus completes validate mode with exact 100% byte, unit, authority, leaf, persistence, lineage, render/reparse, and external-gate reconciliation.
3. One-to-one, split, and combine corpus fixtures exercise successful lineage; unregistered IDs, reused retired IDs, missing origins, duplicate/lost artifacts, and ambiguous mappings fail before apply.
4. Mutation tests independently change every evidence-chain binding and prove apply fails closed.
5. A temporary neutral external repository supplies its own profile, templates, trust policy, validator/build bundle, and corpus; Raptor invokes only public hooks and copies none of those assets into product fixtures.
6. Product and test inventories contain no external consumer name/asset, `NFT`, Dolt implementation, Rust CLI/SQLx path, shell invocation, unverified tool, or hidden conventional fallback.

## Phase-wide non-closure

- No Rust CLI, Rust migration implementation, or SQLx.
- No Dolt/MySQL DDL, adapter, connection, conformance run, branch workflow, or credentials.
- No multi-repository fleet scheduler, remote validator, service, UI, daemon, or continuous synchronization.
- No non-Git source-control revision resolver.
- No consumer-specific profile, fixture, command, site configuration, identifier convention, or copied corpus in Raptor.
- No claim that arbitrary Markdown is round-trippable; unsupported bytes/units fail closed and are reported.
- No destructive source replacement without a current, complete, trusted certification and the existing recoverable journal.

## Risks and stop conditions

| Risk | Mitigation | Stop condition |
|---|---|---|
| Semantic equality hides dropped source bytes | byte intervals cover the exact file and replayable transforms bind units to leaves | any accepted byte is absent, overlapping, or multiply disposed |
| Evidence becomes self-attestation | recompute canonical hashes and transforms from source/tool bytes at every consuming boundary | a record is trusted without recomputation |
| Corpus discovery reads unintended files | root manifest plus scan/routing/identity/profile snapshot is validated before content parsing | traversal, fallback, symlink, or multiply matched read is possible |
| Python renderer bypasses sc-compose | projection receipts and subprocess evidence bind every output to the verified executable/template set | Python assembles complete Markdown structure |
| Split/combine loses identity or origin | explicit lineage, retired-ID transition, artifact bijection, and rendered lineage block | mapping or immutable origin is ambiguous |
| External commands are mutable or consumer-specific | policy-pinned copied bundles, direct no-shell execution, neutral temporary integration tests | ambient command, undeclared bytes, or imported self-report is accepted |

## Handoff after Phase B

Phase B yields a Python certification mechanism suitable for consumer-owned
pilot repositories. Validate-mode evidence cannot authorize apply: after review,
the operator creates an apply-mode input and reruns B8 non-mutating certification;
B9 consumes that exact unchanged input/certification. A later phase may run
pilots at fleet scale or add a Dolt dialect, but it must consume the same
evidence types and persistence conformance contract and may not weaken the
fail-closed certification boundary.
