import json
import sqlite3

import pytest
import raptor_schema


def test_python_api_and_structured_scalar_exception():
    expected = {"sql_ddl", "json_schema", "field_table", "validate_scalar", "accept"}
    assert {name for name in expected if callable(getattr(raptor_schema, name, None))} == expected
    assert not any(hasattr(raptor_schema, name) for name in ("bind_file", "check_inventory", "summarize"))
    sqlite3.connect(":memory:").executescript(raptor_schema.sql_ddl())
    schemas = json.loads(raptor_schema.json_schema())
    assert schemas["requirements"]["x-raptor-kinds"] == ["Req", "Nfr"]
    assert schemas["decisions"]["x-raptor-kinds"] == ["Adr"]
    for table, schema in schemas.items():
        assert schema["x-raptor-fields"] == json.loads(raptor_schema.field_table(table))
    with pytest.raises(raptor_schema.SchemaError) as caught:
        raptor_schema.validate_scalar("Date", "1900-02-29")
    error = caught.value
    assert error.category == "InvalidDate" and error.offending_value == "1900-02-29"
    assert error.table is None and error.record_position is None
    assert error.field_path == "" and error.item_index is None and error.cause and error.message
    assert raptor_schema.validate_scalar("Date", "2000-02-29") is None
    result = json.loads(raptor_schema.accept('{"requirements": [], "decisions": []}'))
    assert result == {"batch": {"requirements": [], "decisions": []}, "errors": [],
                      "summary": {"records": 0, "counts": {}}}
