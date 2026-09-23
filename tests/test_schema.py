import json
import sqlite3
import raptor_schema

def test_python_api():
    sqlite3.connect(":memory:").executescript(raptor_schema.sql_ddl())
    fields = json.loads(raptor_schema.field_table("requirements"))
    assert [field["label"] for field in fields[:6]] == ["ID", "Title", "Status", "Version", "Created", "Last Updated"]
    assert [field["level"] for field in fields if field["name"] == "status"] == ["Header", "Item"]
    diagnostics = [{"file": "one.md", "line": 4, "rule": "UNKNOWN_LABEL", "id": None, "label": "Extra", "message": "ignored", "allowed": ["Status"], "remedy": "ignored"}] * 2
    summary = json.loads(raptor_schema.summarize(json.dumps(diagnostics)))
    assert summary["counts"] == {"UNKNOWN_LABEL": 2}
    assert summary["groups"] == [{"rule": "UNKNOWN_LABEL", "section": None, "label": "Extra", "allowed": ["Status"], "count": 2, "files": {"one.md": [4, 4]}, "remedy": "Remove the label or use an allowed label."}]
