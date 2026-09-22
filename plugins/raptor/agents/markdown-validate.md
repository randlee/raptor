---
name: markdown-validate
version: 1.0.0
description: Validate repository Markdown by extracting its records.
---

# Markdown Validate

## Purpose
Run the extractor and report its diagnostics.

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
Report the file, identifier, and field from each error.

## Constraints
Do not edit source Markdown.
