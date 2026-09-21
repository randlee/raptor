from __future__ import annotations

import re
from typing import Annotated

from pydantic import (
    AfterValidator,
    Field,
    StringConstraints,
    TypeAdapter,
    WithJsonSchema,
    model_validator,
)

from .base import (
    ContractModel,
    ProfileId,
    ProfileVersion,
    RepositoryPath,
    RepositoryId,
    SchemaVersion,
)
from .common import ArtifactType
from .identity import IdentityManifest


def _glob_pattern(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("glob must be non-empty and may not have surrounding whitespace")
    if value.startswith(("/", "!")) or "\\" in value:
        raise ValueError("glob must be a relative POSIX pattern without negation")
    if any(character in value for character in "[]{}"):
        raise ValueError("glob supports only literals, '*', '?', and '**'")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("glob may not contain empty, '.' or '..' segments")
    if "***" in value:
        raise ValueError("glob may not contain runs longer than '**'")
    return value


GlobPattern = Annotated[
    str,
    StringConstraints(min_length=1),
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "pattern": r"^(?!\s)(?!.*\s$)(?![!/])(?!.*\\)(?!.*(?:^|/)(?:\.|\.\.)(?:/|$))(?!.*\*\*\*)(?!.*[\[\]{}])[^/]+(?:/[^/]+)*$",
        }
    ),
    AfterValidator(_glob_pattern),
]

_REPOSITORY_PATH_ADAPTER = TypeAdapter(RepositoryPath)


def _scan_root(value: str) -> str:
    root = _REPOSITORY_PATH_ADAPTER.validate_python(value)
    if root.split("/", 1)[0] in {".git", ".raptor"}:
        raise ValueError("Raptor control directories may not be scan roots")
    return root


ScanRoot = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "pattern": r"^(?!/)(?!\.{1,2}(?:/|$))(?!.*(?:/\.{1,2})(?:/|$))(?!.*//)(?!.*/$)(?!.*\\)(?!(?:\.git|\.raptor)(?:/|$)).+$",
        }
    ),
    AfterValidator(_scan_root),
]

SourceName = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}\z"),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": r"^[a-z][a-z0-9_-]{0,63}(?![\s\S])",
        }
    ),
]


def _config_artifact_path(value: str) -> str:
    path = _REPOSITORY_PATH_ADAPTER.validate_python(value)
    if any(ord(character) < 32 or ord(character) == 127 for character in path):
        raise ValueError("configuration artifact path may not contain control characters")
    if path.split("/", 1)[0] in {".git", ".raptor"}:
        raise ValueError("configuration artifact path is relative to .raptor")
    return path


_CONFIG_PATH_PREFIX = (
    r"^(?!/)(?!\.{1,2}(?:/|$))(?!.*(?:/\.{1,2})(?:/|$))"
    r"(?!.*//)(?!.*\\)(?!.*[\x00-\x1f\x7f])"
    r"(?!(?:\.git|\.raptor)(?:/|$))"
)


def _typed_config_path_schema(extension: str) -> dict[str, object]:
    return {
        "type": "string",
        "minLength": len(extension) + 2,
        "pattern": (
            rf"{_CONFIG_PATH_PREFIX}(?:[^/]+/)*[^/]+\.{extension}(?![\s\S])"
        ),
    }


def _toml_config_path(value: str) -> str:
    if not value.endswith(".toml") or value.rsplit("/", 1)[-1] == ".toml":
        raise ValueError("configuration path must end in .toml")
    return value


def _json_config_path(value: str) -> str:
    if not value.endswith(".json") or value.rsplit("/", 1)[-1] == ".json":
        raise ValueError("configuration path must end in .json")
    return value


_TomlConfigPath = Annotated[
    str,
    WithJsonSchema(_typed_config_path_schema("toml")),
    AfterValidator(_config_artifact_path),
    AfterValidator(_toml_config_path),
]

_JsonConfigPath = Annotated[
    str,
    WithJsonSchema(_typed_config_path_schema("json")),
    AfterValidator(_config_artifact_path),
    AfterValidator(_json_config_path),
]


def _compile_glob(pattern: str) -> re.Pattern[str]:
    expression: list[str] = ["^"]
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    expression.append("(?:[^/]+/)*")
                    index += 1
                else:
                    expression.append(".*")
                continue
            expression.append("[^/]*")
        elif character == "?":
            expression.append("[^/]")
        else:
            expression.append(re.escape(character))
        index += 1
    expression.append("$")
    return re.compile("".join(expression))


