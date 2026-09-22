#!/usr/bin/env python3
"""Load a Raptor JSON index into an idempotent development SQLite database."""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = Path(__file__).parents[1] / "schema" / "schema.sql"

def records(index: dict[str, Any]) -> list[dict[str, Any]]:
    return index.get("requirements", index.get("artifacts", []))

def relationship_rows(record: dict[str, Any]):
    for group, entries in record["relationships"].items():
        if not isinstance(entries, list): continue
        for entry in entries:
            target = entry.get("target_id", entry.get("source_id"))
            if target: yield (record["id"], entry.get("type", group), target, entry.get("context"))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path); parser.add_argument("database", type=Path)
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8")); items = records(index)
    with sqlite3.connect(args.database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.execute("DELETE FROM relationships"); connection.execute("DELETE FROM artifacts")
        for item in items:
            connection.execute("INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                item["id"], item["title"], item["type"], item.get("status"), item.get("domain"),
                json.dumps(item.get("document_metadata", {})), json.dumps(item.get("source", {})),
                json.dumps(item.get("content", {})), json.dumps(item.get("subsections", []))))
            connection.executemany("INSERT INTO relationships VALUES (?, ?, ?, ?)", relationship_rows(item))
    print(f"artifacts={len(items)} database={args.database}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
