"""Strict schema-backed encoding and decoding of SQLite record rows."""

import json
import sqlite3

import raptor_schema

if __package__:
    from .schema_json import resolve, schemas
else:
    from schema_json import resolve, schemas


def load(index, database):
    definitions = schemas()
    submitted = {table: index.get(table, []) for table in definitions}
    accepted = json.loads(raptor_schema.accept(json.dumps(submitted)))
    if accepted["batch"] != submitted:
        raise ValueError(json.dumps(accepted["errors"]))
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        existing = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table'")
        if not existing.fetchone():
            connection.executescript(raptor_schema.sql_ddl())
        for table, schema in definitions.items():
            names = list(schema["properties"])
            marks = ", ".join("?" for _ in names)
            statement = f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) VALUES ({marks})"
            for record in accepted["batch"][table]:
                values = [
                    (
                        json.dumps(record[key])
                        if isinstance(record[key], (dict, list))
                        else record[key]
                    )
                    for key in names
                ]
                connection.execute(statement, values)


def dump(database):
    definitions = schemas()
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        output = {}
        for table, schema in definitions.items():
            rows = []
            for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid"):
                record = dict(row)
                for key, specification in schema["properties"].items():
                    if resolve(specification, schema).get("type") in ("object", "array"):
                        record[key] = json.loads(record[key])
                rows.append(record)
            output[table] = rows
        return output
