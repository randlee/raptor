from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal, Protocol, TypeAlias, cast

from pydantic import JsonValue, TypeAdapter

from .models import (
    Artifact,
    Diagnostic,
    DocumentId,
    JsonObject,
    OriginProvenance,
    ProfileId,
    ProfileVersion,
    RepositoryId,
    SchemaVersion,
    Sha256,
    SourceDocument,
    SourceLocation,
)
from .models.base import reject_non_finite

_REPOSITORY_ID_ADAPTER = TypeAdapter(RepositoryId)
_DOCUMENT_ID_ADAPTER = TypeAdapter(DocumentId)
_JSON_OBJECT_ADAPTER = TypeAdapter(JsonObject)

FrozenJsonValue: TypeAlias = (
    None | bool | int | float | str | tuple["FrozenJsonValue", ...] | Mapping[str, "FrozenJsonValue"]
)
FrozenJsonObject: TypeAlias = Mapping[str, FrozenJsonValue]


def _resolved_inside(root: Path, relative: PurePosixPath) -> Path:
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: source path escapes repository root") from error
    return candidate


def _require_json_shape(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, list):
        for item in value:
            _require_json_shape(item)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            _require_json_shape(item)
        return
    raise ValueError("render projection must contain only JSON-compatible values")


def _freeze_json(value: JsonValue) -> FrozenJsonValue:
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    return value


def _snapshot_mapping(value: Mapping[str, JsonValue]) -> FrozenJsonObject:
    validated = validate_json_object(dict(value))
    return cast(FrozenJsonObject, _freeze_json(validated))


@dataclass(frozen=True)
class SourceInput:
    repo_root: Path
    repository_id: RepositoryId
    document_id: DocumentId
    repository_path: PurePosixPath
    content: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.repo_root, Path):
            raise TypeError("repo_root must be pathlib.Path")
        root = self.repo_root.resolve()
        if not root.is_dir():
            raise ValueError("repo_root must resolve to an existing directory")
        repository_id = _REPOSITORY_ID_ADAPTER.validate_python(self.repository_id)
        document_id = _DOCUMENT_ID_ADAPTER.validate_python(self.document_id)
        if not isinstance(self.repository_path, PurePosixPath):
            raise TypeError("repository_path must be pathlib.PurePosixPath")
        relative = self.repository_path
        if (
            str(relative) == "."
            or not relative.parts
            or relative.is_absolute()
            or any(part in {"", ".", ".."} for part in relative.parts)
        ):
            raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: source path must be normalized and relative")
        _resolved_inside(root, relative)
        if not isinstance(self.content, bytes):
            raise TypeError("content must be bytes")
        object.__setattr__(self, "repo_root", root)
        object.__setattr__(self, "repository_id", repository_id)
        object.__setattr__(self, "document_id", document_id)


@dataclass(frozen=True)
class ParsedSection:
    kind: str
    heading: str | None
    body: str
    location: SourceLocation
    attributes: FrozenJsonObject

    def __post_init__(self) -> None:
        source = cast(Mapping[str, JsonValue], self.attributes)
        object.__setattr__(self, "attributes", _snapshot_mapping(source))


@dataclass(frozen=True)
class ParsedDocument:
    source: SourceInput
    frontmatter: FrozenJsonObject
    sections: tuple[ParsedSection, ...]

    def __post_init__(self) -> None:
        source = cast(Mapping[str, JsonValue], self.frontmatter)
        object.__setattr__(self, "frontmatter", _snapshot_mapping(source))
        object.__setattr__(self, "sections", tuple(self.sections))


@dataclass(frozen=True)
class ArtifactSnapshot:
    data: FrozenJsonObject

    def __post_init__(self) -> None:
        source = cast(Mapping[str, JsonValue], self.data)
        object.__setattr__(self, "data", _snapshot_mapping(source))

    @classmethod
    def from_artifact(cls, artifact: Artifact) -> "ArtifactSnapshot":
        value = cast(JsonObject, artifact.model_dump(mode="json", exclude_none=True))
        return cls(data=cast(FrozenJsonObject, value))


@dataclass(frozen=True)
class ComparableDocument:
    schema_version: SchemaVersion
    origin: OriginProvenance
    artifacts: tuple[ArtifactSnapshot, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))


@dataclass(frozen=True)
class ProfileDescriptor:
    profile_id: ProfileId
    profile_version: ProfileVersion
    api_version: Literal["1"]
    entrypoint: str
    module_sha256: Sha256


class SourceProfile(Protocol):
    profile_id: str
    profile_version: str

    def parse(self, source: SourceInput) -> ParsedDocument: ...
    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]: ...
    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument: ...
    def project_render_input(self, document: SourceDocument) -> JsonObject: ...
    def normalize(self, document: SourceDocument) -> ComparableDocument: ...


def validate_json_object(value: object) -> JsonObject:
    """Validate the recursive JSON-object boundary used by render projections."""
    _require_json_shape(value)
    validated = _JSON_OBJECT_ADAPTER.validate_python(value)
    return cast(JsonObject, reject_non_finite(validated))


__all__ = [
    "ComparableDocument",
    "ArtifactSnapshot",
    "FrozenJsonObject",
    "FrozenJsonValue",
    "ParsedDocument",
    "ParsedSection",
    "ProfileDescriptor",
    "SourceInput",
    "SourceProfile",
    "validate_json_object",
]
