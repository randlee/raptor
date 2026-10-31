# Architecture

Raptor's product is a Dolt database of requirements, architecture decisions,
plans, designs, tests, observability and reporting records, queried by agents
through a Rust CLI. See `docs/requirements.md` and
`docs/adr/adr-rap-product.md`. The product Dolt schema and CLI remain future
work; `raptor-core` and `raptor-cli` are stubs.

Phase A established a standalone import bridge into development SQLite.
Phase B replaces its Python record model with `crates/raptor-schema`, the
single definition of requirement and decision records (ADR-RAP-0004).
This import bridge does not define the product database.

The schema crate owns row types, nested shapes, canonical enums, scalar
validation and a six-attribute field table. SQL DDL, JSON Schema and field
metadata are derived from that definition. Its strict `accept` operation
checks qualified JSON, excludes invalid records individually and returns an
accepted batch plus structured errors and inventory diagnostics. The batch
has no public unchecked constructor. Rust parses no Markdown.

The Python splitter in `scripts/extract.py` knows Markdown structure and
source locations, but no field names. `scripts/qualify.py` reads schema exports,
normalizes source spellings, applies explicit repository aliases, tokenizes
links and lists, and produces canonical JSON. Scalar rules remain in Rust.
The loader inserts through the emitted schema; the renderer iterates the
field table through one Jinja2 template per table. The Python extension is
built with maturin and exposes `sql_ddl`, `json_schema`, `field_table`,
`validate_scalar` and `accept`.

Source diagnostics carry file, line, column and the offending value. The
qualifier maps Rust record/item positions back to those locations. Inventory
checks report duplicate ids and dangling references; edges derive from JSON
columns instead of being stored twice. Only the two supersession columns
are nullable and use deferred same-table foreign keys.

Consumer repositories own their source corrections and `.raptor/aliases.toml`.
Aliases may target existing canonical choices and are counted when applied;
they do not add schema vocabulary. Import validation reads consumer snapshots
without modifying their checkout. Rendered fixtures prove full-object round
trips, while hand-written documents supply diagnostic evidence. Phase B.6
and phase-ending quality approval remain gates before completion.

The bridge has no plugin runtime, audit trail, transaction log or second
schema. Keep modules focused and obey the sprint's size constraints.
