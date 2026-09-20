from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError

from raptor_schema import (
    ComparableDocument,
    Diagnostic,
    JsonObject,
    ParsedDocument,
    ProfileDescriptor,
    SourceDocument,
    SourceInput,
    SourceProfile,
    validate_json_object,
)


def source_input(root: Path, **overrides: object) -> SourceInput:
    values: dict[str, object] = {
        "repo_root": root,
        "repository_id": "urn:raptor:repo:raptor",
        "document_id": "DOC-RAP-001",
        "repository_path": PurePosixPath("docs/source.md"),
        "content": b"source",
    }
    values.update(overrides)
    return SourceInput(**values)  # type: ignore[arg-type]


def test_source_input_validates_and_resolves_root(tmp_path: Path) -> None:
    value = source_input(tmp_path)
    assert value.repo_root == tmp_path.resolve()
    assert value.repository_path == PurePosixPath("docs/source.md")


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("repo_root", "not-a-path", TypeError),
        ("repository_id", "invalid", ValidationError),
        ("document_id", "invalid", ValidationError),
        ("repository_path", "docs/source.md", TypeError),
        ("repository_path", PurePosixPath("/absolute.md"), ValueError),
        ("repository_path", PurePosixPath("../escape.md"), ValueError),
        ("content", "source", TypeError),
        ("content", bytearray(b"source"), TypeError),
    ],
)
def test_source_input_rejects_invalid_boundaries(
    tmp_path: Path, field: str, value: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        source_input(tmp_path, **{field: value})


def test_source_input_rejects_missing_root_and_symlink_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="existing directory"):
        source_input(tmp_path / "missing")
    outside = tmp_path / "outside.md"
    outside.write_bytes(b"outside")
    root = tmp_path / "repo"
    root.mkdir()
    (root / "link.md").symlink_to(outside)
    with pytest.raises(ValueError, match="OUTSIDE_ROOT"):
        source_input(root, repository_path=PurePosixPath("link.md"))


def test_profile_descriptor_is_data_only() -> None:
    descriptor = ProfileDescriptor(
        profile_id="raptor_dogfood",
        profile_version="1.0.0",
        api_version="1",
        entrypoint="profile.py:Profile",
        module_sha256="a" * 64,
    )
    assert descriptor.api_version == "1"


def test_render_projection_json_boundary_accepts_recursive_json() -> None:
    value = {"artifact": {"ids": ["REQ-RAP-001", None], "accepted": True, "count": 1}}
    assert validate_json_object(value) == value


@pytest.mark.parametrize(
    "value",
    [
        ["not", "an", "object"],
        {"bad": {1, 2}},
        {"bad": object()},
        {"bad": (1, 2)},
        {"bad": b"bytes"},
        {"bad": float("nan")},
        {"bad": float("inf")},
    ],
)
def test_render_projection_json_boundary_rejects_non_json(value: object) -> None:
    with pytest.raises((ValidationError, ValueError)):
        validate_json_object(value)


class ContractProfile:
    profile_id = "contract"
    profile_version = "1.0.0"

    def parse(self, source: SourceInput) -> ParsedDocument:
        return ParsedDocument(source=source, frontmatter={}, sections=())

    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]:
        return []

    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument:
        raise NotImplementedError

    def project_render_input(self, document: SourceDocument) -> JsonObject:
        return {"schema_version": document.schema_version}

    def normalize(self, document: SourceDocument) -> ComparableDocument:
        return ComparableDocument(
            schema_version=document.schema_version,
            origin=document.provenance.origin,
            artifacts=tuple(document.artifacts),
        )


def test_source_profile_contract_uses_json_object(document: SourceDocument) -> None:
    # Static conformance is also checked by mypy; runtime validation proves the JSON boundary.
    profile: SourceProfile = ContractProfile()
    assert validate_json_object(profile.project_render_input(document)) == {
        "schema_version": "1.0.0"
    }
