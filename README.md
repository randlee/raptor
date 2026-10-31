# raptor
Requirements, architecture, plan, test, observability and reporting system for AI agent access.

## Documentation import

The Rust `raptor-schema` crate owns the record schema. Python splits and
qualifies Markdown using its exported metadata, loads SQLite, and renders
records through sc-compose templates. Install from the repository root with
the Rust toolchain available:

```sh
python -m venv .venv
. .venv/bin/activate
pip install . markdown sc-compose
```

Configure the input inventory under `.raptor/`, then run:

```sh
python scripts/extract.py --project-root . --output requirements-index.json
python scripts/load_sqlite.py requirements-index.json requirements.sqlite
python scripts/load_sqlite.py requirements.sqlite --dump
python scripts/render.py requirements-index.json --output-dir rendered
```

Extraction reports structured diagnostics and exits nonzero when issues are
present. SQLite is the import fixture; the Dolt-backed product is planned.
See [the project plan](docs/project-plan.md) for phase status.
