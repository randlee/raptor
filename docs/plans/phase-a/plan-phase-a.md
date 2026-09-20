# Phase A — Reversible Artifact Foundation

## Status and authority

- Status: planning; no implementation sprint may start until plan hardening passes.
- Source of truth: this file defines Phase A scope and ordering. Each linked sprint file is authoritative for that sprint's deliverables, acceptance criteria, and validation.
- Branch model: one `gh-stack` PR per sprint in the order below, with the stack rooted at `develop`.
- Product boundary: Raptor is a consumer-neutral system for requirements, non-functional requirements, architecture decisions, design documents, and test plans. P3 Documentation is only the first external consumer.

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
| PA-REQ-001 | Define canonical representations for Requirement, NonFunctionalRequirement, ArchitectureDecision, DesignDocument, and TestPlan. |
| PA-REQ-002 | Preserve stable repository/document/artifact composite identity, immutable origin, and current materialization provenance so artifacts remain traceable across repositories, storage, moves, and rendering. |
| PA-REQ-003 | Publish Pydantic models and generated JSON Schemas from one implementation contract under top-level `schema/`. |
| PA-REQ-004 | Provide deterministic, structured source-profile validation findings before canonical conversion. |
| PA-REQ-005 | Persist and recover canonical artifacts with a minimal SQLite reference schema compatible with the models. |
| PA-REQ-006 | Package repository-neutral validation and conversion operations as one shared skill/scripts implementation discoverable by Claude and Codex. |
| PA-REQ-007 | Render Markdown through sc-compose templates that accept canonical model data. |
| PA-REQ-008 | Prove semantic round-trip equivalence after render and reparse; byte-for-byte Markdown identity is not required. |
| PA-REQ-009 | Derive in-repository examples and fixtures only from Raptor-owned `REQ-RAP-*`, `NFR-RAP-*`, and `ADR-RAP-*` artifacts. |

## Quality requirements

| ID | Requirement |
|---|---|
| PA-NFR-001 | Raptor remains consumer-neutral: no `p3-documentation` fixture, test, adapter, path convention, identifier range, or legacy spelling belongs in this repository. |
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
| ADR-RAP-005 | Claude and Codex integrations share skills, agents, registry-enforcing runner, vendored runtime, scripts, templates, and tests; only thin discovery/invocation adapters differ. |

## Sprint stack

| Sprint | Plan | PR branch | Relation | Closure |
|---|---|---|---|---|
| A1 | [Canonical models and JSON Schema](sprint-a1-models-and-json-schema.md) | `phase-a/01-models-and-json-schema` | root; follows `develop` | Freeze the contract in Raptor dogfood artifacts and publish the five Pydantic families, provenance types, canonical JSON, and generated schemas. |
| A2 | [SQLite reference persistence](sprint-a2-sqlite-reference.md) | `phase-a/02-sqlite-reference` | `must_follow` A1 | Prove model-compatible storage and recovery with minimal reusable tests. |
| A3 | [Plugin foundation](sprint-a3-plugin-foundation.md) | `phase-a/03-plugin-foundation` | `must_follow` A2 | Deliver discovery, router/agent contracts, deterministic vendor/bootstrap, shared runner, and thin client adapters. |
| A4 | [Validate/import/export operations](sprint-a4-plugin-operations.md) | `phase-a/04-plugin-operations` | `must_follow` A3 | Activate Markdown/JSON/SQLite validation, import, and export through six focused agents. |
| A5 | [sc-compose rendering and round-trip](sprint-a5-render-and-roundtrip.md) | `phase-a/05-render-and-roundtrip` | `must_follow` A4 | Render all five families and prove identity/provenance-aware semantic reparse equivalence. |

All relations are `must_follow`. The public contract or generated artifact produced by each parent is consumed by its child. Parent development must be merged forward before every child development or fix round, and parent PRs merge before child PRs.

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
  json/v1/
  sql/sqlite/0001_initial.sql
  tests/
    models/
    json_schema/
    storage/
```

The Pydantic model and canonical JSON contract are the semantic/logical schema. Each database target has independent DDL and an adapter that must satisfy the same persistence conformance tests. Phase A creates only `schema/sql/sqlite/`; `schema/sql/dolt/` is created in a later phase when executable Dolt DDL and its adapter are delivered, never as an empty placeholder.

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
  scripts/
    _bootstrap.py
    agent_runner.py
    validate_plugin.py
    client_adapters/{claude,codex}.py
  templates/
  _vendor/raptor_schema/
```

The four skills are thin routers over focused reference pages; they contain no transformation logic. Focused single-responsibility execution agents perform implemented routes, with versioned YAML frontmatter and plugin-local registry path/version constraints. Shared Python implementation lives only in `plugins/raptor/scripts/`, and shared sc-compose templates live only in `plugins/raptor/templates/`. `round-trip` composes the other routers to prove semantic migration rather than reimplementing their operations. The sole normative plugin-architecture contract is the committed [`references/claude-code-skills-agents-guidelines-v0.7.md`](references/claude-code-skills-agents-guidelines-v0.7.md); its sibling-repository path is provenance only.

The plugin namespace and stable public command surface are exactly:

```text
/raptor:import
/raptor:export
/raptor:validate
/raptor:round-trip
```

Both Claude and Codex discovery tests must resolve these names to the matching router skill directories.

