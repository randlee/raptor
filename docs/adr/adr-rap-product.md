# adr-rap-product - Product Shape Decisions

**ID Range:** ADR-RAP-0001 through ADR-RAP-0006  
**Version:** 0.2.0  
**Status:** Draft  
**Created:** 2026-09-22  
**Last Updated:** 2026-09-22  
**Decision Date:** 2026-09-22  
**Owner:** Rand Lee  

## Context

Raptor replaces reading hundreds of Markdown files with querying one
version-controlled database. These decisions fix the product's shape so that
the import work stays small and the product work starts from a known target.

---

## ADR-RAP-0001: Dolt is the product store

**Status:** Draft  

### Context

Every traceability record needs a history, and agents need to query records
rather than read files.

### Decision

The product database is Dolt.

### Rationale

Its built-in version control gives every traceability record a history
without a separate audit log.

### Consequences

**Positive:**

- Every record has history with no audit log to maintain.

**Negative:**

- The production store is a server, not a file.

### Alternatives Considered

#### Alternative 1: SQLite

**Description:** A single-file SQL database.

**Pros:**

- No server; already the import fixture.

**Cons:**

- No version control.

**Why Rejected:** No version control; kept only as the import fixture
(ADR-RAP-0003).

#### Alternative 2: Plain Git over Markdown

**Description:** Keep the Markdown files and rely on Git for history.

**Pros:**

- No new store.

**Cons:**

- File-level history only.

**Why Rejected:** No per-item queries.

## ADR-RAP-0002: The Rust CLI is the agent interface

**Status:** Draft  

### Context

Agents need to search, read and update items and to resolve Raptor links.

### Decision

Agents use the `raptor` command-line tool in `crates/raptor-cli`. No Python
runtime is part of the product.

### Rationale

One tool is the whole interface, and the Python in this repository is
import-only (ADR-RAP-0003).

### Consequences

**Positive:**

- Agents need one tool.

**Negative:**

- Nothing is usable by agents until the CLI exists.

### Alternatives Considered

#### Alternative 1: A Python package

**Description:** Ship the import models as a package agents import.

**Pros:**

- Reuses Phase A code.

**Cons:**

- Grows the scripts into a product.

**Why Rejected:** The Python in this repository is import-only.

## ADR-RAP-0003: Import scripts are one-time; SQLite output is a test fixture

**Status:** Draft  

### Context

Existing Markdown corpora must be loaded once, and the product needs a
fixture that holds real corpus data.

### Decision

`scripts/extract.py`, `scripts/load_sqlite.py` and `scripts/render.py` import
the existing Markdown corpus into a SQLite file that contains all information
the corpus holds. That file is the fixture the product is tested against. The
scripts stay standalone, gain no framework, and are retired once the product
loads the corpus itself.

### Rationale

Growing the scripts into the product was tried once, produced a large Python
platform, and was removed.

### Consequences

**Positive:**

- The product is tested against real corpus data.
- The scripts stay small.

**Negative:**

- The scripts are thrown away once the product loads the corpus itself.

### Alternatives Considered

#### Alternative 1: Growing the scripts into the product

**Description:** Extend the import scripts into the runtime.

**Pros:**

- No second implementation.

**Cons:**

- A large Python platform.

**Why Rejected:** That path was taken once, produced a large Python platform,
and was removed.

## ADR-RAP-0004: The schema is one Rust crate

**Status:** Draft  

### Context

In Phase A a field was named in seven places: model, JSON Schema, SQL,
templates, parser, loader and diagnostic rule. Each field addition cost a
sprint.

### Decision

`crates/raptor-schema` is the only definition of a record. It holds the row
types, the column groups shared between tables and reached through traits,
the enums shared by every table, and one attribute per field naming its
Markdown label, level, shape and section. The crate emits the SQL DDL, the
JSON Schema and the field table. Python reaches the crate through maturin
and owns no field name; the templates and the loader iterate the field table.

### Rationale

A field named once cannot drift, and the product's Rust code uses the same
types the importer does.

### Consequences

**Positive:**

- A field costs one attribute line, its fixture values and one template line.
- Accepting a new label is a schema change and nothing else.

**Negative:**

- The Python scripts need a Rust toolchain and maturin to run.

### Alternatives Considered

#### Alternative 1: A Pydantic model as the source of truth

**Description:** Keep `schema/record.py` authoritative and hand-write the
rest, as in Phase A.

**Pros:**

- No Rust build in the import path.

**Cons:**

- Seven places per field.

**Why Rejected:** Each field addition cost a sprint.

#### Alternative 2: Generating Rust from a schema file

**Description:** Define the schema in JSON or TOML and generate the Rust
types from it.

**Pros:**

- Schema readable without Rust.

**Cons:**

- A second notation and a translation to keep correct.

**Why Rejected:** The Rust types are the schema.

## ADR-RAP-0005: The record id is the primary key

**Status:** Draft  

### Context

A record is identified by its id, `<TYPE>-<DOMAIN>-<NNNN>`. The file, range,
registry and folder a record sits in today are where it happens to land.

### Decision

The id is the primary key of its table. The file, range, registry and folder
are not information about the record and are not stored. Version is a
column; Dolt commits are the history. Requirements and non-functional
requirements share one table, decisions have another.

### Rationale

Dolt diffs rows by primary key, and the id is what every reference in the
corpus uses.

### Consequences

**Positive:**

- A diff between Dolt commits reads as changes to named records.
- Every reference in the corpus is already a key.

**Negative:**

- Renaming a record is a delete and an insert.

### Alternatives Considered

#### Alternative 1: A surrogate key with the id as a unique index

**Description:** An integer primary key with a unique index on the id.

**Pros:**

- Renames keep history.

**Cons:**

- Dolt diffs by a number no document uses.

**Why Rejected:** The id is what the corpus and the agents use.

#### Alternative 2: One table per record kind

**Description:** Separate tables for REQ and NFR.

**Pros:**

- No kind column.

**Cons:**

- Two tables with every column the same.

**Why Rejected:** REQ and NFR share every column.

## ADR-RAP-0006: Edges are derived; integrity is a diagnostic

**Status:** Draft  

### Context

Records reference each other in id lists inside sections such as
Dependencies and Related Documents. Targets span two tables.

### Decision

References are stored once, as id lists inside the JSON column of the
section that declares them. A view `edges(source, path, target, position)`
derives every edge from those columns. A reference to an id no record
declares is an import diagnostic, `DANGLING_REFERENCE`, reported with its
file and line and never repaired by the importer. The two supersession
scalars, `supersedes` and `superseded_by`, are foreign keys into their own
table.

### Rationale

The Markdown holds each reference in one place; storing it twice invites
drift. A constraint cannot reach into a JSON array.

### Consequences

**Positive:**

- The edges view can be exported to a graph store if one is wanted.
- The edge type is the section and label the author wrote.

**Negative:**

- The database does not reject a dangling reference; the import report does.

### Alternatives Considered

#### Alternative 1: An edges table written by the importer

**Description:** The importer inserts one row per reference into an edges
table.

**Pros:**

- Foreign keys possible.

**Cons:**

- The same information twice.

**Why Rejected:** The Markdown already holds it in one place.

#### Alternative 2: Foreign keys on the id lists

**Description:** Constrain each list element to an existing id.

**Pros:**

- Integrity in the database.

**Cons:**

- Not expressible over a JSON array; targets span two tables.

**Why Rejected:** Not possible in SQL.
