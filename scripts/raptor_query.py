#!/usr/bin/env python3
"""Read REQ, NFR and ADR records from a Raptor SQLite database as JSON."""

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import raptor_schema

if __package__:
    from .schema_json import resolve, schemas
    from .sqlite_records import decode
else:
    from schema_json import resolve, schemas
    from sqlite_records import decode

CONTRACT = """\
output:
  stdout carries one JSON envelope per run:
    {"success": true,  "data": <result>, "error": null}
    {"success": false, "data": null, "error": {"code": "<CODE>", "message": "<text>"}}
  get  -> data is an array of records in argument order; each record is the
          stored row (JSON columns parsed into objects and arrays) plus "type".
  list -> data is an array of {"id", "type", "title", "status"} ordered by id.
  type is the lower-case id prefix: req, nfr or adr.

exit codes: 0 success, 1 query error, 2 usage error.

error codes:
  USAGE           invalid arguments; the message names the allowed values
  DB_NOT_FOUND    --db does not name an existing file
  DB_NOT_RAPTOR   the file is not a SQLite database with the current Raptor
                  schema; rebuild it with scripts/extract.py and load_sqlite.py
  INVALID_ID      an argument is not a Raptor id (<TYPE>-<DOMAIN>-<NNNN>)
  UNKNOWN_ID      no record has the id; the message names every missing id

The database is opened read-only; this command never writes to it."""


class QueryError(Exception):
    """A failure reported to the caller as a typed error envelope."""

    def __init__(self, code, message, exit_code=1):
        super().__init__(message)
        self.code, self.message, self.exit_code = code, message, exit_code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise QueryError("USAGE", f"{self.prog}: {message}", exit_code=2)


class Catalog:
    """Tables, kinds and columns as the schema crate exports them."""

    def __init__(self):
        self.schemas = schemas()
        tables = next(iter(self.schemas.values()))["x-raptor-tables"]
        self.kinds = {
            prefix.rstrip("-").lower(): (table, prefix)
            for table in self.schemas
            for prefix in tables[table]["id_prefixes"]
        }
        heading = next(iter(self.schemas.values()))["x-raptor-protocol"]["heading_roles"]
        self.columns, choices, references = {}, [], set()
        for table, schema in self.schemas.items():
            fields = schema["x-raptor-fields"]
            [key] = {field["name"] for field in fields if field["role"] == heading["identifier"]}
            [title] = {field["name"] for field in fields if field["role"] == heading["caption"]}
            # The lifecycle state is the one property whose values are an enum.
            [(state, values)] = [
                (name, resolve(node, schema)["enum"])
                for name, node in schema["properties"].items()
                if "enum" in resolve(node, schema)
            ]
            self.columns[table] = (key, title, state)
            choices.append(values)
            references.add(schema["properties"][key]["$ref"].rsplit("/", 1)[-1])
        if len(references) != 1 or any(values != choices[0] for values in choices):
            raise ValueError("Schema tables must share one identifier and one state enum")
        [self.identifier_kind], self.states = references, choices[0]

    def kind(self, identifier):
        try:
            raptor_schema.validate_scalar(self.identifier_kind, identifier)
        except raptor_schema.SchemaError as error:
            raise QueryError("INVALID_ID", f"{identifier!r} is not a Raptor id: {error}") from None
        for kind, (table, prefix) in self.kinds.items():
            if identifier.startswith(prefix):
                return kind, table
        raise QueryError("INVALID_ID", f"{identifier!r} has no table for its prefix")


def open_readonly(path):
    """Open a SQLite file so that any write fails."""
    database = Path(path)
    if not database.is_file():
        raise QueryError("DB_NOT_FOUND", f"database file not found: {database}")
    connection = sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def get(connection, catalog, identifiers):
    resolved = [(identifier, *catalog.kind(identifier)) for identifier in identifiers]
    found = {}
    for identifier, kind, table in resolved:
        key = catalog.columns[table][0]
        row = connection.execute(f"SELECT * FROM {table} WHERE {key} = ?", (identifier,)).fetchone()
        if row is not None:
            found[identifier] = {**decode(row, catalog.schemas[table]), "type": kind}
    missing = [identifier for identifier in identifiers if identifier not in found]
    if missing:
        raise QueryError("UNKNOWN_ID", f"no record with id: {', '.join(missing)}")
    return [found[identifier] for identifier in identifiers]


def list_records(connection, catalog, kind=None, status=None):
    rows = []
    for type_name, (table, prefix) in catalog.kinds.items():
        if kind not in (None, type_name):
            continue
        key, title, state = catalog.columns[table]
        query = f"SELECT {key}, {title}, {state} FROM {table} WHERE substr({key}, 1, ?) = ?"
        parameters = [len(prefix), prefix]
        if status is not None:
            query += f" AND {state} = ?"
            parameters.append(status)
        rows += [
            (row[0], {key: row[0], "type": type_name, title: row[1], state: row[2]})
            for row in connection.execute(query, parameters)
        ]
    return [row for _, row in sorted(rows, key=lambda pair: pair[0])]


def parser(catalog):
    root = Parser(
        prog="raptor_query.py",
        description=__doc__,
        epilog=CONTRACT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = root.add_subparsers(
        dest="command", metavar="{get,list}", required=True, parser_class=Parser
    )
    get_command = commands.add_parser("get", help="records by id, in argument order")
    get_command.add_argument("ids", nargs="+", metavar="RECORD_ID")
    get_command.add_argument("--db", required=True, help="Raptor SQLite file")
    list_command = commands.add_parser("list", help="id, type, title and status of records")
    list_command.add_argument("--db", required=True, help="Raptor SQLite file")
    list_command.add_argument("--type", choices=sorted(catalog.kinds))
    list_command.add_argument("--status", choices=catalog.states)
    return root


def run(argv, catalog):
    args = parser(catalog).parse_args(argv)
    with closing(open_readonly(args.db)) as connection:
        try:
            if args.command == "get":
                return get(connection, catalog, args.ids)
            return list_records(connection, catalog, args.type, args.status)
        except sqlite3.DatabaseError as error:
            raise QueryError(
                "DB_NOT_RAPTOR",
                f"{args.db} is not a Raptor database ({error}); rebuild it with "
                "scripts/extract.py and scripts/load_sqlite.py",
            ) from None


def main(argv=None):
    try:
        data = run(sys.argv[1:] if argv is None else argv, Catalog())
    except QueryError as error:
        envelope = {"code": error.code, "message": error.message}
        print(json.dumps({"success": False, "data": None, "error": envelope}))
        return error.exit_code
    print(json.dumps({"success": True, "data": data, "error": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
