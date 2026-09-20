from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from raptor_schema import SourceDocument
from raptor_schema.generate import generate_json_schemas

ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / "schema/json/v1"


def test_checked_in_schemas_have_no_drift() -> None:
    generate_json_schemas(SCHEMAS, check=True)


def test_source_document_schema_matches_positive_case(document_dict: dict[str, object]) -> None:
    schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(document_dict, schema)
    SourceDocument.model_validate(document_dict)


@pytest.mark.parametrize(
    ("comparator", "target"),
    [("lt", "slow"), ("range", [1, 2, 3]), ("range", [1, 2.5])],
)
def test_measurement_schema_rejects_expressible_cases(
    document_dict: dict[str, object], comparator: str, target: object
) -> None:
    schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    measurement = document_dict["artifacts"][1]["measurement"]  # type: ignore[index]
    measurement.update({"comparator": comparator, "target": target})  # type: ignore[union-attr]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(document_dict, schema)


def test_identity_schema_accepts_committed_manifest() -> None:
    schema = json.loads((SCHEMAS / "identity-manifest.schema.json").read_text())
    manifest = json.loads((ROOT / ".raptor/identity.json").read_text())
    jsonschema.validate(manifest, schema)
