from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import Measurement, dump_canonical_json


def test_measurement_shared_comparator_type_unit_matrix(measurement_cases: tuple[object, ...]) -> None:
    for case in measurement_cases:
        values = {
            "name": "threshold",
            "comparator": case.comparator,  # type: ignore[attr-defined]
            "target": case.target,  # type: ignore[attr-defined]
            "unit": case.unit,  # type: ignore[attr-defined]
        }
        if case.valid:  # type: ignore[attr-defined]
            assert Measurement.model_validate(values).comparator == case.comparator  # type: ignore[attr-defined]
        else:
            with pytest.raises(ValidationError):
                Measurement.model_validate(values)


@pytest.mark.parametrize(
    ("comparator", "target", "error"),
    [
        *[
            (comparator, target, "finite")
            for comparator in ("eq", "ne", "lt", "lte", "gt", "gte")
            for target in (float("nan"), float("inf"), float("-inf"))
        ],
        ("range", [2, 1], "lower endpoint"),
        ("range", [2.5, 1.5], "lower endpoint"),
        ("range", [1.0, float("inf")], "finite"),
        ("range", [float("-inf"), 1.0], "finite"),
    ],
)
def test_measurement_python_only_numeric_constraints(
    comparator: str, target: object, error: str
) -> None:
    with pytest.raises(ValidationError, match=error):
        Measurement(name="threshold", comparator=comparator, target=target)


def test_measurement_strict_bool_int_and_explicit_null_unit() -> None:
    assert Measurement(name="flag", comparator="eq", target=True).target is True
    assert Measurement(name="count", comparator="eq", target=1).target == 1
    assert Measurement(name="state", comparator="eq", target="ready", unit=None).unit is None


def test_canonical_negative_zero(document_dict: dict[str, object]) -> None:
    document_dict["artifacts"][1]["measurement"]["target"] = -0.0  # type: ignore[index]
    assert '"target":0.0' in dump_canonical_json(document_dict)
