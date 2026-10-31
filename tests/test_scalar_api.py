import json

import pytest
import raptor_schema


def test_structured_scalar_exception_and_empty_ingress():
    with pytest.raises(raptor_schema.SchemaError) as caught:
        raptor_schema.validate_scalar("Date", "1900-02-29")
    error = caught.value
    assert error.category == "InvalidDate" and error.offending_value == "1900-02-29"
    assert error.table is None and error.record_position is None
    assert error.field_path == "" and error.item_index is None and error.cause and error.message
    assert raptor_schema.validate_scalar("Date", "2000-02-29") is None
    result = json.loads(raptor_schema.accept('{"requirements": [], "decisions": []}'))
    assert result == {
        "batch": {"requirements": [], "decisions": []},
        "errors": [],
        "summary": {"records": 0, "counts": {}},
    }


@pytest.mark.parametrize("table", ["", "Requirements", "unknown-table"])
def test_unknown_metadata_table_has_structured_exception(table):
    with pytest.raises(raptor_schema.SchemaError) as caught:
        raptor_schema.field_table(table)
    error = caught.value
    assert error.category == "UnknownVariant"
    assert error.offending_value == table
    assert error.table is None and error.record_position is None
    assert error.field_path == "" and error.item_index is None
    assert error.first_occurrence_record_position is None
    assert error.cause == "one of requirements or decisions"
    assert error.message and error.recovery
