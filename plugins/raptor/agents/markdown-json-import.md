---
name: markdown-json-import
version: 1.0.0
description: Extract repository Markdown into a validated JSON index.
---

# Markdown JSON Import

## Purpose
Extract the requested repository without changing its Markdown.

## Inputs
- Repository root and output index path.

## Execution Steps
From the target repository, run:

```sh
python3.11 /path/to/raptor/scripts/extract.py . --output requirements-index.json
```

## Output Format
Report records and diagnostics.

## Error Handling
Report the file, identifier, and field from each validation error.

## Constraints
Do not load SQLite or edit source Markdown.
