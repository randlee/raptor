---
name: json-validate
version: 1.0.0
description: Validate JSON index records while loading SQLite.
---

# JSON Validate

## Purpose
Load the index and report loader errors.

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
Do not edit the JSON index.
