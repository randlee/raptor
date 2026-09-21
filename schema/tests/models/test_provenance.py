from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest
from pydantic import ValidationError

from raptor_schema import (
    MaterializationProvenance,
    OriginProvenance,
    SourceDocument,
    SourceProvenance,
    validate_provenance_transition,
)


def rendered_provenance(
    document: SourceDocument, *, content: bytes, path: str = "docs/requirements.md"
) -> SourceProvenance:
    return SourceProvenance(
        origin=document.provenance.origin,
        materialization=MaterializationProvenance(
            repository_path=path,
            content_sha256=hashlib.sha256(content).hexdigest(),
            operation="rendered",
            parent_content_sha256=document.provenance.materialization.content_sha256,
            parser_profile="raptor_dogfood",
            parser_profile_version="1.0.0",
            template_set="raptor_markdown",
            template_version="1.0.0",
        ),
    )


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("content_sha256", "b" * 64, "hashes must match"),
        ("repository_path", "docs/other.md", "paths must match"),
    ],
)
def test_import_provenance_consistency(
    document_dict: dict[str, object], field: str, value: object, error: str
) -> None:
    bad = deepcopy(document_dict)
    bad["provenance"]["materialization"][field] = value  # type: ignore[index]
    with pytest.raises(ValidationError, match=error):
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
    provenance = rendered_provenance(
        baseline, content=content, path="generated/requirements.md"
    )
    assert provenance.materialization.content_sha256 == hashlib.sha256(content).hexdigest()
    assert validate_provenance_transition(baseline.provenance, provenance) is provenance
    moved = baseline.model_copy(deep=True, update={"provenance": provenance})
    moved.artifacts[0].source_location = {"start_line": 1, "start_column": 1}  # type: ignore[assignment]
    assert moved.artifacts[0].source_location != baseline.artifacts[0].source_location
    assert moved.provenance.origin == baseline.provenance.origin


def test_origin_rewrite_and_wrong_parent_are_rejected(document: SourceDocument) -> None:
    current = rendered_provenance(document, content=b"rendered")
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", "urn:raptor:repo:other"),
        ("document_id", "DOC-RAP-099"),
        ("initial_repository_path", "docs/other.md"),
        ("original_content_sha256", "b" * 64),
        ("source_format", "markdown"),
        ("parser_profile", "other_profile"),
        ("parser_profile_version", "1.1.0"),
    ],
)
def test_origin_provenance_rejects_assignment(
    document: SourceDocument, field: str, value: object
) -> None:
    with pytest.raises(ValidationError, match="frozen"):
        setattr(document.provenance.origin, field, value)


def test_origin_and_document_provenance_reject_whole_replacement(
    document: SourceDocument,
) -> None:
    other_origin = document.provenance.origin.model_copy(
        update={"document_id": "DOC-RAP-099"}
    )
    with pytest.raises(ValidationError, match="frozen"):
        setattr(document.provenance, "origin", other_origin)
    other_provenance = document.provenance.model_copy(update={"origin": other_origin})
    with pytest.raises(ValidationError, match="frozen"):
        setattr(document, "provenance", other_provenance)


def imported_materialization() -> dict[str, object]:
    return {
        "repository_path": "docs/requirements.md",
        "content_sha256": "a" * 64,
        "operation": "imported",
        "parser_profile": "raptor_dogfood",
        "parser_profile_version": "1.0.0",
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"repository_path": "../escape.md"},
        {"content_sha256": "ABC"},
        {"parser_profile": "Bad Profile"},
        {"parser_profile_version": "1"},
        {"parent_content_sha256": "b" * 64},
        {"template_set": "raptor_markdown"},
        {"template_version": "1.0.0"},
    ],
)
def test_imported_materialization_negative_matrix(updates: dict[str, object]) -> None:
    value = imported_materialization()
    value.update(updates)
    with pytest.raises(ValidationError):
        MaterializationProvenance.model_validate(value)


@pytest.mark.parametrize(
    "missing",
    ["parent_content_sha256", "template_set", "template_version"],
)
def test_rendered_materialization_required_matrix(missing: str) -> None:
    value = {
        **imported_materialization(),
        "operation": "rendered",
        "parent_content_sha256": "a" * 64,
        "template_set": "raptor_markdown",
        "template_version": "1.0.0",
    }
    value.pop(missing)
    with pytest.raises(ValidationError):
        MaterializationProvenance.model_validate(value)


def test_rendered_materialization_rejects_blank_template_set() -> None:
    value = {
        **imported_materialization(),
        "operation": "rendered",
        "parent_content_sha256": "a" * 64,
        "template_set": "",
        "template_version": "1.0.0",
    }
    with pytest.raises(ValidationError):
        MaterializationProvenance.model_validate(value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository_id", "bad"),
        ("document_id", "DOC-1"),
        ("initial_repository_path", "/absolute.md"),
        ("original_content_sha256", "A" * 64),
        ("source_format", "json"),
        ("parser_profile", "Bad Profile"),
        ("parser_profile_version", "v1"),
    ],
)
def test_origin_provenance_negative_matrix(field: str, value: object) -> None:
    candidate: dict[str, object] = {
        "repository_id": "urn:raptor:repo:raptor",
        "document_id": "DOC-RAP-001",
        "initial_repository_path": "docs/requirements.md",
        "original_content_sha256": "a" * 64,
        "source_format": "markdown",
        "parser_profile": "raptor_dogfood",
        "parser_profile_version": "1.0.0",
    }
    candidate[field] = value
    with pytest.raises(ValidationError):
        OriginProvenance.model_validate(candidate)
