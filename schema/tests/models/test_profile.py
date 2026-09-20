from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath

import pytest
from pydantic import ValidationError

from raptor_schema import (
    ArtifactSnapshot,
    ComparableDocument,
    Diagnostic,
    JsonObject,
    ParsedDocument,
    ParsedSection,
    ProfileDescriptor,
    SourceDocument,
    SourceInput,
    SourceLocation,
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
        ("repository_path", PurePosixPath(r"docs\source.md"), ValueError),
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


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("profile_id", "Bad Profile", ValidationError),
        ("profile_version", "1", ValidationError),
        ("api_version", "2", ValueError),
        ("entrypoint", "   ", ValueError),
        ("entrypoint", 1, ValueError),
        ("module_sha256", "A" * 64, ValidationError),
    ],
)
def test_profile_descriptor_runtime_constraints(
    field: str, value: object, error: type[Exception]
) -> None:
    values: dict[str, object] = {
        "profile_id": "consumer",
        "profile_version": "1.0.0",
        "api_version": "1",
        "entrypoint": "profile.py:Profile",
        "module_sha256": "a" * 64,
    }
    values[field] = value
    with pytest.raises(error):
        ProfileDescriptor(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("schema_version", "2.0.0", ValidationError),
        ("origin", object(), TypeError),
        ("artifacts", [], TypeError),
        ("artifacts", (object(),), TypeError),
    ],
)
def test_comparable_document_runtime_constraints(
    document: SourceDocument, field: str, value: object, error: type[Exception]
) -> None:
    values: dict[str, object] = {
        "schema_version": document.schema_version,
        "origin": document.provenance.origin,
        "artifacts": tuple(ArtifactSnapshot.from_artifact(item) for item in document.artifacts),
    }
    values[field] = value
    with pytest.raises(error):
        ComparableDocument(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "path",
    [PurePosixPath("."), PurePosixPath(""), PurePosixPath("/absolute.md"), PurePosixPath("../escape.md")],
    ids=["current-directory", "empty", "absolute", "parent-escape"],
)
def test_source_input_path_failures_use_namespaced_code(
    tmp_path: Path, path: PurePosixPath
) -> None:
    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        source_input(tmp_path, repository_path=path)


def test_render_projection_json_boundary_accepts_recursive_json() -> None:
    value = {"artifact": {"ids": ["REQ-RAP-001", None], "accepted": True, "count": 1}}
    assert validate_json_object(value) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", 1),
        ("heading", 1),
        ("body", 1),
        ("location", object()),
        ("attributes", [("key", "value")]),
    ],
)
def test_parsed_section_runtime_boundaries(field: str, value: object) -> None:
    values: dict[str, object] = {
        "kind": "requirement",
        "heading": "Requirement",
        "body": "body",
        "location": SourceLocation(start_line=1, start_column=1),
        "attributes": {},
    }
    values[field] = value
    with pytest.raises(TypeError):
        ParsedSection(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", object()),
        ("frontmatter", [("key", "value")]),
        ("sections", []),
        ("sections", (object(),)),
    ],
)
def test_parsed_document_runtime_boundaries(
    tmp_path: Path, field: str, value: object
) -> None:
    values: dict[str, object] = {
        "source": source_input(tmp_path),
        "frontmatter": {},
        "sections": (),
    }
    values[field] = value
    with pytest.raises(TypeError):
        ParsedDocument(**values)  # type: ignore[arg-type]


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
            artifacts=tuple(ArtifactSnapshot.from_artifact(item) for item in document.artifacts),
        )


def test_source_profile_contract_uses_json_object(document: SourceDocument) -> None:
    # Static conformance is also checked by mypy; runtime validation proves the JSON boundary.
    profile: SourceProfile = ContractProfile()
    assert validate_json_object(profile.project_render_input(document)) == {
        "schema_version": "1.0.0"
    }


def test_boundary_types_are_deeply_immutable(
    tmp_path: Path, document: SourceDocument
) -> None:
    source = source_input(tmp_path)
    with pytest.raises(Exception):
        setattr(source, "content", b"changed")

    attributes: dict[str, object] = {"nested": {"items": [1, 2]}}
    location = SourceLocation(start_line=1, start_column=1)
    section = ParsedSection(
        kind="requirement",
        heading="Requirement",
        body="body",
        location=location,
        attributes=attributes,  # type: ignore[arg-type]
    )
    attributes["nested"] = "changed"
    assert section.location is location
    with pytest.raises(ValidationError, match="frozen"):
        setattr(location, "start_line", 2)
    assert section.location.start_line == 1
    assert section.attributes["nested"] != "changed"
    with pytest.raises(TypeError):
        section.attributes["new"] = True  # type: ignore[index]
    nested = section.attributes["nested"]
    assert isinstance(nested, Mapping)
    with pytest.raises(TypeError):
        nested["items"] = ()  # type: ignore[index]
    items = nested["items"]
    assert isinstance(items, tuple)
    with pytest.raises(AttributeError):
        items.append(3)  # type: ignore[union-attr]
    with pytest.raises(ValidationError, match="frozen"):
        setattr(section.location, "start_line", 2)

    frontmatter: dict[str, object] = {"tags": ["one"]}
    sections = [section]
    parsed = ParsedDocument(
        source=source,
        frontmatter=frontmatter,  # type: ignore[arg-type]
        sections=tuple(sections),
    )
    frontmatter["tags"] = ["changed"]
    sections.clear()
    assert parsed.frontmatter["tags"] == ("one",)
    assert parsed.sections == (section,)
    with pytest.raises(TypeError):
        parsed.frontmatter["new"] = None  # type: ignore[index]

    original = document.artifacts[0]
    snapshot = ArtifactSnapshot.from_artifact(original)
    original.acceptance_criteria.append("caller mutation")  # type: ignore[attr-defined]
    assert "caller mutation" not in snapshot.data["acceptance_criteria"]
    with pytest.raises(TypeError):
        snapshot.data["title"] = "changed"  # type: ignore[index]

    comparable = ComparableDocument(
        schema_version=document.schema_version,
        origin=document.provenance.origin,
        artifacts=(snapshot,),
    )
    with pytest.raises(Exception):
        setattr(comparable, "artifacts", ())
    with pytest.raises(TypeError):
        comparable.artifacts[0].data["title"] = "changed"  # type: ignore[index]

    descriptor = ProfileDescriptor(
        profile_id="consumer",
        profile_version="1.0.0",
        api_version="1",
        entrypoint="profile.py:Profile",
        module_sha256="a" * 64,
    )
    with pytest.raises(Exception):
        setattr(descriptor, "entrypoint", "changed")
