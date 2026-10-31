import json
import sqlite3

import raptor_schema


def test_python_api_and_exported_metadata():
    expected = {"sql_ddl", "json_schema", "field_table", "validate_scalar", "accept"}
    assert {name for name in expected if callable(getattr(raptor_schema, name, None))} == expected
    assert not any(
        hasattr(raptor_schema, name) for name in ("bind_file", "check_inventory", "summarize")
    )
    sqlite3.connect(":memory:").executescript(raptor_schema.sql_ddl())
    schemas = json.loads(raptor_schema.json_schema())
    assert schemas["requirements"]["x-raptor-kinds"] == ["Req", "Nfr"]
    assert schemas["decisions"]["x-raptor-kinds"] == ["Adr"]
    for table, schema in schemas.items():
        assert schema["x-raptor-fields"] == json.loads(raptor_schema.field_table(table))
