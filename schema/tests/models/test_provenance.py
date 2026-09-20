from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest
from pydantic import ValidationError

from raptor_schema import (
    SourceDocument,
    create_rendered_provenance,
    validate_provenance_transition,
)


def test_import_provenance_consistency(document_dict: dict[str, object]) -> None:
    bad = deepcopy(document_dict)
    bad["provenance"]["materialization"]["content_sha256"] = "b" * 64  # type: ignore[index]
    with pytest.raises(ValidationError, match="hashes must match"):
        SourceDocument.model_validate(bad)


@pytest.mark.parametrize("new_path", ["docs/requirements.md", "generated/requirements.md"])
def test_render_transition_preserves_origin(document_dict: dict[str, object], new_path: str) -> None:
    baseline = SourceDocument.model_validate(document_dict)
    rendered = deepcopy(document_dict)
    material = rendered["provenance"]["materialization"]  # type: ignore[index]
    material.update({  # type: ignore[union-attr]
        "repository_path": new_path,
        "content_sha256": "b" * 64,
        "operation": "rendered",
        "parent_content_sha256": "a" * 64,
        "template_set": "raptor_markdown",
        "template_version": "1.0.0",
    })
    result = SourceDocument.model_validate(rendered)
    assert result.provenance.origin == baseline.provenance.origin
    assert result.provenance.materialization.repository_path == new_path
    assert result.provenance.materialization.parent_content_sha256 == "a" * 64
    assert result.artifacts[0].source_location == baseline.artifacts[0].source_location


def test_render_requires_transition_fields(document_dict: dict[str, object]) -> None:
    rendered = deepcopy(document_dict)
    rendered["provenance"]["materialization"]["operation"] = "rendered"  # type: ignore[index]
    with pytest.raises(ValidationError, match="requires parent"):
        SourceDocument.model_validate(rendered)


def test_render_helper_recomputes_hash_and_allows_transport_location_change(document_dict: dict[str, object]) -> None:
    baseline = SourceDocument.model_validate(document_dict)
    content = b"rendered canonical document\n"
    provenance = create_rendered_provenance(
        baseline.provenance,
        repository_path="generated/requirements.md",
        content=content,
        parser_profile="raptor_dogfood",
        parser_profile_version="1.0.0",
        template_set="raptor_markdown",
        template_version="1.0.0",
    )
    assert provenance.materialization.content_sha256 == hashlib.sha256(content).hexdigest()
    assert validate_provenance_transition(baseline.provenance, provenance) is provenance
    moved = baseline.model_copy(deep=True)
    moved.provenance = provenance
    moved.artifacts[0].source_location = {"start_line": 1, "start_column": 1}  # type: ignore[assignment]
    assert moved.artifacts[0].source_location != baseline.artifacts[0].source_location
    assert moved.provenance.origin == baseline.provenance.origin


def test_origin_rewrite_and_wrong_parent_are_rejected(document: SourceDocument) -> None:
    current = create_rendered_provenance(
        document.provenance,
        repository_path="docs/requirements.md",
        content=b"rendered",
        parser_profile="raptor_dogfood",
        parser_profile_version="1.0.0",
        template_set="raptor_markdown",
        template_version="1.0.0",
    )
    rewritten = current.model_copy(
        update={"origin": current.origin.model_copy(update={"document_id": "DOC-RAP-099"})}
    )
    with pytest.raises(ValueError, match="ORIGIN_REWRITE"):
        validate_provenance_transition(document.provenance, rewritten)
    wrong_parent = current.model_copy(
        update={
            "materialization": current.materialization.model_copy(
                update={"parent_content_sha256": "c" * 64}
            )
        }
    )
    with pytest.raises(ValueError, match="PARENT_HASH"):
        validate_provenance_transition(document.provenance, wrong_parent)
