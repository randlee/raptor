---
id: B.1
title: The raptor-schema crate
status: planned
branch: feature/B-1-schema-crate
worktree: ../raptor-worktrees/feature/B-1-schema-crate
target: develop
depends_on: []
---

# Sprint B.1 — The `raptor-schema` crate

The schema moves into Rust. This sprint creates `crates/raptor-schema` with
the two row types, the shared column groups and their traits, the enums,
field attributes for today's fields plus the three Phase A missed, emission
of SQL, JSON Schema and field table, the binder and its diagnostics, and a
Python module built by maturin. No Python script changes; B.2 moves the
scripts onto the crate. The contracts (field attributes, label tree,
diagnostics) are in `plan-phase-B.md` and are not restated here.

## Exact Targets

- `Cargo.toml` (workspace members and dependencies), `Cargo.lock`
- `crates/raptor-schema/Cargo.toml`, `crates/raptor-schema/src/**`,
  `crates/raptor-schema/tests/**`
- `pyproject.toml` (new, repository root)
- `.github/workflows/ci.yml` (`corpus-scripts` job only)
- `tests/fixtures/records.json` (new), `tests/test_schema.py` (new)
- `docs/adr/adr-rap-product.md` (ADR-RAP-0004 to 0006), `docs/architecture.md`

## Deliverables

### Types

- Enums and newtypes, each with serde and schemars: `Status`, `Version`
  (`X.Y.Z`, one digit each), `Date` (`YYYY-MM-DD`, validated, no date
  dependency), `Id` (`(REQ|NFR|ADR)-[A-Z]{2,5}-\d{4}`), `RecordKind`
  (from the id prefix), `Modal` (declared now, used in B.3).
- Column groups as structs, flattened into each row type with
  `#[serde(flatten)]`: `Identity {id, title}`,
  `Lifecycle {status, version, created, last_updated, owner}`,
  `Provenance {repository, path, line}`. One accessor trait per group,
  `HasIdentity`, `HasLifecycle`, `HasProvenance`, implemented by both rows.
- Row types `Requirement {identity, kind, lifecycle, provenance}` and
  `Decision {identity, lifecycle, provenance}`. A `Table` trait with the
  table name and `fields() -> Vec<FieldMeta>`.
- `FieldMeta {name, label, level, shape, section, required, sql_type}`.
  Field attributes are schemars extension keywords on each field. If the
  attribute is unavailable on fields in the schemars version used, a
  `const FIELDS: &[FieldMeta]` adjacent to each struct with a unit test
  asserting it names exactly the struct's serde fields, in order.
- Attributes for B.1: header level `Status`, `Version`, `Created`,
  `Last Updated`, `Owner`; item level `Status` (a record's own line wins
  over the header); header level `ID Range` with shape `derived`, validated
  against the record ids in the file and not stored.

### Emission

- `sql_ddl() -> String`: `requirements` and `decisions`, generated from the
  field tables, `id TEXT PRIMARY KEY`, every B.1 column `NOT NULL`, `CHECK`
  constraints from the `Status` and `RecordKind` enums. Hand-written SQL is
  a defect.
- `json_schema() -> Value`: one document, both tables, groups as `$defs`,
  field attributes as extension keywords.
- `field_table(table) -> Vec<FieldMeta>`.

### Binding and diagnostics

- `bind_file(tree, repository) -> {requirements, decisions, diagnostics}`
  over one label tree. Header-level fields inherited, item line wins.
  Rules in B.1: `MISSING_ID`, `MISSING_FIELD`, `UNKNOWN_SECTION`,
  `UNKNOWN_LABEL`, `BAD_VALUE`, with the row effects in the plan.
- `check_inventory(requirements, decisions) -> diagnostics`: `DUPLICATE_ID`
  at every occurrence.
- `summarize(diagnostics) -> {counts, groups}` in the plan's group shape.
- Every diagnostic message and remedy is a constant next to its rule.

### Python module

- Feature `python` enabling pyo3 with `abi3-py311`; module `raptor_schema`
  exposing the six functions above, JSON strings in and out.
- `pyproject.toml` at the root with the maturin backend pointing at the
  crate with `features = ["python"]`. `pip install .` builds it.
- CI `corpus-scripts`: install `maturin`, run `pip install .`, keep pytest.
  `Pydantic` leaves the install line.

### Fixture

`tests/fixtures/records.json`: `{"requirements": [...], "decisions": [...]}`,
four records in full row shape, values as the B.2 splitter will produce for
the rendered files (paths `docs/requirements/<id>.md`,
`docs/decisions/<id>.md`, heading lines). Repository
`urn:raptor:repo:fixture`.

| id | exercises |
|---|---|
| REQ-FIX-0001 | item `Status` Active over header Draft |
| NFR-FIX-0001 | kind NFR; different dates |
| ADR-FIX-0001 | decisions table |
| ADR-FIX-0002 | same owner and version as 0001, distinct dates |

### Tests

- Rust: fixture deserializes into both row types; `bind_file` over a
  hand-written tree for each fixture file equals the fixture; one test per
  rule, one tree mutation each, asserting the exact diagnostic object and the
  row effect; `sql_ddl()` executes in SQLite (rusqlite, bundled, dev only);
  `json_schema()` validates the fixture; a serde field name that has no
  attribute fails a test.
- `tests/test_schema.py`: `import raptor_schema`; `sql_ddl()` executes in
  `sqlite3`; `field_table("requirements")` lists the six labels above.

### Product documents

- `docs/adr/adr-rap-product.md` gains, in the file's existing item format:
  ADR-RAP-0004 the schema is a Rust crate and Python owns none; ADR-RAP-0005
  the record id is the primary key, version is a column, Dolt commits are
  the history; ADR-RAP-0006 edges are derived from JSON columns, integrity is
  an import diagnostic, supersession scalars are foreign keys.
- `docs/architecture.md`: the paragraph naming `schema/record.py` as
  authoritative and the sentence excluding code generation are replaced by
  two sentences naming the crate and the three emitted artifacts.

## Out of scope

Anything not named above. No change to `scripts/`, `templates/`, `schema/`
or `tests/test_scripts.py`; they still run on the Phase A shape until B.2.
No section columns, no list shapes, no edges view. No derive macro of our
own. No Dolt.

## Ceilings

Crate `src/` 450 lines; crate tests 250; `pyproject.toml` 15;
`ci.yml` diff 10 lines; `records.json` 120; `test_schema.py` 25; each ADR
item 20 lines.

## Acceptance

- `cargo fmt --check --all`, `cargo clippy --all-targets --all-features -- -D warnings`,
  `cargo test -p raptor-schema` pass.
- `pip install . && python -m pytest -q tests/test_schema.py` passes.
- Every label literal in `crates/raptor-schema/src/` occurs inside a field
  attribute or `FIELDS` table: `rg -n '"[A-Z][A-Za-z ]+"' src/` shows no
  other occurrence.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
