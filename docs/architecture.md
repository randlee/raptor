# Architecture

Raptor is a Dolt database of requirements, architecture decisions, plans,
designs, tests, observability and reporting records, version controlled for
traceability and queried by agents through the `raptor` Rust CLI. See
`docs/requirements.md` and `docs/adr/adr-rap-product.md`. Neither the Dolt
schema nor the CLI exists yet; `crates/` holds stubs.

Phase A is a short-lived import bridge for the Rust product. It records the
existing documentation-index shape, loads it into development SQLite, and renders
reviewable Markdown. It does not define the product database or a Python runtime.

`crates/raptor-schema` is the only definition of a record (ADR-RAP-0004). It
emits the SQL DDL, the JSON Schema and the field table; the extractor binds a
label tree against it, the loader inserts by it, and the renderer iterates it
through one Jinja2 template per table. Until Phase B lands, `schema/record.py`
is the Phase A model the scripts still run on.

The scripts are deliberately standalone: no package, configuration system,
plugin, audit trail or transaction log is part of this bridge. Source
repositories are corrected by their owners from the importer's grouped
diagnostics rather than by adding repository-specific parsing rules here.
