# adr-rap-product - Product Shape Decisions

**ID Range:** ADR-RAP-0001 through ADR-RAP-0003  
**Version:** 0.1.0  
**Status:** Draft  
**Created:** 2026-09-22  
**Last Updated:** 2026-09-22  
**Owner:** Rand Lee  

## Context

Raptor replaces reading hundreds of Markdown files with querying one
version-controlled database. These decisions fix the product's shape so that
the import work stays small and the product work starts from a known target.

---

## ADR-RAP-0001: Dolt is the product store

**Status:** Draft  

### Decision

The product database is Dolt. Its built-in version control gives every
traceability record a history without a separate audit log.

### Alternatives

- SQLite: no version control; kept only as the import fixture (ADR-RAP-0003).
- Plain Git over Markdown: file-level history only, no per-item queries.

## ADR-RAP-0002: The Rust CLI is the agent interface

**Status:** Draft  

### Decision

Agents use the `raptor` command-line tool in `crates/raptor-cli` to search,
read and update items and to resolve Raptor links. No Python runtime is part
of the product.

### Alternatives

- A Python package: rejected; the Python in this repository is import-only.

## ADR-RAP-0003: Import scripts are one-time; SQLite output is a test fixture

**Status:** Draft  

### Decision

`scripts/extract.py`, `scripts/load_sqlite.py` and `scripts/render.py` import
the existing Markdown corpus into a SQLite file that contains all information
the corpus holds. That file is the fixture the product is tested against. The
scripts stay standalone, gain no framework, and are retired once the product
loads the corpus itself.

### Alternatives

- Growing the scripts into the product: rejected; that path was taken once,
  produced a large Python platform, and was removed.
