# JSON → Markdown

From the target repository, render one index record through sc-compose:

```sh
python3.11 /path/to/raptor/scripts/render.py .build/requirements-index.json --id REQ-EXAMPLE-0001 --output-dir .build/rendered
```

To render every record, omit `--id`:

```sh
python3.11 /path/to/raptor/scripts/render.py .build/requirements-index.json --output-dir .build/rendered
```
