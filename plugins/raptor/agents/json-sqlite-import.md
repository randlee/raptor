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
Bootstrap the verified schema, validate all documents, then use one adapter transaction.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced validation, reference, or storage errors.

## Constraints
Do not parse or render Markdown, connect to another database, or operate before A4 activation.
