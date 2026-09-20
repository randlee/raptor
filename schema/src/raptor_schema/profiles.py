from __future__ import annotations

import hashlib
import importlib.util
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Protocol

from pydantic import JsonValue, TypeAdapter

from .models import (
    Artifact,
    Diagnostic,
    DocumentId,
    OriginProvenance,
    ProfileId,
    ProfileVersion,
    RepositoryId,
    SchemaVersion,
    Sha256,
    SourceDocument,
    SourceLocation,
)


class ProfileError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _inside(root: Path, path: Path) -> Path:
    root = root.resolve()
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ProfileError("RAPTOR.PATH.OUTSIDE_ROOT", f"{path} escapes {root}") from error
    return path


@dataclass(frozen=True)
class SourceInput:
    repo_root: Path
    repository_id: RepositoryId
    document_id: DocumentId
    repository_path: PurePosixPath
    content: bytes

    def __post_init__(self) -> None:
        root = self.repo_root.resolve()
        relative = self.repository_path
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ProfileError("RAPTOR.PATH.OUTSIDE_ROOT", "source path must be normalized and relative")
        _inside(root, root / Path(*relative.parts))
        object.__setattr__(self, "repo_root", root)


@dataclass(frozen=True)
class ParsedSection:
    kind: str
    heading: str | None
    body: str
    location: SourceLocation
    attributes: Mapping[str, JsonValue]


@dataclass(frozen=True)
class ParsedDocument:
    source: SourceInput
    frontmatter: Mapping[str, JsonValue]
    sections: tuple[ParsedSection, ...]


@dataclass(frozen=True)
class ComparableDocument:
    schema_version: SchemaVersion
    origin: OriginProvenance
    artifacts: tuple[Artifact, ...]


@dataclass(frozen=True)
class ProfileDescriptor:
    profile_id: ProfileId
    profile_version: ProfileVersion
    api_version: Literal["1"]
    entrypoint: str
    module_sha256: Sha256


@dataclass(frozen=True)
class ResolvedProfile:
    descriptor: ProfileDescriptor
    descriptor_path: Path
    module_path: Path
    source: Literal["explicit", "repository", "builtin"]


class SourceProfile(Protocol):
    profile_id: str
    profile_version: str

    def parse(self, source: SourceInput) -> ParsedDocument: ...
    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]: ...
    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument: ...
    def project_render_input(self, document: SourceDocument) -> dict[str, object]: ...
    def normalize(self, document: SourceDocument) -> ComparableDocument: ...


def _read_descriptor(path: Path, *, root: Path, source: str) -> ResolvedProfile:
    descriptor_path = _inside(root, path)
    try:
        raw = tomllib.loads(descriptor_path.read_text(encoding="utf-8"))
        expected = {"profile_id", "profile_version", "api_version", "entrypoint", "module_sha256"}
        if set(raw) != expected:
            raise ValueError("descriptor fields do not match the contract")
        if raw["api_version"] != "1":
            raise ProfileError("RAPTOR.PROFILE.API", "unsupported profile API")
        descriptor = ProfileDescriptor(
            profile_id=TypeAdapter(ProfileId).validate_python(raw["profile_id"]),
            profile_version=TypeAdapter(ProfileVersion).validate_python(raw["profile_version"]),
            api_version="1",
            entrypoint=TypeAdapter(str).validate_python(raw["entrypoint"]),
            module_sha256=TypeAdapter(Sha256).validate_python(raw["module_sha256"]),
        )
    except ProfileError:
        raise
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.RETURN_TYPE", "invalid profile descriptor") from error
    if ":" not in descriptor.entrypoint:
        raise ProfileError("RAPTOR.PROFILE.ENTRYPOINT", "entrypoint must be module.py:object")
    module_name, symbol = descriptor.entrypoint.split(":", 1)
    if not module_name or not symbol or Path(module_name).is_absolute():
        raise ProfileError("RAPTOR.PROFILE.ENTRYPOINT", "invalid entrypoint")
    module_path = _inside(descriptor_path.parent, descriptor_path.parent / module_name)
    if hashlib.sha256(module_path.read_bytes()).hexdigest() != descriptor.module_sha256:
        raise ProfileError("RAPTOR.PROFILE.HASH", "profile module hash mismatch")
    return ResolvedProfile(descriptor, descriptor_path, module_path, source)  # type: ignore[arg-type]


