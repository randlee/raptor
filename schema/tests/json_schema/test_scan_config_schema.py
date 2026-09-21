from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from raptor_schema import RepositoryScanConfig

ROOT = Path(__file__).parents[3]
SCHEMA = ROOT / "schema/json/v1/repository-scan-config.schema.json"


def test_generated_scan_config_schema_accepts_neutral_example() -> None:
    payload = {
        "schema_version": "1.0.0",
        "sources": [
            {
                "name": "architecture-decisions",
                "root": "architecture/decisions",
                "include": ["*.md", "**/*.md"],
                "exclude": ["README.md", "archive/**"],
            }
        ],
    }

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(payload, schema)
    RepositoryScanConfig.model_validate(payload)


@pytest.mark.parametrize("pattern", ["../*.md", "/**/*.md", "!draft/**", "*.{md,txt}"])
def test_generated_scan_config_schema_rejects_invalid_globs(pattern: str) -> None:
    payload = {
        "schema_version": "1.0.0",
        "sources": [
            {
                "name": "requirements",
                "root": "specifications/requirements",
                "include": [pattern],
            }
        ],
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)
