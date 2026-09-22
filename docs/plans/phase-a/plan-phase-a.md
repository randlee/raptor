# Phase A — Reversible Artifact Foundation

## Status and authority

- Status: A1–A8, A9, and A10 merged; A11 and A12 planned. A11/A12 implementation starts only after this plan gate passes and this PR merges.
- Source of truth: this file defines Phase A scope and ordering. Each linked sprint file is authoritative for that sprint's deliverables, acceptance criteria, and validation.
- Branch model: one `gh-stack` PR per sprint in the order below, with the stack rooted at `develop`.
- Product boundary: Raptor is a consumer-neutral system for requirements, non-functional requirements, architecture decisions, design documents, and test plans. The reference-extractor port is A11; consumer-owned corpus proof is A12; consumer migration/apply remains outside this repository.

## Outcome

Phase A delivers a small, testable reference path that can validate a repository's Markdown, convert it to canonical JSON, validate that JSON with Pydantic and JSON Schema, persist it in SQLite, render Markdown from the canonical representation, and prove semantic equivalence after reparsing.

```text
Markdown
  -> source-profile validation
  -> canonical JSON
  -> Pydantic + JSON Schema validation
  -> SQLite reference persistence
  -> canonical JSON
  -> sc-compose Markdown rendering
  -> source-profile reparse
  -> semantic equivalence
```

This establishes the contract needed to migrate 30–50 repositories without putting any consumer-specific adapter, fixture, identifier rule, or compatibility suite inside Raptor.

## Phase requirements

| ID | Requirement |
|---|---|
| PA-REQ-001 | Define one generic source-record representation: its ten fields and source Markdown survive byte-for-byte, while family content stays inside that Markdown and derived subsections. |
| PA-REQ-002 | Preserve stable repository/document/artifact composite identity, immutable origin, and current materialization provenance so artifacts remain traceable across repositories, storage, registered path changes, and rendering. |
| PA-REQ-003 | Publish Pydantic models and generated JSON Schemas from one implementation contract under top-level `schema/`. |
| PA-REQ-004 | Provide deterministic, structured source-profile validation findings before canonical conversion. |
| PA-REQ-005 | Persist and recover canonical artifacts with a minimal SQLite reference schema compatible with the models. |
| PA-REQ-006 | Package repository-neutral validation and conversion operations as one shared importable runtime with thin skill/CLI adapters discoverable by Claude and Codex. |
| PA-REQ-007 | Render Markdown through sc-compose templates that accept canonical model data. |
| PA-REQ-008 | Prove semantic round-trip equivalence after render and reparse; byte-for-byte Markdown identity is not required. |
| PA-REQ-009 | Derive in-repository examples and fixtures only from Raptor-owned `REQ-RAP-*`, `NFR-RAP-*`, and `ADR-RAP-*` artifacts. |
| PA-REQ-010 | Authorize repository scans only through a valid Raptor-owned configuration of non-overlapping roots and include/exclude filters. |
| PA-REQ-011 | Route every authorized scan source through exactly one versioned source profile and canonical artifact-family allowlist. |
| PA-REQ-012 | Discover repository configuration through an explicit root manifest whose repository identity agrees with its identity registry. |

## Quality requirements

| ID | Requirement |
|---|---|
| PA-NFR-001 | Raptor remains consumer-neutral: no external-consumer fixture, test, adapter, path convention, identifier range, or legacy spelling belongs in this repository. |
| PA-NFR-002 | `NFR` is the only canonical abbreviation for non-functional requirement; `NFT` is invalid. |
| PA-NFR-003 | Prefer a small Python reference implementation and standard-library SQLite; do not add Rust SQLx in Phase A. |
| PA-NFR-004 | Canonical serialization, schema generation, persistence, rendering inputs, and comparison are deterministic. |
| PA-NFR-005 | Public contracts are versioned and reject unsupported schema versions explicitly. |
| PA-NFR-006 | Each sprint is independently reviewable, production-ready for its stated boundary, and represented by one `gh-stack` PR. |

## Architectural decisions to record in Sprint A1

