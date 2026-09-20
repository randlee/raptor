from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import Diagnostic, SourceLocation


@pytest.mark.parametrize(
    "value",
    [
        {"start_line": 0, "start_column": 1},
        {"start_line": 2, "start_column": 3, "end_line": 1, "end_column": 9},
        {"start_line": 1, "start_column": 1, "end_line": 2},
    ],
)
def test_location_constraints(value: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        SourceLocation.model_validate(value)


def test_diagnostic_shape_and_omission() -> None:
    diagnostic = Diagnostic(
        code="RAPTOR.PROFILE.VALIDATION",
        severity="error",
        message="invalid source",
        repository_id="urn:raptor:repo:raptor",
        document_id="DOC-RAP-001",
        repository_path="docs/requirements.md",
    )
    dumped = diagnostic.model_dump(mode="json", exclude_none=True)
    assert "location" not in dumped and "artifact_key" not in dumped
    with pytest.raises(ValidationError):
        Diagnostic.model_validate({**dumped, "code": "lower.case"})
