from __future__ import annotations

import json
import math
from typing import cast

from pydantic import BaseModel, JsonValue

from .models import JsonObject, SourceDocument


def _normalize(value: JsonValue) -> JsonValue:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON rejects non-finite floats")
        return 0.0 if value == 0.0 else value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def _encode_canonical_value(value: JsonValue) -> str:
    return json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def dump_canonical_fragment(value: BaseModel) -> str:
    return _encode_canonical_value(cast(JsonValue, value.model_dump(mode="json", exclude_none=True)))


def dump_canonical_json(value: SourceDocument | object) -> str:
    document = SourceDocument.model_validate(value)
    return _encode_canonical_value(cast(JsonObject, document.model_dump(mode="json", exclude_none=True))) + "\n"


def load_canonical_json(value: str | bytes | bytearray) -> SourceDocument:
    return SourceDocument.model_validate_json(value)


__all__ = ["dump_canonical_fragment", "dump_canonical_json", "load_canonical_json"]