| ID | Decision boundary |
|---|---|
| ADR-RAP-001 | Canonical artifacts are consumer-neutral; source profiles and adapters stay at integration boundaries. |
| ADR-RAP-002 | Pydantic models are authoritative and JSON Schemas are generated artifacts checked for drift. |
| ADR-RAP-003 | SQLite is the Phase A reference persistence target; Dolt/MySQL follows only after the logical schema is proven. |
| ADR-RAP-004 | Composite repository/document/artifact identity and immutable origin survive storage/rendering; materialization provenance records path/hash transitions; round-trip success means semantic plus transition equivalence. |
| ADR-RAP-005 | Claude and Codex integrations share skills, agents, registry-enforcing runner, vendored schema, importable runtime, thin scripts, templates, and tests; only thin discovery/invocation adapters differ. |

## Sprint stack

| Sprint | Plan | PR branch | Relation | Closure |
|---|---|---|---|---|
| A1 | [Canonical models and JSON Schema](sprint-a1-models-and-json-schema.md) | `phase-a/01-models-and-json-schema` | root; follows `develop` | Freeze the contract in Raptor dogfood artifacts and publish the five Pydantic families, provenance types, canonical JSON, and generated schemas. |
| A2 | [SQLite reference persistence](sprint-a2-sqlite-reference.md) | `phase-a/02-sqlite-reference` | `must_follow` A1 | Prove model-compatible storage and recovery with minimal reusable tests. |
| A3 | [Plugin foundation](sprint-a3-plugin-foundation.md) | `phase-a/03-plugin-foundation` | `must_follow` A2 | Deliver discovery, router/agent contracts, deterministic vendor/bootstrap, shared runner, and thin client adapters. |
| A4 | [Validate/import/export operations](sprint-a4-plugin-operations.md) | `phase-a/04-plugin-operations` | `must_follow` A3 | Activate Markdown/JSON/SQLite validation, import, and export through six focused agents. |
| A5 | [sc-compose rendering and round-trip](sprint-a5-render-and-roundtrip.md) | `phase-a/05-render-and-roundtrip` | `must_follow` A4 | Render all five families and prove identity/provenance-aware semantic reparse equivalence. |
| A6 | [Repository scan configuration](sprint-a6-repository-scan-config.md) | `phase-a/06-repository-scan-config` | `must_follow` A5 | Publish the explicit file-scan authorization contract before adding repository traversal or routing rules. |
| A7 | [Source routing configuration](sprint-a7-source-routing-config.md) | `phase-a/07-source-routing-config` | `must_follow` A6 | Bind each authorized source to an exact profile and canonical artifact-family allowlist. |
| A8 | [Repository configuration manifest](sprint-a8-repository-manifest-config.md) | `phase-a/08-repository-manifest-config` | `must_follow` A7 | Publish the explicit root manifest and cross-file repository-identity invariant. |
| A9 | [Configured ingress and batch loss report](sprint-a9-configured-ingress.md) | `phase-a/09-configured-ingress` | `must_follow` A8 | Use validated `.raptor/` configuration to batch existing ingress operations and report every selected result. |
| A10 | [SQLite export proof](sprint-a10-sqlite-export-proof.md) | `phase-a/10-sqlite-export-proof` | `must_follow` A9 | Prove the durable SQLite→canonical JSON→sc-compose→Markdown path, including traceability projections. |
| A11 | [Reference extractor port](sprint-a11-reference-extractor-port.md) | `phase-a/11-reference-extractor-port` | `must_follow` A10 | Replace the invented native Markdown grammar, re-derive models/keys/templates from the reference extractor, and publish the consumer-neutral external-proof handoff without importing consumer assets. |
| A12 | [External corpus proof](sprint-a12-external-corpus-proof.md) | `phase-a/12-external-corpus-proof` | `must_follow` A11; commands finalized after A11 | Run the complete public-interface loop and external compatibility proof after direct extraction replaces the adapter. |

All relations are `must_follow`. The public contract or generated artifact produced by each parent is consumed by its child. Parent development must be merged forward before every child development or fix round, and parent PRs merge before child PRs.

### A1 contract supersession record

A11 replaces A1-D3's five-family field matrix with the extractor grammar and
generic record; retains A1-D4/D8's Raptor-only fixture-origin restriction while
replacing their parser/compatibility evidence; retains A1-D5 provenance and
envelope while dropping typed family payloads; and retains A1-D6 version/ID/
unknown-field checks while dropping measurements, family checks, and four
reference modes. Schema generation, plugin boundary, neutrality, and Python-only
decisions remain in force. The normative replacement is [A11](sprint-a11-reference-extractor-port.md).

