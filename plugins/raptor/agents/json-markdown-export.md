---
name: json-markdown-export
version: 1.0.0
description: Render one JSON index record to Markdown.
---

# JSON Markdown Export

## Purpose
Render the requested record through sc-compose and the checked-in templates.

## Inputs
- JSON index and output directory.

## Execution Steps
From the target repository, run:

```sh
python3.11 /path/to/raptor/scripts/render.py .build/requirements-index.json --id REQ-EXAMPLE-0001 --output-dir .build/rendered
```

To render every record, omit `--id`:

```sh
python3.11 /path/to/raptor/scripts/render.py .build/requirements-index.json --output-dir .build/rendered
```

## Output Format
Report the rendered file.

## Error Handling
Report index, identifier, or template errors.

## Constraints
Do not alter the index.
