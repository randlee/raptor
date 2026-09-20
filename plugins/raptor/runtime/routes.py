from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .agent_runner import AgentBackend, JsonValue, run_agent
from .dependencies import dependency_error, sc_compose_error

_SUPPORTED: dict[tuple[str, str | None, str | None], tuple[str, str]] = {
    ("import", "markdown", "json"): ("markdown-json-import", "markdown_to_json.py"),
    ("import", "md", "json"): ("markdown-json-import", "markdown_to_json.py"),
    ("import", "json", "sqlite"): ("json-sqlite-import", "import_sqlite.py"),
    ("export", "sqlite", "json"): ("sqlite-json-export", "export_sqlite.py"),
    ("export", "json", "markdown"): ("json-markdown-export", "json_to_markdown.py"),
    ("validate", "markdown", None): ("markdown-validate", "validate.py"),
    ("validate", "json", None): ("json-validate", "validate.py"),
    ("validate", "sqlite", None): ("sqlite-validate", "validate.py"),
}


def route(
    command: str,
    source: str | None = None,
    target: str | None = None,
    *,
    backend: AgentBackend | None = None,
    repository_root: Path | None = None,
    params: Mapping[str, JsonValue] | None = None,
) -> dict[str, Any]:
    """Resolve one public route and dispatch active work through the A3 runner."""
    dependency_failure = dependency_error()
    if dependency_failure is not None:
        return dependency_failure
    command = command.lower()
    normalized_source = source.lower() if source else None
    normalized_target = target.lower() if target else None
    values = {value.lower() for value in (source, target) if value}
    if "dolt" in values:
        return unsupported_envelope("Dolt")
    if (command, normalized_source, normalized_target) == (
        "round-trip",
        "migration",
        None,
    ):
        cli_failure = sc_compose_error()
        if cli_failure is not None:
            return cli_failure
        if backend is None or repository_root is None or params is None:
            return _unsupported(
                "RAPTOR.ROUTE.CONTEXT",
                "Round trip requires a client backend, repository root, and explicit paths.",
                "Provide every migration path and validate/apply intent.",
            )
        from .rendering import migration_round_trip

        required = {
            "markdown_input",
            "json_path",
            "database",
            "exported_json_path",
            "markdown_output",
        }
        if not required.issubset(params) or any(
            not isinstance(params[name], str) for name in required
        ):
            return _unsupported(
                "RAPTOR.ROUTE.INPUT",
                "Round-trip paths must be explicit strings.",
                "Provide all five repository-relative paths.",
            )
        return migration_round_trip(
            repository_root,
            str(params["markdown_input"]),
            str(params["json_path"]),
            str(params["database"]),
            str(params["exported_json_path"]),
            str(params["markdown_output"]),
            backend=backend,
            profile_id=str(params.get("profile_id", "raptor")),
            template_set=str(params.get("template_set", "raptor")),
            apply=params.get("apply") is True,
        )
    supported = _SUPPORTED.get((command, normalized_source, normalized_target))
    if supported is not None:
        if supported[0] in {"json-markdown-export", "migration-round-trip"}:
            cli_failure = sc_compose_error()
            if cli_failure is not None:
                return cli_failure
        agent, _ = supported
        if backend is None or repository_root is None:
            return _unsupported(
                "RAPTOR.ROUTE.CONTEXT",
                "Active routes require a client backend and repository root.",
                "Invoke the route through the Claude or Codex client adapter.",
            )
        return run_agent(
            agent=agent,
            params=params or {},
            backend=backend,
            repository_root=repository_root,
        )
    return unsupported_envelope("Sprint A5")


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
