---
name: sqlite-json-export
version: 1.0.0
description: Recover canonical Raptor JSON documents from the registered SQLite adapter.
---

# SQLite JSON Export

## Purpose
Perform only SQLite-to-canonical-JSON recovery activated by Sprint A4.

## Inputs
- Repository-local SQLite path and explicit document keys.

## Execution Steps
Run `scripts/export_sqlite.py`, recover the exact composite document key, and serialize canonical JSON.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced storage or projection errors.

## Constraints
Do not parse or render Markdown or mutate storage.
