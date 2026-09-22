# Raptor Requirements

**ID Range:** REQ-RAP-0001 through REQ-RAP-0007  
**Status:** Draft  
**Created:** 2026-09-22  
**Last Updated:** 2026-09-22  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

Raptor is a Dolt database that records requirements, architecture, plans,
tests, observability and reporting for AI agent access. It is version
controlled so every piece of traceability information across an organization
has history. Plans link to REQ, ADR, NFR, design and test items by id or URL,
which is how agents are given proper context. The database is searchable and
queryable by product, repository and module.

The product has not started. The Python scripts under `scripts/` are import
scripts only. They read existing Markdown corpora, one of several source
repositories to be mined, and produce a SQLite file holding every item and
header field those corpora have today. That file is the
fixture the product is tested against. The scripts are not the product and
must not grow into one.

---

## REQ-RAP-0001: Version-controlled traceability store

**Status:** Draft  

Raptor stores requirements, non-functional requirements, architecture
decisions, plans, design documents, test plans, observability and reporting
records in a Dolt database. Every change to a record is versioned.

## REQ-RAP-0002: Items are the unit of record

**Status:** Draft  

Each REQ, NFR, ADR, design document and test plan is one row. Status, Created,
Last Updated and Version are columns on that row and are edited per item. In
Markdown these fields could only be set once per file.

## REQ-RAP-0003: Raptor links

**Status:** Draft  

Plans and other documents reference items by id or by URL. Raptor resolves
those links so an agent can pull the referenced items into its context.

## REQ-RAP-0004: Queryable by product, repository and module

**Status:** Draft  

Every item is searchable and can be filtered by product, repository and module.

## REQ-RAP-0005: Agent access

**Status:** Draft  

Agents read and write Raptor through the `raptor` command-line tool in
`crates/raptor-cli`. Giving agents proper context is the purpose of the
product.

## REQ-RAP-0006: Import from existing Markdown

**Status:** Draft  

Each existing Markdown corpus is imported once by standalone scripts. There
are several source repositories; none is named in this repository. The output
is a SQLite database containing every item and header field the corpora have,
used as the test fixture for the product. Source documents are corrected
in their own repository rather than worked around in the import scripts.

## REQ-RAP-0007: Per-repository `.raptor/` folder

**Status:** Draft  

Each repository stores all of its Raptor-specific data in a `.raptor/` folder
at the repository root, as TOML and other files. Its primary purpose is
consumption of Raptor data: mapping the repository's code and documents to
Raptor database classes and id ranges. Its secondary purpose is ingress:
configuration for importing and syncing information, such as Markdown files,
between the repository and the Raptor database.
