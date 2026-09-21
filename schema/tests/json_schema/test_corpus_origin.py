from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from raptor_schema import SourceDocument

CORPUS = Path(__file__).parents[1] / "corpus"
ROOT = Path(__file__).parents[3]


def test_every_fixture_has_raptor_origin() -> None:
    manifest = json.loads((CORPUS / "origin-manifest.json").read_text())
    fixtures = {path.name for path in CORPUS.glob("*.json")} - {"origin-manifest.json"}
    assert set(manifest["fixtures"]) == fixtures
    sources = (ROOT / "docs/requirements.md").read_text() + "\n" + "\n".join(
        path.read_text() for path in (ROOT / "docs/adr").glob("ADR-RAP-*.md")
    )
    for origins in manifest["fixtures"].values():
        assert origins
        for artifact_id in origins:
            assert re.fullmatch(r"(?:REQ|NFR|ADR)-RAP-[0-9]{3,}", artifact_id)
            assert artifact_id in sources


def test_all_corpus_documents_validate() -> None:
    identity = json.loads((ROOT / ".raptor/identity.json").read_text())
    for path in CORPUS.glob("*.json"):
        if path.name != "origin-manifest.json":
            document = SourceDocument.model_validate_json(path.read_text())
            origin = document.provenance.origin
            materialization = document.provenance.materialization
            assert origin.repository_id == identity["repository_id"]
            assert origin.document_id in identity["documents"]
            registered_path = identity["documents"][origin.document_id]["path"]
            assert origin.initial_repository_path == registered_path
            source_bytes = (ROOT / registered_path).read_bytes()
            actual_hash = hashlib.sha256(source_bytes).hexdigest()
            assert origin.original_content_sha256 == actual_hash
            if materialization.operation == "imported":
                assert materialization.repository_path == registered_path
                assert materialization.content_sha256 == actual_hash
