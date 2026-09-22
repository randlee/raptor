---
name: json-sqlite-import
version: 1.0.0
description: Load a validated JSON index into SQLite.
---

# JSON SQLite Import

## Purpose
Load a validated index into the requested SQLite database.

## Inputs
- JSON index path and SQLite database path.

## Execution Steps
From the target repository, run:

```sh
python3.11 /path/to/raptor/scripts/load_sqlite.py requirements-index.json requirements.sqlite
```

## Output Format
Report the artifact count written by the loader.

## Error Handling
Report JSON or SQLite errors.

## Constraints
Do not parse or render Markdown.
