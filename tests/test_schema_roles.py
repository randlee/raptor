"""Prove nested property spellings come from emitted semantic metadata."""

import json

import raptor_schema

from scripts.extract import split
from scripts.markdown_renderer import render
from scripts.qualify import Qualifier
from corpus_support import ROOT, project


def test_renamed_content_property_round_trips_without_python_changes(tmp_path, monkeypatch):
    definitions = json.loads(raptor_schema.json_schema())
    original = "text"
    replacement = "body_content"
    for schema in definitions.values():
        for node in schema["definitions"].values():
            if original in node.get("properties", {}):
                node["properties"][replacement] = node["properties"].pop(original)
                node["required"] = [
                    replacement if key == original else key for key in node.get("required", [])
                ]
            if node.get("x-raptor-roles", {}).get("content") == original:
                node["x-raptor-roles"]["content"] = replacement
    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())

    def rename(value):
        if isinstance(value, dict):
            return {
                replacement if key == original else key: rename(item) for key, item in value.items()
            }
        return [rename(item) for item in value] if isinstance(value, list) else value

    fixture = rename(fixture)
    root = project(tmp_path)
    monkeypatch.setattr(raptor_schema, "json_schema", lambda: json.dumps(definitions))
    for table, records in fixture.items():
        qualifier = Qualifier(root)
        for record in records:
            render(record, table, ROOT / "templates", root / "renamed", definitions)
            identifier = next(
                field["name"]
                for field in definitions[table]["x-raptor-fields"]
                if field["role"] == "heading_id"
            )
            path = root / "renamed" / table / f"{record[identifier]}.md"
            text = path.read_text()
            qualifier.qualify(split(path, text), text)
        assert qualifier.issues == []
        assert qualifier.rows[table] == records


def test_shape_tag_spellings_do_not_select_python_content_policy(tmp_path, monkeypatch):
    definitions = json.loads(raptor_schema.json_schema())
    original_fields = raptor_schema.field_table
    fields = {table: json.loads(original_fields(table)) for table in definitions}
    for table, schema in definitions.items():
        for metadata in [*schema["x-raptor-fields"], *fields[table]]:
            metadata["shape"] = "OpaqueSchemaTag"
    monkeypatch.setattr(raptor_schema, "json_schema", lambda: json.dumps(definitions))
    monkeypatch.setattr(raptor_schema, "field_table", lambda table: json.dumps(fields[table]))
    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    root = project(tmp_path)
    for table, records in fixture.items():
        qualifier = Qualifier(root)
        for record in records:
            render(record, table, ROOT / "templates", root / "opaque", definitions)
            heading = definitions[table]["x-raptor-protocol"]["heading_roles"]["identifier"]
            identifier = next(field["name"] for field in fields[table] if field["role"] == heading)
            path = root / "opaque" / table / f"{record[identifier]}.md"
            text = path.read_text()
            qualifier.qualify(split(path, text), text)
        assert qualifier.issues == []
        assert qualifier.rows[table] == records
