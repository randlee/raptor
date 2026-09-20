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
Bootstrap the verified schema, recover exact documents, and serialize canonical JSON.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced storage or projection errors.

## Constraints
Do not parse or render Markdown, mutate storage, or operate before A4 activation.