class ScanSource(ContractModel):
    name: SourceName
    root: ScanRoot
    include: tuple[GlobPattern, ...] = Field(
        min_length=1, json_schema_extra={"uniqueItems": True}
    )
    exclude: tuple[GlobPattern, ...] = Field(
        default_factory=tuple, json_schema_extra={"uniqueItems": True}
    )

    @model_validator(mode="after")
    def unique_patterns(self) -> "ScanSource":
        for label, patterns in (("include", self.include), ("exclude", self.exclude)):
            if len(patterns) != len(set(patterns)):
                raise ValueError(f"{label} patterns must be unique")
        return self

    def matches(self, repository_path: RepositoryPath | str) -> bool:
        try:
            path = _REPOSITORY_PATH_ADAPTER.validate_python(repository_path)
        except ValueError:
            return False
        if {".git", ".raptor"}.intersection(path.split("/")):
            return False
        prefix = f"{self.root}/"
        if not path.startswith(prefix):
            return False
        relative = path[len(prefix) :]
        included = any(_compile_glob(pattern).fullmatch(relative) for pattern in self.include)
        excluded = any(_compile_glob(pattern).fullmatch(relative) for pattern in self.exclude)
        return included and not excluded


class RepositoryScanConfig(ContractModel):
    schema_version: SchemaVersion
    sources: tuple[ScanSource, ...] = Field(
        min_length=1, json_schema_extra={"uniqueItems": True}
    )

    @model_validator(mode="after")
    def unique_non_overlapping_sources(self) -> "RepositoryScanConfig":
        names = [source.name for source in self.sources]
        if len(names) != len(set(names)):
            raise ValueError("source names must be unique")

        roots = [source.root for source in self.sources]
        if len(roots) != len(set(roots)):
            raise ValueError("source roots must be unique")
        for index, left in enumerate(roots):
            for right in roots[index + 1 :]:
                if left.startswith(f"{right}/") or right.startswith(f"{left}/"):
                    raise ValueError(f"source roots may not overlap: {left!r} and {right!r}")
        return self

    def matching_source(self, repository_path: RepositoryPath | str) -> ScanSource | None:
        matches = [source for source in self.sources if source.matches(repository_path)]
        if len(matches) > 1:
            raise AssertionError("validated source roots cannot match the same path")
        return matches[0] if matches else None


class ProfileSelection(ContractModel):
    profile_id: ProfileId
    profile_version: ProfileVersion


class SourceRoute(ContractModel):
    source: SourceName
    profile: ProfileSelection
    artifact_types: tuple[ArtifactType, ...] = Field(
        min_length=1, json_schema_extra={"uniqueItems": True}
    )

    @model_validator(mode="after")
    def unique_artifact_types(self) -> "SourceRoute":
        if len(self.artifact_types) != len(set(self.artifact_types)):
            raise ValueError("artifact types must be unique")
        return self


class RepositoryRoutingConfig(ContractModel):
    schema_version: SchemaVersion
    routes: tuple[SourceRoute, ...] = Field(
        min_length=1, json_schema_extra={"uniqueItems": True}
    )

    @model_validator(mode="after")
    def unique_sources(self) -> "RepositoryRoutingConfig":
        sources = [route.source for route in self.routes]
        if len(sources) != len(set(sources)):
            raise ValueError("each source must have exactly one route")
        return self


def validate_source_routing(
    scan: RepositoryScanConfig, routing: RepositoryRoutingConfig
) -> tuple[SourceRoute, ...]:
    scan = RepositoryScanConfig.model_validate(scan.model_dump(mode="python"))
    routing = RepositoryRoutingConfig.model_validate(routing.model_dump(mode="python"))
    scan_sources = {source.name for source in scan.sources}
    routed_sources = {route.source for route in routing.routes}
    missing = sorted(scan_sources - routed_sources)
    unknown = sorted(routed_sources - scan_sources)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing routes: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown sources: {', '.join(unknown)}")
        raise ValueError("RAPTOR.CONFIG.ROUTING: " + "; ".join(details))
    routes = {route.source: route for route in routing.routes}
    return tuple(routes[source.name] for source in scan.sources)


class RepositoryConfigFiles(ContractModel):
    scan: _TomlConfigPath
    routing: _TomlConfigPath
    identity: _JsonConfigPath

    @model_validator(mode="after")
    def distinct_typed_paths(self) -> "RepositoryConfigFiles":
        paths = (self.scan, self.routing, self.identity)
        if len(set(paths)) != len(paths):
            raise ValueError("configuration artifact paths must be unique")
        return self


class RepositoryConfigManifest(ContractModel):
    schema_version: SchemaVersion
    repository_id: RepositoryId
    files: RepositoryConfigFiles


def validate_repository_manifest_identity(
    manifest: RepositoryConfigManifest, identity: IdentityManifest
) -> None:
    manifest = RepositoryConfigManifest.model_validate(manifest.model_dump(mode="python"))
    identity = IdentityManifest.model_validate(identity.model_dump(mode="python"))
    if manifest.repository_id != identity.repository_id:
        raise ValueError(
            "RAPTOR.CONFIG.REPOSITORY_ID: repository manifest and identity manifest differ"
        )


__all__ = [
    "GlobPattern",
    "ProfileSelection",
    "RepositoryConfigFiles",
    "RepositoryConfigManifest",
    "RepositoryRoutingConfig",
    "RepositoryScanConfig",
    "ScanRoot",
    "ScanSource",
    "SourceName",
    "SourceRoute",
    "validate_source_routing",
    "validate_repository_manifest_identity",
]
