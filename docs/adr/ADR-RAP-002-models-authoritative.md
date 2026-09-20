# ADR-RAP-002 — Pydantic models are authoritative

- Status: accepted

## Context

Maintaining handwritten runtime models and JSON Schemas creates two contracts that
can silently diverge.

## Decision

Pydantic v2 models are authoritative. Versioned JSON Schemas are deterministic,
checked-in generated artifacts, verified by a no-diff command.

## Alternatives

- Maintain JSON Schema first and generate Python types.
- Hand-maintain both representations.

## Consequences

- Runtime-only cross-record constraints are documented beside generated schemas.
- Schema changes begin in Python and must regenerate checked-in output.
- RULE-002 requires the drift check in CI.
