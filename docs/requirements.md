# Raptor Requirements

These artifacts are the normative product requirements for Phase A. Each has a
stable Raptor-owned identifier and an observable acceptance statement.

## Functional requirements

### REQ-RAP-001 — Canonical artifact families

Raptor shall define consumer-neutral canonical representations for requirements,
non-functional requirements, architecture decisions, design documents, and test
plans.

Acceptance: one valid instance of every family validates in a single source
document and retains its family-specific fields after canonical JSON round-trip.

### REQ-RAP-002 — Stable composite identity and provenance

Raptor shall retain repository, document, and artifact identity together with
immutable origin and current materialization provenance.

Acceptance: overlapping local IDs from two repository namespaces remain distinct,
and render transitions never rewrite origin provenance.

### REQ-RAP-003 — Executable JSON contract

Raptor shall publish installable Pydantic models and generated JSON Schemas from
one authoritative implementation under `schema/`.

Acceptance: generated schemas are reproducible and a drift check fails after any
unchecked model/schema divergence.

### REQ-RAP-004 — Source-profile diagnostics

Raptor shall define a versioned source-profile protocol whose validation produces
deterministic, structured diagnostics before canonical conversion.

Acceptance: the public profile types install independently of a concrete parser,
use recursively JSON-compatible render projections, and leave discovery, trust,
loading, and execution to the later integration runtime.

### REQ-RAP-005 — Reference persistence boundary

Raptor shall expose a model-compatible contract suitable for lossless reference
persistence without embedding a persistence DTO in the semantic model.

Acceptance: the public validation/load/dump interface is sufficient for a later
SQLite adapter to recover complete source documents without field translation.

### REQ-RAP-006 — Shared integration runtime boundary

Raptor shall permit Claude and Codex integrations to share one runtime contract
while keeping client discovery adapters thin.

Acceptance: the canonical package has no dependency on either client and exposes
only consumer-neutral Python calls.

### REQ-RAP-007 — Rendering input boundary

Raptor shall let a source profile project canonical documents into renderer input
without changing canonical semantics.

Acceptance: `SourceProfile.project_render_input` is part of the executable public
protocol and returns JSON-compatible data.

### REQ-RAP-008 — Semantic round-trip boundary

Raptor shall define semantic comparison independently of byte-for-byte Markdown
formatting.

Acceptance: `ComparableDocument` retains schema version, immutable origin, and all
canonical artifacts while excluding only documented transport variation.

### REQ-RAP-009 — Raptor-owned evidence

Raptor shall derive its in-repository examples and fixtures only from its own
requirements, non-functional requirements, and architecture decisions.

Acceptance: every fixture has an origin-manifest entry naming a `REQ-RAP-*`,
`NFR-RAP-*`, or `ADR-RAP-*` source artifact.

### REQ-RAP-010 — Explicit scan authorization

Raptor shall scan only files authorized by a valid, versioned repository scan
configuration containing non-overlapping repository-relative source roots and
include/exclude filters.

Acceptance: the executable model and generated JSON Schema reject absent or empty
source lists, traversal, absolute paths, ambiguous glob syntax, duplicates, and
overlapping roots; matching tests prove that unlisted and excluded files are not
authorized.

### REQ-RAP-011 — Complete source routing

Raptor shall bind every authorized scan source to exactly one versioned source
profile and a non-empty allowlist of canonical artifact families before parsing.

Acceptance: executable validation rejects missing, unknown, or duplicate source
routes, invalid or floating profile identities, empty or duplicate family lists,
and unsupported artifact-family values.

### REQ-RAP-012 — Explicit repository manifest

Raptor shall discover repository configuration only through a validated
`.raptor/raptor.toml` manifest that declares repository identity and explicit,
distinct scan, routing, and identity artifact paths.

Acceptance: the manifest model and generated schema reject missing, unknown,
escaping, wrongly typed, or duplicate artifact paths, and cross-file validation
rejects a repository ID that differs from the identity manifest.

## Non-functional requirements

### NFR-RAP-001 — Consumer neutrality

The canonical contract shall contain no consumer-specific identifier rule, source
fixture, adapter, or path convention.

Acceptance: the forbidden-content gate over product paths reports no external
consumer names or identifiers.

### NFR-RAP-002 — Canonical terminology

Non-functional requirements shall use `NFR` as their only abbreviation.

Acceptance: the forbidden-content gate reports no obsolete abbreviation in
product paths.

### NFR-RAP-003 — Small reference implementation

Phase A shall use a bounded Python reference implementation and shall not add a
parallel Rust persistence implementation.

Acceptance: the schema package depends only on Pydantic at runtime and product
crates contain no SQL persistence dependency.

### NFR-RAP-004 — Determinism

Canonical serialization, schema generation, comparison, and ordered collection
handling shall be deterministic.

Acceptance: repeated generation and serialization are byte-identical, with sorted
object/set-like keys and preserved authorial list order.

### NFR-RAP-005 — Versioned compatibility

Public contracts shall carry semantic versions and reject unsupported schema
major versions explicitly.

Acceptance: schema major `1` validates and every other major produces a stable
validation failure.

### NFR-RAP-006 — Independently reviewable sprints

Each sprint shall be production-ready for its stated boundary and delivered as a
separate stacked change.

Acceptance: A1 passes its authoritative checks without relying on persistence,
plugin, Markdown parser, or rendering implementation.

### NFR-RAP-007 — Platform-independent scan matching

Repository scan paths and globs shall have one case-sensitive POSIX interpretation
on every supported operating system.

Acceptance: the configuration contract specifies its complete glob dialect and
tests root-level, nested, excluded, outside-root, and invalid-pattern cases without
depending on host path matching behavior.
