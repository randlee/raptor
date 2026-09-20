from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from raptor_schema import SourceDocument

PathPart = str | int


def set_path(value: object, path: tuple[PathPart, ...], replacement: object) -> None:
    current = value
    for part in path[:-1]:
        current = current[part]  # type: ignore[index]
    current[path[-1]] = replacement  # type: ignore[index]


FAMILY_NEGATIVE_CASES: tuple[tuple[str, tuple[PathPart, ...], object, str | None], ...] = (
    # Requirement
    ("requirement-statement", ("artifacts", 0, "statement"), "   ", "must not be blank"),
    ("requirement-acceptance", ("artifacts", 0, "acceptance_criteria"), [], None),
    ("requirement-rationale", ("artifacts", 0, "rationale"), "", "must not be blank"),
    ("requirement-priority", ("artifacts", 0, "priority"), "urgent", None),
    # Non-functional requirement
    ("nfr-statement", ("artifacts", 1, "statement"), "", "must not be blank"),
    ("nfr-quality", ("artifacts", 1, "quality_attribute"), "Bad Attribute", None),
    ("nfr-measurement", ("artifacts", 1, "measurement", "target"), "zero", "numeric"),
    ("nfr-acceptance", ("artifacts", 1, "acceptance_criteria"), [], None),
    ("nfr-rationale", ("artifacts", 1, "rationale"), "", "must not be blank"),
    ("nfr-priority", ("artifacts", 1, "priority"), "urgent", None),
    # Architecture decision
    ("adr-context", ("artifacts", 2, "context"), "", "must not be blank"),
    ("adr-decision", ("artifacts", 2, "decision"), "", "must not be blank"),
    ("adr-consequences", ("artifacts", 2, "consequences"), [], None),
    ("adr-alternative", ("artifacts", 2, "alternatives", 0), "", "must not be blank"),
    # Design document and nested payloads
    ("design-overview", ("artifacts", 3, "overview"), "", "must not be blank"),
    ("design-components", ("artifacts", 3, "components"), [], None),
    ("component-name", ("artifacts", 3, "components", 0, "name"), "", "must not be blank"),
    ("component-responsibility", ("artifacts", 3, "components", 0, "responsibility"), "", "must not be blank"),
    ("interface-name", ("artifacts", 3, "interfaces", 0, "name"), "", "must not be blank"),
    ("interface-description", ("artifacts", 3, "interfaces", 0, "description"), "", "must not be blank"),
    ("interface-participants", ("artifacts", 3, "interfaces", 0, "participants"), ["Raptor"], None),
    # Test plan and nested payloads
    ("test-objective", ("artifacts", 4, "objective"), "", "must not be blank"),
    ("test-scope", ("artifacts", 4, "scope"), "", "must not be blank"),
    ("test-cases", ("artifacts", 4, "test_cases"), [], None),
    ("case-id", ("artifacts", 4, "test_cases", 0, "id"), "CASE-1", None),
    ("case-title", ("artifacts", 4, "test_cases", 0, "title"), "", "must not be blank"),
    ("case-steps", ("artifacts", 4, "test_cases", 0, "steps"), [], None),
    ("case-expected", ("artifacts", 4, "test_cases", 0, "expected_result"), "", "must not be blank"),
    ("case-verifies", ("artifacts", 4, "test_cases", 0, "verifies"), [], None),
    ("entry-criterion", ("artifacts", 4, "entry_criteria"), [""], "must not be blank"),
    ("exit-criterion", ("artifacts", 4, "exit_criteria"), [""], "must not be blank"),
)


@pytest.mark.parametrize(
    ("name", "path", "replacement", "message"),
    FAMILY_NEGATIVE_CASES,
    ids=[case[0] for case in FAMILY_NEGATIVE_CASES],
)
def test_family_negative_constraint_matrix(
    document_dict: dict[str, object],
    name: str,
    path: tuple[PathPart, ...],
    replacement: object,
    message: str | None,
) -> None:
    candidate = deepcopy(document_dict)
    set_path(candidate, path, replacement)
    with pytest.raises(ValidationError, match=message):
        SourceDocument.model_validate(candidate)


@pytest.mark.parametrize(
    ("path", "message"),
    [
        (
            ("artifacts", 3, "components", 0, "dependencies"),
            "duplicate component dependency",
        ),
        (
            ("artifacts", 4, "test_cases", 0, "verifies"),
            "duplicate verification key",
        ),
    ],
)
def test_set_like_artifact_keys_reject_duplicates_deterministically(
    document_dict: dict[str, object], path: tuple[PathPart, ...], message: str
) -> None:
    candidate = deepcopy(document_dict)
    current = candidate
    for part in path:
        current = current[part]  # type: ignore[index,assignment]
    duplicated = [deepcopy(current[0]), deepcopy(current[0])]  # type: ignore[index]
    set_path(candidate, path, duplicated)
    with pytest.raises(ValidationError, match=message):
        SourceDocument.model_validate(candidate)
