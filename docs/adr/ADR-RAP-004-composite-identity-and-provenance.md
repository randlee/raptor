# ADR-RAP-004 — Composite identity and provenance

- Status: accepted

## Context

One database may contain repositories with overlapping local document and artifact
IDs, while documents may move and be regenerated over time.

## Decision

Repository/document and repository/artifact pairs are canonical keys. A committed
identity manifest is the sole identity authority. Immutable origin records the
first source; materialization provenance records current path, hash, operation,
profile, parent hash, and render template transition.

## Alternatives

- Treat artifact IDs or paths as globally unique.
- Recompute identity from Git remotes or content hashes.
- Replace provenance on every render.

## Consequences

- Clones and path moves retain stable identity.
- References always include repository identity, even within one repository.
- Semantic equality preserves origin while transition-checking materialization.
- RULE-003 and RULE-004 prohibit inferred identity and ambient resolution.
