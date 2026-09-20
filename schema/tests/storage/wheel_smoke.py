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
        "schema_version": "1.0.0",
        "provenance": {
            "origin": {
                "repository_id": "urn:raptor:repo:wheel",
                "document_id": "DOC-WHL-001",
                "initial_repository_path": "docs/wheel.md",
                "original_content_sha256": content_hash,
                "source_format": "markdown",
                "parser_profile": "wheel_smoke",
                "parser_profile_version": "1.0.0",
            },
            "materialization": {
                "repository_path": "docs/wheel.md",
                "content_sha256": content_hash,
                "operation": "imported",
                "parser_profile": "wheel_smoke",
                "parser_profile_version": "1.0.0",
            },
        },
        "artifacts": [
            {
                "artifact_type": "requirement",
                "id": "REQ-WHL-001",
                "title": "Wheel smoke",
                "status": "accepted",
                "relationships": [],
                "extensions": {},
                "statement": "Persist outside the source tree.",
                "acceptance_criteria": ["Reopen and recover."],
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
        DocumentKey(repository_id="urn:raptor:repo:wheel", document_id="DOC-WHL-001")
    )
    assert dump_canonical_json(recovered) == dump_canonical_json(document)
    reopened.close()
