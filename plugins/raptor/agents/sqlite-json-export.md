---
name: sqlite-json-export
version: 1.0.0
description: Inspect JSON fields held by an imported SQLite record.
---

# SQLite JSON Export

## Purpose
Query a record and its JSON fields from SQLite.

## Inputs
- SQLite path and artifact identifier.

## Execution Steps
Run:

```sh
sqlite3 requirements.sqlite "SELECT id, document_metadata, source, content, subsections FROM artifacts WHERE id = 'REQ-EXAMPLE-0001';"
```

## Output Format
Return the selected row.

## Error Handling
Report SQLite errors.

## Constraints
Do not mutate storage.
