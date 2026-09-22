# raptor
Requirements, architecture, plan, test, observability and reporting system for AI agent access

## Documentation import

```sh
python scripts/extract.py /path/to/docs --output requirements-index.json
python scripts/load_sqlite.py requirements-index.json requirements.sqlite
python scripts/render.py requirements-index.json --output-dir rendered
```
