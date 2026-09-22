---
id: B.1
title: The raptor-schema crate
status: planned
branch: feature/b-1-schema-crate
worktree: ../raptor-worktrees/feature/b-1-schema-crate
target: develop
depends_on: []
relation: bottom of the stack; based on develop
---

# Sprint B.1 — The `raptor-schema` crate

The schema moves into Rust. This sprint creates `crates/raptor-schema` with
the two row types, the shared column groups and their traits, the enums,
field attributes for today's fields plus the three Phase A missed, emission
of SQL, JSON Schema and field table, the binder and its diagnostics, and a
Python module built by maturin. No Python script changes; B.2 moves the
scripts onto the crate. The contracts (field attributes, label tree,
diagnostics) are in `plan-phase-b.md` and the decisions in ADR-RAP-0004 to
0006; neither is restated here.

## Exact Targets

- `Cargo.toml` (workspace members and dependencies), `Cargo.lock`
- `crates/raptor-schema/Cargo.toml`, `crates/raptor-schema/src/**`,
  `crates/raptor-schema/tests/**`
- `pyproject.toml` (new, repository root)
- `.github/workflows/ci.yml` (`corpus-scripts` job only)
- `tests/fixtures/records.json` (new), `tests/test_schema.py` (new)

## Deliverables

### Types

- Enums and newtypes, each with serde and schemars: `Status`, `Version`
  (`X.Y.Z`, one digit each), `Date` (`YYYY-MM-DD`, validated, no date
  dependency), `Id` (`(REQ|NFR|ADR)-[A-Z]{2,5}-\d{4}`), `RecordKind`
  (from the id prefix), `Modal` (declared now, used in B.3).
- Column groups as structs, flattened into each row type with
  `#[serde(flatten)]`: `Identity {id, title}`,
  `Lifecycle {status, version, created, last_updated, owner}`. One accessor
  trait per group, `HasIdentity`, `HasLifecycle`, implemented by both rows.
- Row types `Requirement {identity, lifecycle}` and
  `Decision {identity, lifecycle}`. No `kind` column: the id prefix says
  REQ or NFR. No file, line or repository column: file and line live on
  diagnostics only. A `Table` trait with the table name and
  `fields() -> Vec<FieldMeta>`.
- `FieldMeta {name, label, level, shape, section, required, sql_type}`.
  Field attributes are schemars extension keywords on each field. If the
  attribute is unavailable on fields in the schemars version used, a
  `const FIELDS: &[FieldMeta]` adjacent to each struct with a unit test
  asserting it names exactly the struct's serde fields, in order.
- Attributes for B.1: header level `Status`, `Version`, `Created`,
  `Last Updated`, `Owner`; item level `Status` (a record's own line wins
  over the header); header level `ID Range` with shape `derived`, validated
  against the record ids in the file and not stored.

### Signatures

The public surface of the crate, as it must read; names are fixed, bodies
and derives are the developer's.

```rust
pub enum Status { Draft, Proposed, Active, Approved, Deprecated, Superseded }
pub enum RecordKind { Req, Nfr, Adr }
pub enum Modal { Must, Should, MustNot }
pub struct Version(String);   // X.Y.Z, one digit each
pub struct Date(String);      // YYYY-MM-DD, validated
pub struct Id(String);        // (REQ|NFR|ADR)-[A-Z]{2,5}-\d{4}
impl Id { pub fn kind(&self) -> RecordKind; }

pub enum Level { Header, Item, Section, Label }
pub enum Shape { Text, Date, Version, Status, Id, IdList, TextList,
                 StatementList, Checklist, LinkList, Group, Derived }
pub struct FieldMeta { pub name: &'static str, pub label: &'static str,
    pub level: Level, pub shape: Shape, pub section: Option<&'static str>,
    pub required: bool, pub sql_type: &'static str }

pub struct Identity { pub id: Id, pub title: String }
pub struct Lifecycle { pub status: Status, pub version: Version,
    pub created: Date, pub last_updated: Date, pub owner: String }
pub trait HasIdentity { fn identity(&self) -> &Identity; }
pub trait HasLifecycle { fn lifecycle(&self) -> &Lifecycle; }

pub struct Requirement { pub identity: Identity, pub lifecycle: Lifecycle }
pub struct Decision { pub identity: Identity, pub lifecycle: Lifecycle }
pub trait Table { const NAME: &'static str; fn fields() -> Vec<FieldMeta>; }

pub struct Diagnostic { pub file: String, pub line: u32, pub rule: Rule,
    pub id: Option<Id>, pub label: Option<String>, pub message: &'static str,
    pub allowed: Option<Vec<String>>, pub remedy: &'static str }
pub enum Rule { MissingId, MissingField, UnknownSection, UnknownLabel,
                BadValue, DuplicateId }   // DanglingReference in B.3

pub struct Bound { pub requirements: Vec<Requirement>,
    pub decisions: Vec<Decision>, pub diagnostics: Vec<Diagnostic> }
pub fn sql_ddl() -> String;
pub fn json_schema() -> serde_json::Value;
pub fn field_table(table: &str) -> Vec<FieldMeta>;
pub fn bind_file(tree: &serde_json::Value) -> Bound;
pub fn check_inventory(requirements: &[Requirement], decisions: &[Decision]) -> Vec<Diagnostic>;
pub fn summarize(diagnostics: &[Diagnostic]) -> serde_json::Value;
```

The Python module exposes the last six as functions of the same name,
taking and returning JSON strings.

### Emission

- `sql_ddl() -> String`: `requirements` and `decisions`, generated from the
  field tables, `id TEXT PRIMARY KEY`, every B.1 column `NOT NULL`, a
  `CHECK` constraint from the `Status` enum and one on `id` for the table's
  prefixes. Hand-written SQL is a defect.
- `json_schema() -> Value`: one document, both tables, groups as `$defs`,
  field attributes as extension keywords.
- `field_table(table) -> Vec<FieldMeta>`.

### Binding and diagnostics

- `bind_file(tree) -> {requirements, decisions, diagnostics}`
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
the rendered files.

| id | exercises |
|---|---|
| REQ-FIX-0001 | item `Status` Active over header Draft |
| NFR-FIX-0001 | NFR prefix in the `requirements` table; different dates |
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

## Out of scope

Anything not named above. No change to `scripts/`, `templates/`, `schema/`,
`tests/test_scripts.py` or any file under `docs/`; the scripts still run on
the Phase A shape until B.2. The decisions this crate implements are
ADR-RAP-0004 to 0006, already written. No section columns, no list shapes,
no edges view. No derive macro of our own. No Dolt.

## Ceilings

Crate `src/` 450 lines; crate tests 250; `pyproject.toml` 15;
`ci.yml` diff 10 lines; `records.json` 120; `test_schema.py` 25.

## Acceptance

- `cargo fmt --check --all`, `cargo clippy --all-targets --all-features -- -D warnings`,
  `cargo test -p raptor-schema` pass.
- `pip install . && python -m pytest -q tests/test_schema.py` passes.
- Every label literal in `crates/raptor-schema/src/` occurs inside a field
  attribute or `FIELDS` table: `rg -n '"[A-Z][A-Za-z ]+"' src/` shows no
  other occurrence.
- `rg -ni --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' .` prints nothing.