## Stack workflow

Each sprint uses `gh-stack` from its named branch. The stack is rooted at `develop`; child PRs retain their stack dependency until their parent merges. The sprint plan is the PR's scope contract.

Common checks before opening or updating any sprint PR:

```sh
git status --short
gh stack status
```

No later sprint may absorb an unfinished acceptance criterion from an earlier sprint. A parent must be corrected, or the phase plan must be explicitly re-hardened.

## Boundary contracts

### Schema repository layout and dialects

Phase A uses one top-level schema project:

```text
schema/
  pyproject.toml
  src/raptor_schema/
    models/
    canonical.py
    storage/
  json/v2/
  sql/sqlite/0001_initial.sql
  tests/
    models/
    json_schema/
    storage/
```

The Pydantic model and canonical JSON contract are the semantic/logical schema. Each database target has independent DDL and an adapter that must satisfy the same persistence conformance tests. Phase A creates only `schema/sql/sqlite/`; `schema/sql/dolt/` is created in a later phase when executable Dolt DDL and its adapter are delivered, never as an empty placeholder. A11 replaces the initial schema output with `schema/json/v2/` and replacement SQLite `0001_initial.sql`; databases are regenerated from Markdown.

### Plugin layout and schema vendoring

The dual-client plugin has one implementation layout:

```text
plugins/raptor/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  plugin-manifest.json
  skills/
    import/
      SKILL.md
      references/{installation-and-troubleshooting,md-json,json-sqlite,json-dolt}.md
    export/
      SKILL.md
      references/{installation-and-troubleshooting,sqlite-json,json-md,dolt-json}.md
    validate/
      SKILL.md
      references/{installation-and-troubleshooting,markdown,json,sqlite,dolt}.md
    round-trip/
      SKILL.md
      references/installation-and-troubleshooting.md
  agents/
    registry.yaml
    markdown-json-import.md
    json-sqlite-import.md
    sqlite-json-export.md
    markdown-validate.md
    json-validate.md
    sqlite-validate.md
    json-markdown-export.md
    migration-round-trip.md
  runtime/
    __init__.py
    bootstrap.py
    agent_runner.py
    plugin_validation.py
    vendor.py
    operations.py
    identity.py
    profiles.py
    rendering.py
    transactions.py
    client_adapters/{claude,codex}.py
  scripts/
    run_agent.py
    validate_plugin.py
    vendor_schema.py
    identity.py
    markdown_to_json.py
    import_sqlite.py
    export_sqlite.py
    validate.py
    json_to_markdown.py
    render_transaction.py
  templates/
    requirement.md.j2
    non-functional-requirement.md.j2
    architecture-decision.md.j2
    design-document.md.j2
    test-plan.md.j2
  _vendor/raptor_schema/
```

The four skills are thin routers over focused reference pages; they contain no transformation logic. Focused single-responsibility execution agents perform implemented routes, with versioned YAML frontmatter and plugin-local registry path/version constraints. Shared importable behavior lives only in `plugins/raptor/runtime/`; files under `plugins/raptor/scripts/` are thin argument/exit-code wrappers that call that runtime and contain no transformation, orchestration, registry, profile-loading, rendering, or recovery logic. Shared sc-compose templates live only in `plugins/raptor/templates/`. `round-trip` composes the other routers to prove semantic migration rather than reimplementing their operations. The sole normative plugin-architecture contract is the committed [`references/claude-code-skills-agents-guidelines-v0.7.md`](references/claude-code-skills-agents-guidelines-v0.7.md); its sibling-repository path is provenance only.

The plugin namespace and stable public command surface are exactly:

```text
/raptor:import
/raptor:export
/raptor:validate
/raptor:round-trip
```

Both Claude and Codex discovery tests must resolve these names to the matching router skill directories.