def _version_tuple(value: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def resolve_profile_descriptor(
    profile_id: str,
    requested_version: str,
    *,
    repo_root: Path,
    explicit_descriptor: Path | None = None,
    builtin_descriptors: tuple[Path, ...] = (),
    allow_profile_code: bool = False,
) -> ResolvedProfile:
    root = repo_root.resolve()
    source: Literal["explicit", "repository", "builtin"]
    candidates: list[tuple[Path, Path, Literal["explicit", "repository", "builtin"]]]
    if explicit_descriptor is not None:
        source = "explicit"
        candidates = [(explicit_descriptor, explicit_descriptor.parent.resolve(), source)]
    else:
        local_root = root / ".raptor" / "profiles" / profile_id
        local = sorted(local_root.glob("**/profile.toml")) if local_root.exists() else []
        if local:
            source = "repository"
            candidates = [(path, root, source) for path in local]
        else:
            source = "builtin"
            candidates = [(path, path.parent.resolve(), source) for path in builtin_descriptors]
    if not candidates:
        raise ProfileError("RAPTOR.PROFILE.VERSION", "no matching profile is installed")
    if source != "builtin" and not allow_profile_code:
        raise ProfileError("RAPTOR.PROFILE.UNTRUSTED", "external profile code requires explicit trust")
    resolved = [_read_descriptor(path, root=boundary, source=kind) for path, boundary, kind in candidates]
    resolved = [item for item in resolved if item.descriptor.profile_id == profile_id]
    if not resolved:
        raise ProfileError("RAPTOR.PROFILE.VERSION", "profile id mismatch")
    if requested_version.endswith(".x"):
        try:
            major = int(requested_version[:-2])
        except ValueError as error:
            raise ProfileError("RAPTOR.PROFILE.VERSION", "invalid version constraint") from error
        matches = [item for item in resolved if _version_tuple(item.descriptor.profile_version)[0] == major]
        if not matches:
            raise ProfileError("RAPTOR.PROFILE.VERSION", "no compatible profile version")
        highest = max(_version_tuple(item.descriptor.profile_version) for item in matches)
        matches = [item for item in matches if _version_tuple(item.descriptor.profile_version) == highest]
    else:
        matches = [item for item in resolved if item.descriptor.profile_version == requested_version]
    if not matches:
        raise ProfileError("RAPTOR.PROFILE.VERSION", "requested profile version is unavailable")
    if len(matches) != 1:
        raise ProfileError("RAPTOR.PROFILE.AMBIGUOUS", "duplicate profile versions at one precedence")
    selected = matches[0]
    if selected.descriptor.api_version != "1":
        raise ProfileError("RAPTOR.PROFILE.API", "unsupported profile API")
    return selected


def load_profile(resolved: ResolvedProfile) -> SourceProfile:
    _, symbol = resolved.descriptor.entrypoint.split(":", 1)
    spec = importlib.util.spec_from_file_location(f"raptor_profile_{resolved.descriptor.module_sha256}", resolved.module_path)
    if spec is None or spec.loader is None:
        raise ProfileError("RAPTOR.PROFILE.ENTRYPOINT", "profile module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.PARSE", "profile import failed") from error
    if not hasattr(module, symbol):
        raise ProfileError("RAPTOR.PROFILE.ENTRYPOINT", "entrypoint symbol is missing")
    try:
        profile = getattr(module, symbol)
        profile = profile() if isinstance(profile, type) else profile
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.PARSE", "profile initialization failed") from error
    if not all(callable(getattr(profile, name, None)) for name in ("parse", "validate", "canonicalize", "project_render_input", "normalize")):
        raise ProfileError("RAPTOR.PROFILE.RETURN_TYPE", "entrypoint does not implement SourceProfile")
    if getattr(profile, "profile_id", None) != resolved.descriptor.profile_id or getattr(profile, "profile_version", None) != resolved.descriptor.profile_version:
        raise ProfileError("RAPTOR.PROFILE.ENTRYPOINT", "entrypoint identity does not match descriptor")
    return profile


def parse_with_profile(profile: SourceProfile, source: SourceInput) -> ParsedDocument:
    try:
        result = profile.parse(source)
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.PARSE", "profile parse failed") from error
    if not isinstance(result, ParsedDocument):
        raise ProfileError("RAPTOR.PROFILE.RETURN_TYPE", "parse returned an invalid type")
    return result


def validate_with_profile(profile: SourceProfile, parsed: ParsedDocument) -> list[Diagnostic]:
    try:
        result = profile.validate(parsed)
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.VALIDATION", "profile validation failed") from error
    if not isinstance(result, list) or any(not isinstance(item, Diagnostic) for item in result):
        raise ProfileError("RAPTOR.PROFILE.RETURN_TYPE", "validate returned an invalid type")
    return result


def canonicalize_with_profile(profile: SourceProfile, parsed: ParsedDocument) -> SourceDocument:
    try:
        result = profile.canonicalize(parsed)
    except Exception as error:
        raise ProfileError("RAPTOR.PROFILE.CANONICALIZE", "profile canonicalization failed") from error
    if not isinstance(result, SourceDocument):
        raise ProfileError("RAPTOR.PROFILE.RETURN_TYPE", "canonicalize returned an invalid type")
    return result
