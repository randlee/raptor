"""The splitter recognizes structure; Rust owns the record ID policy."""

import pytest

from corpus_support import document, qualify, replace_present


@pytest.mark.parametrize("invalid", ["REQ-FIX-12", "REQ-project-0001", "OTHER-FIX-0001"])
def test_invalid_heading_id_is_a_bad_value(document, invalid):
    root, text = document
    text = replace_present(text, "## REQ-FIX-0001:", f"## {invalid}:")
    result = qualify(root, text)
    assert any(issue["rule"] == "BAD_VALUE" for issue in result.issues)
    assert not any(issue["rule"] == "MISSING_ID" for issue in result.issues)
    assert not result.rows["requirements"]


@pytest.mark.parametrize("invalid", ["unseparated", "OTHER-FIX-0001", "REQ-FIX-abc"])
def test_every_heading_id_reaches_rust_before_routing(document, monkeypatch, invalid):
    import json
    import raptor_schema

    root, text = document
    definitions = json.loads(raptor_schema.json_schema())
    for schema in definitions.values():
        heading = next(
            field for field in schema["x-raptor-fields"] if field["role"] == "heading_id"
        )
        specification = schema["properties"][heading["name"]]
        original_kind = specification["$ref"].rsplit("/", 1)[-1]
        schema["definitions"]["HeadingIdentity"] = schema["definitions"][original_kind]
        specification["$ref"] = "#/definitions/HeadingIdentity"
    validate = raptor_schema.validate_scalar
    with pytest.raises(raptor_schema.SchemaError) as expected:
        validate(original_kind, invalid)
    calls = []

    def traced_validation(kind, value):
        calls.append((kind, value))
        return validate(original_kind if kind == "HeadingIdentity" else kind, value)

    monkeypatch.setattr(raptor_schema, "json_schema", lambda: json.dumps(definitions))
    monkeypatch.setattr(raptor_schema, "validate_scalar", traced_validation)
    text = replace_present(text, "## REQ-FIX-0001:", f"## {invalid}:")
    result = qualify(root, text)
    assert calls[0] == ("HeadingIdentity", invalid)
    assert calls.count(("HeadingIdentity", invalid)) == 1
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert issue["value"] == invalid
    assert issue["message"] == f"{expected.value.category}: {expected.value.message}"
    assert issue["allowed"] == expected.value.allowed_values
    assert not any(result.rows.values())


def test_valid_heading_is_validated_once_before_its_record_fields(document, monkeypatch):
    import json
    import raptor_schema

    root, text = document
    schema = json.loads(raptor_schema.json_schema())["requirements"]
    heading = next(field for field in schema["x-raptor-fields"] if field["role"] == "heading_id")
    scalar_kind = schema["properties"][heading["name"]]["$ref"].rsplit("/", 1)[-1]
    original = raptor_schema.validate_scalar
    calls = []

    def traced_validation(kind, value):
        calls.append((kind, value))
        return original(kind, value)

    monkeypatch.setattr(raptor_schema, "validate_scalar", traced_validation)
    result = qualify(root, text)
    assert calls[0] == (scalar_kind, "REQ-FIX-0001")
    assert calls.count((scalar_kind, "REQ-FIX-0001")) == 1
    assert result.issues == []
    assert len(result.rows["requirements"]) == 1
