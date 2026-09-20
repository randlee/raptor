# JSON → SQLite

Invoke `json-sqlite-import` through the Agent Runner with repository root, canonical JSON input, repository-local database, and validate/apply intent. The agent delegates to `scripts/import_sqlite.py`; only apply may commit one SQLite transaction.