Every skill/agent declares versioned YAML frontmatter. Agents return fenced standard JSON envelopes with namespaced errors and no secrets/tool traces. CLI-dependent routes verify the tool and minimum version before delegation and link `references/installation-and-troubleshooting.md`; this is mandatory for `sc-compose` on JSON→Markdown and round-trip routes. All file operations use repository-root allowlists. Mutations default to validate/dry-run, require explicit apply intent, and use atomic writes or transactions.

`schema/src/raptor_schema/` remains authoritative. A3 owns the exact-copy/hash/bootstrap contract, shared registry-enforcing agent runner, and logic-free Claude/Codex adapters. A4 activates Markdown→JSON, JSON/Markdown/SQLite validation, JSON→SQLite, and SQLite→JSON. A5 implements JSON→Markdown, shared templates, and composed round-trip proof.

The `json-dolt`, `dolt-json`, and Dolt validation references reserve future interface semantics only. During Phase A they must clearly describe the unavailable capability and return a structured unsupported result. They may not add Dolt DDL, drivers, connections, fixtures, or tests.

### Canonical versus source-profile data

Canonical model fields describe Raptor concepts. A source profile may map repository-specific Markdown into those fields and report diagnostics, but it may not extend canonical semantics implicitly. Consumer extensions, when eventually supported, must live in an explicit namespaced extension field governed by the schema version.

Every imported document carries a stable `RepositoryId`, repository-scoped `DocumentId`, and repository-scoped artifact IDs. Canonical document/artifact keys are composite with repository identity, so one SQLite database safely holds many repositories with overlapping local IDs and paths. Immutable origin records first path/hash/profile; materialization provenance records current path/hash/profile and render transition. Preservation of original bytes is optional; preservation of immutable origin is required.

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
| PA-REQ-001, PA-REQ-003 | A1 | Pydantic API, schema files, family tests |
| PA-REQ-002 | A1, A2, A5 | composite identity/provenance model, persisted recovery/move tests, render-transition proof |
| PA-REQ-004 | A1, A4 | concrete source-profile contract and structured diagnostic route tests |
| PA-REQ-005 | A2 | SQL migration plus store/load tests |
| PA-REQ-006 | A3, A4, A5 | shared discovery/vendor/runner foundation and activated focused operation agents |
| PA-REQ-007 | A5 | five sc-compose templates and render tests |
| PA-REQ-008 | A5 | semantic round-trip tests for all five families |
| PA-REQ-009 | A1–A5 | fixture-origin audit tied to Raptor artifact IDs |
| PA-NFR-001, PA-NFR-002 | every sprint | repository-wide forbidden-content gates |
| PA-NFR-003 | A1, A2 | bounded Python implementation; no SQLx dependency |
| PA-NFR-004, PA-NFR-005 | A1–A5 | deterministic-output and unsupported-version tests |
| PA-NFR-006 | every sprint | one reviewed stacked PR per sprint |

## Phase acceptance

Phase A is complete only when:

1. Every sprint PR has met its own acceptance criteria and merged in stack order.
2. A Raptor-owned Markdown artifact can traverse the complete pipeline and return semantically equivalent canonical JSON.
3. The same public interfaces can be invoked by an external consumer without adding consumer-specific code or test data to Raptor.
4. Repository checks find no `NFT`, `p3-documentation`, P3-specific identifiers, Rust SQLx, Dolt integration, or bulk-migration implementation in Phase A artifacts.
5. Schema, SQL, templates, plugin assets, and tests are version-aligned and documented at their public entry points.
6. Both client packages contain the same registered skills, focused references, agents, scripts, complete `.j2` inventory, schema vendor, and manifest metadata; CI fails omissions or version/path drift.

## Phase-wide non-closure

The following are intentionally deferred:

- Dolt/MySQL DDL, drivers, operational topology, branching policy, and production migration.
- Rust SQLx or any parallel Rust persistence implementation.
- migration of P3 Documentation or any of the 30–50 source repositories.
- P3 adapters, legacy `NRF` handling, identifier ranges, Markdown fixtures, or compatibility tests.
- byte-for-byte preservation of source Markdown formatting.
- fleet orchestration, remote execution, registry service, web UI, authorization, and multi-tenant behavior.

## Phase risks

| Risk | Mitigation | Stop condition |
|---|---|---|
| Consumer conventions leak into canonical models | A1 ownership matrix and repo-wide forbidden-content checks | Any required canonical field exists only to satisfy one consumer. |
| Model and SQL contracts diverge | A2 uses public model dumps/loads and a reusable dialect-neutral conformance suite | A persisted valid model cannot be loaded without loss. |
| Rendering hides data loss | A5 compares semantics and validates origin/materialization transitions after reparse | Any canonical field, composite key, origin value, or transition is unaccounted for. |
| Plugin duplicates implementations | A3 owns one runner/vendor and thin client adapters; A4/A5 use shared scripts | Client manifests or agents select different policy/transformation logic. |
| Sprint scope grows into fleet migration | enforce Phase-wide non-closure and re-harden before expansion | Work requires consumer repository changes or Dolt operations. |

## Handoff after Phase A

The next phase may validate the logical schema against Dolt/MySQL and conduct consumer-owned pilots. Its entry criteria are a stable Phase A schema version, published compatibility policy, complete round-trip evidence, and no unresolved Phase A acceptance criterion.
