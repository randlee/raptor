"""Outside-repository smoke test for packaged SQLite DDL and persistence."""

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from raptor_schema import (
    DocumentKey,
    SQLiteArtifactStore,
    SourceDocument,
    dump_canonical_json,
)


store = SQLiteArtifactStore()
store.initialize()
assert store.list_artifact_keys() == []
store.close()

content_hash = hashlib.sha256(b"wheel smoke").hexdigest()
document = SourceDocument.model_validate(
    {
        "schema_version": "2.0.0",
        "provenance": {
            "origin": {
                "repository_id": "urn:raptor:repo:wheel",
                "document_id": "DOC-WHL-0001",
                "initial_repository_path": "docs/wheel.md",
                "original_content_sha256": content_hash,
                "source_format": "markdown",
                "parser_profile": "raptor",
                "parser_profile_version": "2.0.0",
            },
            "materialization": {
                "repository_path": "docs/wheel.md",
                "content_sha256": content_hash,
                "operation": "imported",
                "parser_profile": "raptor",
                "parser_profile_version": "2.0.0",
            },
        },
        "title": "Wheel smoke",
        "document_metadata": {"Owner": "Raptor"},
        "non_item_segments": [
            {"kind": "text", "content": "# Wheel smoke\n\n"},
            {"kind": "artifact", "artifact_index": 0},
        ],
        "artifacts": [
            {
                "artifact_type": "requirement",
                "id": "REQ-WHL-0001",
                "title": "Wheel smoke",
                "status": "Approved",
                "domain": "schema",
                "source": {"heading": "REQ-WHL-0001: Wheel smoke", "heading_level": 2},
                "content": "\nPersist outside the source tree.\n",
                "relationships": [],
                "subsections": [],
                "source_location": {
                    "start_line": 3,
                    "start_column": 1,
                    "end_line": 4,
                    "end_column": 1,
                },
            }
        ],
    }
)
with TemporaryDirectory() as directory:
    database = Path(directory) / "wheel.db"
    file_store = SQLiteArtifactStore(database)
    file_store.initialize()
    file_store.put_document(document)
    file_store.close()
    reopened = SQLiteArtifactStore(database)
    reopened.initialize()
    recovered = reopened.get_document(
        DocumentKey(repository_id="urn:raptor:repo:wheel", document_id="DOC-WHL-0001")
    )
    assert dump_canonical_json(recovered) == dump_canonical_json(document)
    reopened.close()
