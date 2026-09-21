from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


def dependency_error() -> dict[str, Any] | None:
    if sys.version_info < (3, 11):
        return _error("Python 3.11 or newer is required.")
    try:
        parts = version("pydantic").split(".")
        compatible = int(parts[0]) == 2 and int(parts[1]) >= 10
    except (PackageNotFoundError, ValueError, IndexError):
        compatible = False
    return None if compatible else _error("Pydantic >=2.10,<3 is required.")


def sc_compose_error() -> dict[str, Any] | None:
    from .rendering import resolve_sc_compose

    try:
        resolve_sc_compose()
    except ValueError as error:
        message = str(error)
        code = message.split(":", 1)[0]
        return _error(message, code=code)
    return None


def _error(
    message: str, *, code: str = "RAPTOR.DEPENDENCY.INCOMPATIBLE"
) -> dict[str, Any]:
    return {
        "success": False,
        "canceled": False,
        "aborted_by": None,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": False,
            "suggested_action": "Read references/installation-and-troubleshooting.md.",
        },
        "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
    }


__all__ = ["dependency_error", "sc_compose_error"]
