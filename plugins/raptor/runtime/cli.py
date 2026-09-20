from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


def success(data: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "success": True,
        "canceled": False,
        "aborted_by": None,
        "data": data or {},
        "error": None,
        "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
    }


def failure(error: Exception) -> dict[str, Any]:
    message = str(error)
    prefix = message.split(":", 1)[0]
    code = prefix if prefix.startswith("RAPTOR.") else "RAPTOR.CLI.ERROR"
    diagnostic = getattr(error, "diagnostic", None)
    if diagnostic is not None and hasattr(diagnostic, "model_dump"):
        message = json.dumps(
            diagnostic.model_dump(mode="json", exclude_none=True),
            sort_keys=True,
            separators=(",", ":"),
        )
    suggested_action = getattr(
        error,
        "suggested_action",
        "Correct the reported plugin state and retry.",
    )
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": False,
            "suggested_action": suggested_action,
        },
        "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
    }


def emit(value: dict[str, Any]) -> int:
    print("```json")
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))
    print("```")
    return 0 if value["success"] else 1


def invoke(operation: Callable[[], dict[str, Any] | None]) -> int:
    try:
        return emit(success(operation()))
    except Exception as error:
        return emit(failure(error))


__all__ = ["emit", "failure", "invoke", "success"]
