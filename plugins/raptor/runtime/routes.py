from __future__ import annotations

from typing import Any

from .cli import success
from .dependencies import dependency_error

_SUPPORTED: dict[tuple[str, str | None, str | None], tuple[str, str]] = {
    ("import", "markdown", "json"): ("markdown-json-import", "markdown_to_json.py"),
    ("import", "md", "json"): ("markdown-json-import", "markdown_to_json.py"),
    ("import", "json", "sqlite"): ("json-sqlite-import", "import_sqlite.py"),
    ("export", "sqlite", "json"): ("sqlite-json-export", "export_sqlite.py"),
    ("validate", "markdown", None): ("markdown-validate", "validate.py"),
    ("validate", "json", None): ("json-validate", "validate.py"),
    ("validate", "sqlite", None): ("sqlite-validate", "validate.py"),
}


def route(
    command: str, source: str | None = None, target: str | None = None
) -> dict[str, Any]:
    """Return A3's explicit route boundary without invoking an agent."""
    dependency_failure = dependency_error()
    if dependency_failure is not None:
        return dependency_failure
    command = command.lower()
    normalized_source = source.lower() if source else None
    normalized_target = target.lower() if target else None
    values = {value.lower() for value in (source, target) if value}
    if "dolt" in values:
        return unsupported_envelope("Dolt")
    supported = _SUPPORTED.get((command, normalized_source, normalized_target))
    if supported is not None:
        agent, script = supported
        return success({"agent": agent, "script": f"scripts/{script}"})
    owner = (
        "A5"
        if command == "round-trip"
        or (command == "export" and normalized_target == "markdown")
        else "A4"
    )
    return unsupported_envelope(f"Sprint {owner}")


def unsupported_envelope(policy: str) -> dict[str, Any]:
    if policy == "Dolt":
        return _unsupported(
            "RAPTOR.UNSUPPORTED.DOLT",
            "Dolt support is reserved for a later phase.",
            "Use a supported route until Dolt support is available.",
        )
    if policy not in {"Sprint A4", "Sprint A5"}:
        raise ValueError("unknown unsupported policy")
    owner = policy.removeprefix("Sprint ")
    return _unsupported(
        "RAPTOR.UNSUPPORTED.PHASE",
        f"This route is activated in Sprint {owner}.",
        f"Use the Sprint {owner} implementation when available.",
    )


def _unsupported(code: str, message: str, suggested_action: str) -> dict[str, Any]:
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


__all__ = ["route", "unsupported_envelope"]
