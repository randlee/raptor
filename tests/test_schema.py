import json
import sqlite3
import raptor_schema

def test_python_api():
    sqlite3.connect(":memory:").executescript(raptor_schema.sql_ddl())
    fields = json.loads(raptor_schema.field_table("requirements"))
    assert [field["label"] for field in fields[:6]] == ["ID", "Title", "Status", "Version", "Created", "Last Updated"]
    assert [field["level"] for field in fields if field["name"] == "status"] == ["Header", "Item"]
