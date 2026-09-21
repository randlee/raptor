from __future__ import annotations

import json
import math
from typing import Any


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def loads(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON constant: {value}")
        ),
    )


def is_value(value: Any) -> bool:
    if value is None or type(value) in {bool, int, str}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(is_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and is_value(item) for key, item in value.items()
        )
    return False


__all__ = ["is_value", "loads"]
