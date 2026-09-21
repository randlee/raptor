from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import RepositoryScanConfig


def config(*sources: dict[str, object]) -> RepositoryScanConfig:
    return RepositoryScanConfig.model_validate(
        {"schema_version": "1.0.0", "sources": list(sources)}
    )


def source(
    name: str = "product-requirements",
    root: str = "specifications/requirements",
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "root": root,
        "include": ["**/*.md"] if include is None else include,
        "exclude": [] if exclude is None else exclude,
    }


def test_allowlist_matches_only_included_files_below_root() -> None:
    scan = config(
        source(
            include=["*.md", "**/*.md"],
            exclude=["README.md", "archive/**"],
        )
    )

    assert scan.matching_source("specifications/requirements/REQ-RAP-010.md")
    assert scan.matching_source("specifications/requirements/current/REQ-RAP-011.md")
    assert scan.matching_source("specifications/requirements/README.md") is None
    assert scan.matching_source("specifications/requirements/archive/REQ-RAP-001.md") is None
    assert scan.matching_source("unlisted/REQ-RAP-010.md") is None


@pytest.mark.parametrize(
    "root",
    ["/absolute", "../outside", "specifications/../outside", ".", "", "folder/"],
)
def test_source_root_must_be_a_normalized_repository_relative_folder(root: str) -> None:
    with pytest.raises(ValidationError):
        config(source(root=root))


@pytest.mark.parametrize(
    "pattern",
    ["", "/**/*.md", "../*.md", "folder/../*.md", "folder\\*.md", "!draft/**", "*.{md,txt}", "***/*.md"],
)
def test_glob_rejects_ambiguous_or_escaping_syntax(pattern: str) -> None:
    with pytest.raises(ValidationError):
        config(source(include=[pattern]))


def test_source_names_roots_and_patterns_are_unique() -> None:
    invalid_cases = (
        (source(), source(root="architecture/decisions")),
        (source(), source(name="architecture-decisions")),
        (source(include=["**/*.md", "**/*.md"]),),
        (source(exclude=["archive/**", "archive/**"]),),
    )
    for sources in invalid_cases:
        with pytest.raises(ValidationError):
            config(*sources)


def test_source_roots_may_not_overlap() -> None:
    with pytest.raises(ValidationError, match="may not overlap"):
        config(
            source(root="specifications"),
            source(name="requirements", root="specifications/requirements"),
        )


def test_unknown_fields_and_empty_sources_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RepositoryScanConfig.model_validate(
            {"schema_version": "1.0.0", "sources": [], "unexpected": True}
        )

    with pytest.raises(ValidationError):
        config(source(include=[]))


@pytest.mark.parametrize("root", [".git/objects", ".raptor/state"])
def test_control_directories_cannot_be_scan_roots(root: str) -> None:
    with pytest.raises(ValidationError, match="control directories"):
        config(source(root=root))


def test_double_star_matches_zero_or_more_directories() -> None:
    scan = config(source(include=["**/*.md"]))

    assert scan.matching_source("specifications/requirements/REQ-RAP-010.md")
    assert scan.matching_source("specifications/requirements/a/b/REQ-RAP-010.md")
    assert scan.matching_source("specifications/requirements/REQ-RAP-010.txt") is None
