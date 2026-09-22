---
name: sqlite-validate
version: 1.0.0
description: Check a Raptor SQLite database for integrity.
---

# SQLite Validate

## Purpose
Run SQLite's integrity check and report its result.

## Inputs
- SQLite database path.

## Execution Steps
Run:

```sh
sqlite3 requirements.sqlite "PRAGMA integrity_check;"
```

## Output Format
Report the integrity-check result.

## Error Handling
Report SQLite errors.

## Constraints
Do not mutate storage.
