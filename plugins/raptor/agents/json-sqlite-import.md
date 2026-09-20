---
name: json-sqlite-import
version: 1.0.0
description: Persist validated canonical Raptor JSON documents through the registered SQLite adapter.
---

# JSON SQLite Import

## Purpose
Perform only canonical JSON-to-SQLite persistence activated by Sprint A4.

## Inputs
- Canonical JSON paths and repository-local SQLite path.
- `apply`: false validates; true permits one transaction.

## Execution Steps
Run `scripts/import_sqlite.py`; bootstrap the verified schema, validate all documents, then use one adapter transaction only when apply is explicit.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced validation, reference, or storage errors.

## Constraints
Do not parse or render Markdown or connect to another database.
