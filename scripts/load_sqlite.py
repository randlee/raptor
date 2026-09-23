#!/usr/bin/env python3
"""Load or dump a schema-defined SQLite index."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import raptor_schema

def fields(table: str) -> list[dict]:
    seen = set()
    return [field for field in json.loads(raptor_schema.field_table(table)) if field["name"] != "id_range" and field["level"] != "Label" and not (field["name"] in seen or seen.add(field["name"]))]


def load(index: dict, database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table'").fetchone():
            connection.executescript(raptor_schema.sql_ddl())
        for table in ("requirements", "decisions"):
            names = [field["name"] for field in fields(table)]
            marks = ", ".join("?" for _ in names)
            sql = f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) VALUES ({marks})"
            for record in index.get(table, []):
                values = [json.dumps(record[name]) if isinstance(record[name], (dict, list)) else record[name] for name in names]
                connection.execute(sql, values)


def dump(database: Path) -> dict:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        def decode(table: str, row: sqlite3.Row) -> dict:
            item = dict(row)
            for field in fields(table):
                if field["level"] == "Section" and isinstance(item[field["name"]], str) and item[field["name"]][:1] in "[{":
                    item[field["name"]] = json.loads(item[field["name"]])
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
