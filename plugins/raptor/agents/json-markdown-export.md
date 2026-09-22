---
name: json-markdown-export
version: 1.0.0
description: Render one JSON index record to Markdown.
---

# JSON Markdown Export

## Purpose
Render the requested record using the checked-in templates.

## Inputs
- JSON index and output directory.

## Execution Steps
From the target repository, run:

```sh
python3.11 /path/to/raptor/scripts/render.py requirements-index.json --output-dir rendered
```

## Output Format
Report the rendered file.

## Error Handling
Report index, identifier, or template errors.

## Constraints
Do not alter the index.
