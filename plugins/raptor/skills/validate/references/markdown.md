# Markdown validation

From the target repository, validate source Markdown while writing only an index:

```sh
python3.11 /path/to/raptor/scripts/extract.py . --output requirements-index.json
```

Correct every reported diagnostic in the source Markdown and rerun until clean.
