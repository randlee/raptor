from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass(frozen=True)
class MeasurementCase:
    name: str
    comparator: str
    target: object
    unit: str | None
    valid: bool


@pytest.fixture(scope="session")
def measurement_cases() -> tuple[MeasurementCase, ...]:
    cases: list[MeasurementCase] = []
    scalar_targets = (("string", "ready", False), ("boolean", True, False), ("integer", 3, True), ("float", 3.5, True))
    for comparator in ("eq", "ne"):
        for label, target, numeric in scalar_targets:
            cases.append(MeasurementCase(f"{comparator}-{label}-no-unit", comparator, target, None, True))
            cases.append(MeasurementCase(f"{comparator}-{label}-unit", comparator, target, "ms", numeric))
    for comparator in ("lt", "lte", "gt", "gte"):
        for label, target, numeric in scalar_targets:
            cases.append(MeasurementCase(f"{comparator}-{label}-no-unit", comparator, target, None, numeric))
            cases.append(MeasurementCase(f"{comparator}-{label}-unit", comparator, target, "ms", numeric))
    cases.extend(
        (
            MeasurementCase("range-integers", "range", [1, 2], None, True),
            MeasurementCase("range-integers-unit", "range", [1, 2], "ms", True),
            MeasurementCase("range-floats", "range", [1.5, 2.5], None, True),
            MeasurementCase("range-floats-unit", "range", [1.5, 2.5], "ms", True),
            MeasurementCase("range-mixed", "range", [1, 2.5], None, False),
            MeasurementCase("range-booleans", "range", [True, False], None, False),
            MeasurementCase("range-strings", "range", ["a", "b"], None, False),
            MeasurementCase("range-short", "range", [1], None, False),
            MeasurementCase("range-long", "range", [1, 2, 3], None, False),
            MeasurementCase("range-scalar", "range", 1, None, False),
        )
    )
    return tuple(cases)
