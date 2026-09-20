---
name: sqlite-validate
version: 1.0.0
description: Validate a repository-local Raptor SQLite store and its canonical projections.
---

# SQLite Validate

## Purpose
Perform only SQLite validation activated by Sprint A4.

## Inputs
- Repository-local SQLite path.

## Execution Steps
Bootstrap the verified schema and validate metadata, integrity, and canonical projections.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced schema, integrity, or projection errors.

## Constraints
Never mutate storage or connect to another database; do not operate before A4 activation.
