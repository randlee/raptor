# ADR-RAP-001 — Consumer-neutral canonical contract

- Status: accepted

## Context

Many repositories use different Markdown conventions for the same underlying
artifact concepts. Encoding one convention in Raptor would prevent reuse.

## Decision

Canonical artifact models contain only Raptor semantics. Source profiles own
parsing, validation, normalization, and renderer projection at the integration
boundary. Extra consumer data requires an explicit namespaced extension.

## Alternatives

- Adopt the first consumer's document shapes as canonical.
- Keep arbitrary source dictionaries without a typed canonical layer.

## Consequences

- New consumers implement profiles rather than changing core fields.
- Canonical validation cannot promise fidelity for undeclared presentation data.
- RULE-001 forbids consumer adapters and Markdown parsers in the schema package.
