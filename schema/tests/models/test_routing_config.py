from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import (
    ArtifactType,
    RepositoryRoutingConfig,
    RepositoryScanConfig,
    validate_source_routing,
)


def scan_config(*names: str) -> RepositoryScanConfig:
    return RepositoryScanConfig.model_validate(
        {
            "schema_version": "1.0.0",
            "sources": [
                {
                    "name": name,
                    "root": f"specifications/{name}",
                    "include": ["**/*.md"],
                }
                for name in names
            ],
        }
    )


def route(source: str, *artifact_types: str) -> dict[str, object]:
    return {
        "source": source,
        "profile": {"profile_id": "raptor", "profile_version": "1.0.0"},
        "artifact_types": list(artifact_types),
    }


def routing_config(*routes: dict[str, object]) -> RepositoryRoutingConfig:
    return RepositoryRoutingConfig.model_validate(
        {"schema_version": "1.0.0", "routes": list(routes)}
    )


def test_routing_covers_every_scan_source_in_scan_order() -> None:
    scan = scan_config("requirements", "decisions")
    routing = routing_config(
        route("decisions", "architecture_decision"),
        route("requirements", "requirement", "non_functional_requirement"),
    )

    resolved = validate_source_routing(scan, routing)

    assert [item.source for item in resolved] == ["requirements", "decisions"]
    assert resolved[0].artifact_types == [
        ArtifactType.REQUIREMENT,
        ArtifactType.NON_FUNCTIONAL_REQUIREMENT,
    ]


@pytest.mark.parametrize(
    ("routes", "message"),
    [
        ([route("requirements", "requirement")], "missing routes: decisions"),
        (
            [
                route("requirements", "requirement"),
                route("decisions", "architecture_decision"),
                route("unlisted", "test_plan"),
            ],
            "unknown sources: unlisted",
        ),
    ],
)
def test_routing_rejects_missing_and_unknown_sources(
    routes: list[dict[str, object]], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_source_routing(scan_config("requirements", "decisions"), routing_config(*routes))


def test_routing_reports_missing_and_unknown_sources_deterministically() -> None:
    with pytest.raises(
        ValueError,
        match=r"missing routes: decisions; unknown sources: unlisted",
    ):
        validate_source_routing(
            scan_config("requirements", "decisions"),
            routing_config(
                route("requirements", "requirement"),
                route("unlisted", "test_plan"),
            ),
        )


def test_each_source_has_exactly_one_route() -> None:
    with pytest.raises(ValidationError, match="exactly one route"):
        routing_config(
            route("requirements", "requirement"),
            route("requirements", "non_functional_requirement"),
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": "1.0.0", "routes": []},
        {
            "schema_version": "1.0.0",
            "routes": [route("requirements")],
        },
        {
            "schema_version": "1.0.0",
            "routes": [route("requirements", "requirement", "requirement")],
        },
        {
            "schema_version": "1.0.0",
            "routes": [
                {
                    **route("requirements", "requirement"),
                    "profile": {"profile_id": "Bad Profile", "profile_version": "1.0.0"},
                }
            ],
        },
        {
            "schema_version": "1.0.0",
            "routes": [
                {
                    **route("requirements", "requirement"),
                    "profile": {"profile_id": "raptor", "profile_version": "latest"},
                }
            ],
        },
    ],
)
def test_routing_rejects_invalid_or_ambiguous_rules(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        RepositoryRoutingConfig.model_validate(payload)
