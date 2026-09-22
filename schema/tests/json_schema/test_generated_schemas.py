import json
from pathlib import Path

from raptor_schema.generate import generate_json_schemas


ROOT = Path(__file__).parents[3]
SCHEMAS = ROOT / "schema/json/v2"


def test_generated_v2_schema_inventory_is_current() -> None:
    generate_json_schemas(SCHEMAS, check=True)
    expected = {"artifact.schema.json", "identity-manifest.schema.json", "ingress-report.schema.json", "repository-config-manifest.schema.json", "repository-routing-config.schema.json", "repository-scan-config.schema.json", "source-document.schema.json"}
    assert {path.name for path in SCHEMAS.glob("*.schema.json")} == expected


def test_source_document_schema_is_v2_generic_record() -> None:
    schema = json.loads((SCHEMAS / "source-document.schema.json").read_text())
    encoded = json.dumps(schema)
    assert "2.0.0" in encoded
    assert "statement" not in encoded
    assert "Measurement" not in encoded
