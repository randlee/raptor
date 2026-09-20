from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from raptor_schema import Measurement


@pytest.mark.parametrize(
    ("comparator", "target", "unit"),
    [
        ("eq", "ready", None), ("ne", True, None), ("eq", 3, "items"), ("eq", 3.5, "seconds"),
        ("lt", 3, None), ("lte", 3.5, "seconds"), ("gt", 0, None), ("gte", 0.0, None),
        ("range", [1, 2], "ms"), ("range", [1.0, 2.0], None),
    ],
)
def test_measurement_comparator_cells(comparator: str, target: object, unit: str | None) -> None:
    result = Measurement(name="threshold", comparator=comparator, target=target, unit=unit)
    assert result.comparator == comparator


@pytest.mark.parametrize(
    ("comparator", "target", "unit"),
    [
        ("lt", True, None), ("gte", "3", None), ("range", [1, 2.0], None),
        ("range", [True, False], None), ("range", [2, 1], None), ("eq", "ready", "ms"),
        ("range", [1, 2, 3], None), ("eq", float("nan"), None), ("range", [1.0, float("inf")], None),
    ],
)
def test_measurement_invalid_cells(comparator: str, target: object, unit: str | None) -> None:
    with pytest.raises(ValidationError):
        Measurement(name="threshold", comparator=comparator, target=target, unit=unit)


def test_canonical_negative_zero(document_dict: dict[str, object]) -> None:
    from raptor_schema import dump_canonical_json

    document_dict["artifacts"][1]["measurement"]["target"] = -0.0  # type: ignore[index]
    assert '"target":0.0' in dump_canonical_json(document_dict)
