# Raptor Requirements

**ID Range:** REQ-RAP-0001 through REQ-RAP-0008  
**Status:** Draft  
**Created:** 2026-09-22  
**Last Updated:** 2026-09-22  
**Owner:** Rand Lee  
**Version:** 0.2.0  

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

### Requirement Statement

**MUST statements:**

- Raptor MUST store requirements, non-functional requirements, architecture
  decisions, plans, design documents, test plans, observability and reporting
  records in a Dolt database.
- Every change to a record MUST be versioned.

### Rationale

Every piece of traceability information across an organization has history.

### Success Criteria

**Acceptance Criteria:**

- [ ] A record's earlier values are retrievable after it changes.

## REQ-RAP-0002: Items are the unit of record

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Each REQ, NFR, ADR, design document and test plan MUST be one row.
- Status, Created, Last Updated and Version MUST be columns on that row,
  edited per item.

### Rationale

In Markdown these fields could only be set once per file.

### Success Criteria

**Acceptance Criteria:**

- [ ] Two items from one source file carry different Status values after
  import.

## REQ-RAP-0003: Raptor links

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Plans and other documents MUST be able to reference items by id or by URL.
- Raptor MUST resolve those links.

### Rationale

An agent can pull the referenced items into its context.

### Success Criteria

**Acceptance Criteria:**

- [ ] Given an item's id or URL, Raptor returns that item.

## REQ-RAP-0004: Queryable by product, repository and module

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Every item MUST be searchable.
- Every item MUST be filterable by product, repository and module.

### Rationale

Agents are given context scoped to the product, repository or module they
work in.

### Success Criteria

**Acceptance Criteria:**

- [ ] Given a consuming repository's `.raptor/` mapping, a query scoped to
  that repository, product or module returns only the items the mapping
  names.

## REQ-RAP-0005: Agent access

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Agents MUST read and write Raptor through the `raptor` command-line tool
  in `crates/raptor-cli`.

### Rationale

Giving agents proper context is the purpose of the product.

### Success Criteria

**Acceptance Criteria:**

- [ ] An agent reads and writes an item using no tool other than `raptor`.

## REQ-RAP-0006: Import from existing Markdown

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Each existing Markdown corpus MUST be imported once by standalone scripts.
- The output MUST be a SQLite database containing every item and header
  field the corpora have.
- Source documents MUST be corrected in their own repository rather than
  worked around in the import scripts.

### Rationale

The SQLite database is the test fixture for the product. There are several
source repositories; none is named in this repository.

### Success Criteria

**Acceptance Criteria:**

- [ ] The SQLite database holds every item and header field the corpus has.
- [ ] The scripts contain no rule specific to one repository.

## REQ-RAP-0007: Per-repository `.raptor/` folder

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- Each repository MUST store all of its Raptor-specific data in a `.raptor/`
  folder at the repository root, as TOML and other files.

### Rationale

Its primary purpose is consumption of Raptor data: mapping the repository's
code and documents to Raptor database classes and id ranges. Its secondary
purpose is ingress: configuration for importing and syncing information, such
as Markdown files, between the repository and the Raptor database.

### Success Criteria

**Acceptance Criteria:**

- [ ] No Raptor-specific file exists in a repository outside `.raptor/`.

## REQ-RAP-0008: Ingress settings

**Status:** Draft  

### Requirement Statement

**MUST statements:**

- The ingress files in a repository's `.raptor/` folder MUST declare which
  folders contain documents Raptor should ingest.
- The ingress files MUST declare a pointer to the current Raptor database:
  in production a URL that works on every computer; for test a full path,
  or better, an environment variable that names the database location.

### Rationale

Documents not under Raptor control are ignored.

### Success Criteria

**Acceptance Criteria:**

- [ ] A document outside the declared folders is not ingested.
- [ ] The database pointer resolves on a second computer without editing.
