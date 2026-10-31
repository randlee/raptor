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
    duplicate_rule = "DUPLICATE_ID"
    prior_duplicates = [
        issue
        for issue in index.get("diagnostics", {}).get("issues", [])
        if issue["rule"] == duplicate_rule
    ]
    if prior_duplicates:
        raise ValueError(json.dumps(prior_duplicates))
    submitted = {table: index.get(table, []) for table in definitions}
    accepted = json.loads(raptor_schema.accept(json.dumps(submitted)))
    rules = next(iter(definitions.values()))["x-raptor-rules"]
    duplicate_categories = rules[duplicate_rule]["categories"]
    if accepted["batch"] != submitted or any(
        error["category"] in duplicate_categories for error in accepted["errors"]
    ):
        raise ValueError(json.dumps(accepted["errors"]))
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        existing = connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table'")
        if not existing.fetchone():
            connection.executescript(raptor_schema.sql_ddl())
        for table, schema in definitions.items():
            names = list(schema["properties"])
            marks = ", ".join("?" for _ in names)
            identifier_role = schema["x-raptor-protocol"]["heading_roles"]["identifier"]
            [identifier] = [
                field["name"]
                for field in schema["x-raptor-fields"]
                if field["role"] == identifier_role
            ]
            updates = ", ".join(f"{name} = excluded.{name}" for name in names if name != identifier)
            statement = (
                f"INSERT INTO {table} ({', '.join(names)}) VALUES ({marks}) "
                f"ON CONFLICT({identifier}) DO UPDATE SET {updates}"
            )
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
