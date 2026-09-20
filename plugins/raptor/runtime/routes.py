from __future__ import annotations

from typing import Any

from .dependencies import dependency_error


def route(
    command: str, source: str | None = None, target: str | None = None
) -> dict[str, Any]:
    """Return A3's explicit route boundary without invoking an agent."""
    dependency_failure = dependency_error()
    if dependency_failure is not None:
        return dependency_failure
    command = command.lower()
    normalized_target = target.lower() if target else None
    values = {value.lower() for value in (source, target) if value}
    if "dolt" in values:
        return _unsupported(
            "RAPTOR.UNSUPPORTED.DOLT",
            "Dolt support is reserved for a later phase.",
        )
    owner = (
        "A5"
        if command == "round-trip"
        or (command == "export" and normalized_target == "markdown")
        else "A4"
    )
    return _unsupported(
        "RAPTOR.UNSUPPORTED.PHASE",
        f"The {command} route is activated in Sprint {owner}.",
    )


def _unsupported(code: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": False,
            "suggested_action": "Use the owning sprint implementation when available.",
        },
        "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
    }


__all__ = ["route"]
