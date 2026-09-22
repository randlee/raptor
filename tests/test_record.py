import json
from pathlib import Path

from schema.record import Record


def test_record_accepts_the_invented_fixture_shape() -> None:
    fixture = {
        "id": "REQ-CORE-0001", "title": "First", "type": "REQ", "status": "Draft", "domain": "core",
        "document_metadata": {"created": "2026-01-01", "last_updated": "2026-01-01", "owner": "Example", "id_range": "REQ-CORE-0001", "range_description": None},
        "source": {"file": "items.md", "section_line": 1},
        "content": {"markdown": "Body", "html": "<p>Body</p>", "summary": "Body"},
        "relationships": {"references": [], "referenced_by": [], "family": {"id_range": "REQ-CORE-0001", "members_count": 1}},
        "subsections": [],
    }
    assert Record.model_validate(fixture).id == "REQ-CORE-0001"
    assert json.loads(Path("schema/record.schema.json").read_text()) == Record.model_json_schema()
