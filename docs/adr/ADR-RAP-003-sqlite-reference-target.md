# ADR-RAP-003 — SQLite is the first persistence target

- Status: accepted

## Context

The logical artifact contract should be proven with a small, portable database
before adopting an operational version-controlled database.

## Decision

SQLite will be the first reference persistence implementation in Sprint A2.
Other SQL dialects follow only after the logical schema and conformance tests are
proven. A1 supplies no database implementation.

## Alternatives

- Implement the production database dialect first.
- Build parallel Python and Rust persistence layers.

## Consequences

- A2 owns independent SQLite DDL and a thin adapter.
- The canonical models remain independent of database libraries.
- Dialects must satisfy the same model-level conformance contract.
