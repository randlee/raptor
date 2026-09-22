from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from pydantic import ValidationError

from .agent_runner import redact


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
    if isinstance(error, ValidationError):
        code = "RAPTOR.VALIDATION.ERROR"
        message = "RAPTOR.VALIDATION.ERROR: input failed schema validation"
    elif code == "RAPTOR.CLI.ERROR":
        message = "RAPTOR.CLI.ERROR: operation failed"
    suggested_action = getattr(
        error,
        "suggested_action",
        "Correct the reported plugin state and retry.",
    )
    message = cast(str, redact(message))
    suggested_action = cast(str, redact(suggested_action))
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
    safe = cast(dict[str, Any], redact(value))
    print("```json")
    print(json.dumps(safe, sort_keys=True, separators=(",", ":")))
    print("```")
    return 0 if value["success"] else 1


def invoke(operation: Callable[[], dict[str, Any] | None]) -> int:
    try:
        return emit(success(operation()))
    except Exception as error:
        return emit(failure(error))


__all__ = ["emit", "failure", "invoke", "success"]