Every skill/agent declares versioned YAML frontmatter. Agents return fenced standard JSON envelopes with namespaced errors and no secrets/tool traces. CLI-dependent routes verify the tool and minimum version before delegation and link `references/installation-and-troubleshooting.md`. For JSON→Markdown and round-trip, the shared `plugin-manifest.json` `requires.cli` entry named `sc-compose` is authoritative and pins `>=1.6.1,<2.0.0`; `which sc-compose && sc-compose --version` is the first executable preflight step, followed by the pinned guideline's common-location/troubleshooting path when absent. All file operations use repository-root allowlists. Mutations default to validate/dry-run and require explicit apply intent. Individual file replacement and SQLite transactions are atomic within their own resource; A5 uses a bounded durable journal with restart recovery rather than claiming atomicity across files and SQLite.

`schema/src/raptor_schema/` remains authoritative, including the executable `SourceProfile` protocol and its boundary data types. A3 owns the portable copy/hash/bootstrap contract, shared importable runtime foundation, registry-enforcing agent runner, thin CLI wrappers, and logic-free Claude/Codex adapters. A4 imports the A1 profile contract and owns only profile implementations, registry/discovery/loading, Markdown→JSON, JSON/Markdown/SQLite validation, JSON→SQLite, and SQLite→JSON. A5 adds runtime rendering/recovery behavior, JSON→Markdown, shared templates, and composed round-trip proof.

The `json-dolt`, `dolt-json`, and Dolt validation references reserve future interface semantics only. During Phase A they must clearly describe the unavailable capability and return a structured unsupported result. They may not add Dolt DDL, drivers, connections, fixtures, or tests.

### Canonical versus source-profile data

Canonical model fields describe Raptor concepts. A source profile may map repository-specific Markdown into those fields and report diagnostics, but it may not extend canonical semantics implicitly. Consumer extensions, when eventually supported, must live in an explicit namespaced extension field governed by the schema version.

Every imported document carries a stable `RepositoryId`, repository-scoped `DocumentId`, and repository-scoped artifact IDs. Canonical document/artifact keys are composite with repository identity, so one SQLite database safely holds many repositories with overlapping local IDs and paths. Immutable origin records first path/hash/profile; materialization provenance records current path/hash/profile and render transition. Preservation of original bytes is optional; preservation of immutable origin is required.

Each repository owns `.raptor/identity.json` as the stable repository/document identity authority. First import requires an explicit validate/apply registration; identity is never inferred from a path or remote. A1 owns only the manifest model/schema, conflict semantics, and Raptor dogfood validation. A2 enforces store/batch resolution on writes. A4 solely implements/tests identity registration and mode-selecting routes. A5 changes a registered path through its bounded render journal followed by ordinary idempotent `put_document`.

### Semantic round trip

The authoritative comparison is:

```python
normalize(parse(render(load(store(validate(canonicalize(parse(markdown)))))))) \
    == normalize(canonicalize(parse(markdown)))
```

Normalization may remove presentation-only variation documented by the source profile. It may not discard composite keys, canonical fields, relationships, meaningful order, or immutable origin. Current path/hash/template and transport locations are transition-validated rather than directly equal after render.

### External consumer contract

An external repository may supply Markdown adapters, profile rules, and its own fixtures, then call Raptor's public validation, conversion, persistence, rendering, and comparison interfaces. Its tests run in that consumer repository. Phase A does not copy those assets into Raptor and does not make Raptor CI depend on that repository.

## Traceability

