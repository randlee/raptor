from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from raptor_schema import RepositoryRoutingConfig

ROOT = Path(__file__).parents[3]
SCHEMA = ROOT / "schema/json/v2/repository-routing-config.schema.json"


def valid_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "routes": [
            {
                "source": "requirements",
                "profile": {"profile_id": "raptor", "profile_version": "1.0.0"},
                "artifact_types": ["requirement", "non_functional_requirement"],
            }
        ],
    }


def test_generated_routing_schema_accepts_neutral_example() -> None:
    payload = valid_payload()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)
    RepositoryRoutingConfig.model_validate(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("routes", 0, "artifact_types"), []),
        (("routes", 0, "artifact_types"), ["requirement", "requirement"]),
        (("routes", 0, "artifact_types"), ["unknown"]),
        (("routes", 0, "profile", "profile_id"), "Bad Profile"),
        (("routes", 0, "profile", "profile_version"), "latest"),
    ],
)
def test_generated_routing_schema_rejects_expressible_invalid_cases(
    path: tuple[str | int, ...], value: object
) -> None:
    payload = valid_payload()
    current: object = payload
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = value  # type: ignore[index]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_generated_routing_schema_rejects_identical_routes() -> None:
    payload = valid_payload()
    route = payload["routes"][0]  # type: ignore[index]
    payload["routes"] = [route, route]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), "1.0.0\n"),
        (("routes", 0, "source"), "requirements\n"),
        (("routes", 0, "profile", "profile_id"), "raptor\n"),
        (("routes", 0, "profile", "profile_version"), "1.0.0\n"),
        (("routes", 0, "profile", "profile_version"), "1.01.0"),
        (("routes", 0, "profile", "profile_version"), "1.0.01"),
    ],
)
def test_generated_schema_rejects_non_exact_identifiers_and_versions(
    path: tuple[str | int, ...], value: str
) -> None:
    payload = valid_payload()
    current: object = payload
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = value  # type: ignore[index]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
