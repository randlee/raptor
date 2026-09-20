from __future__ import annotations

import base64
import json
from pathlib import Path, PurePosixPath

import pytest
from raptor_schema.profiles import SourceInput

from runtime.profiles import RaptorMarkdownProfile


def test_reserved_block_rejects_origin_mutation(tmp_path: Path) -> None:
    profile = RaptorMarkdownProfile()
    payload = {
        "schema_version": "1.0.0",
        "origin": {
            "repository_id": "urn:raptor:repo:other",
            "document_id": "DOC-RAP-001",
            "initial_repository_path": "docs/x.md",
            "original_content_sha256": "0" * 64,
            "source_format": "markdown",
            "parser_profile": "raptor",
            "parser_profile_version": "1.0.0",
        },
        "artifacts": [],
        "parent_content_sha256": "0" * 64,
        "parser_profile": "raptor",
        "parser_profile_version": "1.0.0",
        "template_set": "raptor",
        "template_version": "1.0.0",
    }
    token = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    content = (
        f"<!-- raptor-provenance-v1:{token} -->\n# x\n### REQ-RAP-001 — X\nx\n".encode()
    )
    source = SourceInput(
        repo_root=tmp_path,
        repository_id="urn:raptor:repo:raptor",
        document_id="DOC-RAP-001",
        repository_path=PurePosixPath("docs/x.md"),
        content=content,
    )
    with pytest.raises(ValueError, match="ORIGIN_MUTATION"):
        profile.canonicalize(profile.parse(source))
