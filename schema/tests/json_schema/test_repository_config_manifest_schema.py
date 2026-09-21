from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from raptor_schema import RepositoryConfigManifest

ROOT = Path(__file__).parents[3]
SCHEMA = ROOT / "schema/json/v1/repository-config-manifest.schema.json"


def test_generated_repository_manifest_schema_accepts_neutral_example() -> None:
    payload = {
        "schema_version": "1.0.0",
        "repository_id": "urn:raptor:repo:raptor",
        "files": {
            "scan": "sources.toml",
            "routing": "routing.toml",
            "identity": "identity.json",
        },
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)
    RepositoryConfigManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", "urn:raptor:repo:raptor\n"),
        ("scan", "../sources.toml"),
        ("scan", "/sources.toml"),
        ("scan", "sources.json"),
        ("routing", "routing.json"),
        ("identity", "identity.toml"),
        ("identity", "nested\\identity.json"),
    ],
)
def test_generated_manifest_schema_rejects_expressible_invalid_values(
    field: str, value: str
) -> None:
    payload = {
        "schema_version": "1.0.0",
        "repository_id": "urn:raptor:repo:raptor",
        "files": {
            "scan": "sources.toml",
            "routing": "routing.toml",
            "identity": "identity.json",
        },
    }
    if field == "repository_id":
        payload[field] = value
    else:
        payload["files"][field] = value  # type: ignore[index]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
