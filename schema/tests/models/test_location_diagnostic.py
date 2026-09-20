from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import Diagnostic, SourceLocation


@pytest.mark.parametrize(
    "value",
    [
        {"start_line": 1, "start_column": 1},
        {"start_line": 1, "start_column": 1, "end_line": 1, "end_column": 1},
        {"start_line": 1, "start_column": 9, "end_line": 2, "end_column": 1},
        {"start_line": 2, "start_column": 3, "end_line": 2, "end_column": 4},
    ],
)
def test_location_positive_matrix(value: dict[str, int]) -> None:
    assert SourceLocation.model_validate(value).start_line >= 1


@pytest.mark.parametrize(
    "value",
    [
        {"start_line": 0, "start_column": 1},
        {"start_line": 1, "start_column": 0},
        {"start_line": 2, "start_column": 3, "end_line": 1, "end_column": 9},
        {"start_line": 2, "start_column": 3, "end_line": 2, "end_column": 2},
        {"start_line": 1, "start_column": 1, "end_line": 2},
        {"start_line": 1, "start_column": 1, "end_column": 2},
        {"start_line": 1, "start_column": 1, "end_column": 2, "end_line": None},
    ],
)
def test_location_negative_matrix(value: dict[str, int | None]) -> None:
    with pytest.raises(ValidationError):
        SourceLocation.model_validate(value)


def diagnostic_value() -> dict[str, object]:
    return {
        "code": "RAPTOR.PROFILE.VALIDATION",
        "severity": "error",
        "message": "invalid source",
        "repository_id": "urn:raptor:repo:raptor",
        "document_id": "DOC-RAP-001",
        "repository_path": "docs/requirements.md",
    }


@pytest.mark.parametrize("severity", ["error", "warning", "info"])
def test_diagnostic_positive_matrix(severity: str) -> None:
    value = diagnostic_value()
    value["severity"] = severity
    value["location"] = {"start_line": 1, "start_column": 1}
    value["artifact_key"] = {
        "repository_id": "urn:raptor:repo:raptor",
        "artifact_id": "REQ-RAP-001",
    }
    diagnostic = Diagnostic.model_validate(value)
    assert diagnostic.severity.value == severity


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "lower.case"),
        ("severity", "fatal"),
        ("message", "   "),
        ("repository_id", "raptor"),
        ("document_id", "DOC-1"),
        ("repository_path", "../escape.md"),
        ("location", {"start_line": 0, "start_column": 1}),
        ("artifact_key", {"repository_id": "bad", "artifact_id": "REQ-RAP-001"}),
        ("unknown", True),
    ],
)
def test_diagnostic_negative_matrix(field: str, value: object) -> None:
    candidate = diagnostic_value()
    candidate[field] = value
    with pytest.raises(ValidationError):
        Diagnostic.model_validate(candidate)


def test_diagnostic_optional_fields_are_omitted() -> None:
    dumped = Diagnostic.model_validate(diagnostic_value()).model_dump(
        mode="json", exclude_none=True
    )
    assert "location" not in dumped and "artifact_key" not in dumped
