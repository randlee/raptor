# raptor
Requirements, architecture, plan, test, observability and reporting system for AI agent access

## Documentation import

Install the two Python dependencies before running the extractor:

```sh
pip install markdown pydantic
```

Generate the committed record schema after changing its Pydantic model:

```sh
python -c 'from schema.record import Record; import json; print(json.dumps(Record.model_json_schema(), indent=2))' > schema/record.schema.json
```

```sh
python scripts/extract.py /path/to/docs --output requirements-index.json
python scripts/load_sqlite.py requirements-index.json requirements.sqlite
python scripts/render.py requirements-index.json --output-dir rendered
```