| Requirement | Owning sprint | Evidence at phase close |
|---|---|---|
| PA-REQ-001 | A1, A11 | Pydantic API, v2 schema files, generic-record tests |
| PA-REQ-003 | A1 | Pydantic API and generated-schema publication |
| PA-REQ-002 | A1, A2, A4, A5, A10, A11 | registered repository/document identity, persisted recovery/rendered-path-update tests, and repository-scoped SQLite traceability queries |
| PA-REQ-004 | A1, A4, A11 | source-profile contract and extractor diagnostic tests |
| PA-REQ-005 | A2 | SQL migration plus store/load tests |
| PA-REQ-006 | A3, A4, A5 | shared discovery/vendor/runner foundation, importable runtime, thin CLI wrappers, and activated focused operation agents |
| PA-REQ-007 | A5 | five sc-compose templates and render tests |
| PA-REQ-008 | A5 | semantic round-trip tests for all five families |
| PA-REQ-009 | A1–A5 | fixture-origin audit tied to Raptor artifact IDs |
| PA-REQ-010 | A6 | scan configuration models, generated schema, normative requirements, and allowlist matching tests |
| PA-REQ-011 | A7 | routing models, generated schema, cross-file coverage validation, and neutral configuration examples |
| PA-REQ-012 | A8 | root manifest model/schema, typed artifact paths, and identity agreement validation |
| REQ-RAP-013 | A9 | configured batch inventory and per-path ingress report |
| REQ-RAP-014 | A10 | deterministic SQLite export, sc-compose render, field-coverage report, and reparse proof |
| REQ-RAP-015 | A10, A11, A12 | zero-loss report for canonical fields, relationships, identity, and provenance; queryable SQLite traceability checks |
| REQ-RAP-016 | A12 | Consumer template parity and external validator/secondary-gate evidence on rendered output |
| NFR-RAP-008 | A9–A12 | deterministic, fail-closed per-path and aggregate evidence |
| PA-NFR-001, PA-NFR-002 | every sprint | repository-wide forbidden-content gates |
| PA-NFR-003 | A1, A2 | bounded Python implementation; no SQLx dependency |
| PA-NFR-004, PA-NFR-005 | A1–A8 | deterministic-output and unsupported-version tests |
| PA-NFR-006 | every sprint | one reviewed stacked PR per sprint |

## Phase acceptance

Phase A is complete only when:

1. Every sprint PR has met its own acceptance criteria and merged in stack order.
2. Every supported family traverses Markdown→JSON→SQLite→JSON→sc-compose→Markdown→JSON with semantic equality after the documented materialization transition and a zero-loss report.
3. The complete authorized external consumer corpus traverses the same public interfaces through the A11 reference extractor; its validator and declared secondary gates are clean on rendered output, while consumer code and test data remain outside Raptor. The oracle is 783/783 index-equal records with zero blocked entries.
4. Repository checks find no `NFT`, Rust SQLx, Dolt integration, or bulk-migration implementation. External-consumer source, fixture, adapter, and identifier data remain absent; A12 may record only the execution coordinate and evidence contract needed for consumer-owned proof.
5. Schema, SQL, templates, plugin assets, and tests are version-aligned and documented at their public entry points.
6. Both client packages contain the same registered skills, focused references, agents, runtime modules, thin scripts, complete `.j2` inventory, schema vendor, and manifest metadata; CI fails omissions or version/path drift.

## Phase-wide non-closure

The following are intentionally deferred:

- Dolt/MySQL DDL, drivers, operational topology, branching policy, and production migration.
- Rust SQLx or any parallel Rust persistence implementation.
- migration/apply of external source repositories.
- external-consumer adapters, legacy spelling handling, identifier ranges, or Markdown fixtures. A12's consumer-owned compatibility proof is in scope, but its assets do not enter Raptor.
- byte-for-byte preservation of source Markdown formatting.
- byte-unit ledgers, transformation or derivation proofs, trust policy, tool-bundle sandboxing, corpus split/combine lineage, certification engines, and multi-resource apply/recovery orchestration.
- fleet orchestration, remote execution, registry service, web UI, authorization, and multi-tenant behavior.

## Phase risks

| Risk | Mitigation | Stop condition |
|---|---|---|
| Consumer conventions leak into canonical models | A1 ownership matrix and repo-wide forbidden-content checks | Any required canonical field exists only to satisfy one consumer. |
| Model and SQL contracts diverge | A2 uses public model dumps/loads and a reusable dialect-neutral conformance suite | A persisted valid model cannot be loaded without loss. |
| Rendering hides data loss | A5 compares semantics and validates origin/materialization transitions after reparse | Any canonical field, composite key, origin value, or transition is unaccounted for. |
| Plugin duplicates implementations | A3 owns one runtime/runner/vendor and thin client/CLI adapters; A4/A5 add behavior only to shared runtime modules | Client manifests, scripts, or agents select different policy/transformation logic. |
| Sprint scope grows into fleet migration | retain one-time batch tooling and consumer-owned proof only | Work requires consumer apply automation, fleet coordination, or Dolt operations. |

## Handoff after Phase A

The next phase may validate the logical schema against Dolt/MySQL and conduct additional consumer-owned pilots. Its entry criteria are a stable Phase A schema version, complete A9–A12 round-trip evidence, and no unresolved Phase A acceptance criterion.
