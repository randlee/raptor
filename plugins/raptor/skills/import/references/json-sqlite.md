# JSON → SQLite

From the target repository, load a validated index into SQLite:

```sh
python3.11 /path/to/raptor/scripts/load_sqlite.py requirements-index.json requirements.sqlite
```

The load replaces artifact and relationship rows, so rerunning it is safe.
