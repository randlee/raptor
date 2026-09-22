# Project Plan

The product is described in `docs/requirements.md` and `docs/adr/`. Work is
ordered so the import fixture exists before any product code is written.

| Step | Scope | State |
|---|---|---|
| Phase A | Import scripts: record model, extractor, skills, templates (`docs/phase-A/`) | Done |
| Phase B | Schema in Rust (`crates/raptor-schema`), Python importer generic over it, REQ/NFR and ADR columns, grouped diagnostics for the consumer corpus; five sprints (`docs/phase-B/`) | Planned |
| Product | Dolt schema and the Rust CLI, tested against the SQLite fixture | Not started; no sprints exist |

Only the operator adds steps to this table.
