from __future__ import annotations

import re
from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints, WithJsonSchema, model_validator

from .base import ContractModel, RepositoryPath, SchemaVersion


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
            "pattern": r"^(?![!/])(?!.*\\)(?!.*(?:^|/)(?:\.|\.\.)(?:/|$))(?!.*\*\*\*)(?!.*[\[\]{}])[^/]+(?:/[^/]+)*$",
        }
    ),
    AfterValidator(_glob_pattern),
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
    name: Annotated[
        str,
        StringConstraints(pattern=r"^[a-z][a-z0-9_-]{0,63}$"),
    ]
    root: RepositoryPath
    include: list[GlobPattern] = Field(min_length=1)
    exclude: list[GlobPattern] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_patterns(self) -> "ScanSource":
        if self.root.split("/", 1)[0] in {".git", ".raptor"}:
            raise ValueError("Raptor control directories may not be scan roots")
        for label, patterns in (("include", self.include), ("exclude", self.exclude)):
            if len(patterns) != len(set(patterns)):
                raise ValueError(f"{label} patterns must be unique")
        return self

    def matches(self, repository_path: RepositoryPath | str) -> bool:
        path = str(repository_path)
        prefix = f"{self.root}/"
        if not path.startswith(prefix):
            return False
        relative = path[len(prefix) :]
        included = any(_compile_glob(pattern).fullmatch(relative) for pattern in self.include)
        excluded = any(_compile_glob(pattern).fullmatch(relative) for pattern in self.exclude)
        return included and not excluded


class RepositoryScanConfig(ContractModel):
    schema_version: SchemaVersion
    sources: list[ScanSource] = Field(min_length=1)

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


__all__ = ["GlobPattern", "RepositoryScanConfig", "ScanSource"]
