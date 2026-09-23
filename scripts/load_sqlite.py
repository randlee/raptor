#!/usr/bin/env python3
"""Load or dump a schema-defined SQLite index."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import raptor_schema
if __package__:
    from .qualify import empty, resolve
else:
    from qualify import empty, resolve

def load(index: dict, database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table'").fetchone():
            connection.executescript(raptor_schema.sql_ddl())
        for table in ("requirements", "decisions"):
            schema = json.loads(raptor_schema.json_schema())[table]
            names = list(schema["properties"])
            defaults = {f["name"]: empty(schema["properties"][f["name"]], schema) for f in schema["x-raptor-fields"] if not f["required"] and f["name"] in names}
            marks = ", ".join("?" for _ in names)
            sql = f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) VALUES ({marks})"
            for record in index.get(table, []):
                canonical = {name: record.get(name) if record.get(name) is not None else defaults.get(name) for name in names}
                values = [json.dumps(canonical[name]) if isinstance(canonical[name], (dict, list)) else canonical[name] for name in names]
                connection.execute(sql, values)


def dump(database: Path) -> dict:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        def decode(table: str, row: sqlite3.Row) -> dict:
            item, schema = dict(row), json.loads(raptor_schema.json_schema())[table]
            for name, specification in schema["properties"].items():
                if resolve(specification, schema).get("type") == "object":
                    item[name] = json.loads(item[name])
            return item
        return {table: [decode(table, row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")] for table in ("requirements", "decisions")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("--dump", action="store_true")
    args = parser.parse_args()
    if args.dump:
        print(json.dumps(dump(args.paths[0])))
    else:
        load(json.loads(args.paths[0].read_text()), args.paths[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
