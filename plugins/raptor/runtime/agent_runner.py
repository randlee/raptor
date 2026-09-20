from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

from .io import atomic_json
from .registry import parse_registry
from .strict_json import is_value, loads

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
_FENCE = re.compile(r"\A\s*```json\s*(\{.*\})\s*```\s*\Z", re.DOTALL)
_SECRET_KEY = re.compile(
    r"(?:secret|token|pass(?:word)?|api.?key|authorization|credential|private.?key|access.?key)",
    re.I,
)
_SECRET_VALUE = re.compile(
    r"(?:Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----|https?://[^\s/@:]+:[^\s/@]+@)",
    re.I | re.DOTALL,
)
_URL_SECRET = re.compile(
    r"([?&](?:token|key|secret|password|signature)=)[^&#\s]+", re.I
)
_TRACE_KEYS = {
    "tooltrace",
    "tooltraces",
    "rawoutput",
    "transcript",
    "trace",
    "traces",
    "stacktrace",
}


class AgentBackend(Protocol):
    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str: ...


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _error(code: str, message: str, *, canceled: bool = False) -> dict[str, Any]:
    return {
        "success": False,
        "canceled": canceled,
        "aborted_by": "timeout" if canceled else None,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "recoverable": False,
            "suggested_action": "Correct the plugin configuration or response and retry.",
        },
        "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
    }


def _version_matches(actual: str, constraint: str) -> bool:
    if constraint.endswith(".x"):
        return actual.split(".", 1)[0] == constraint[:-2]
    return actual == constraint


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in _TRACE_KEYS:
                continue
            result[key] = (
                "[REDACTED]" if _SECRET_KEY.search(normalized) else _redact(item)
            )
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _URL_SECRET.sub(r"\1[REDACTED]", _SECRET_VALUE.sub("[REDACTED]", value))
    return value


def _parse_envelope(response: str) -> dict[str, Any]:
    match = _FENCE.fullmatch(response)
    if match is None:
        raise ValueError("response must contain exactly one fenced JSON object")
    value = loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("response envelope must be an object")
    required = {"success", "canceled", "aborted_by", "data", "error", "metadata"}
    if not is_value(value):
        raise ValueError("response is not finite JSON")
    if (
        set(value) != required
        or type(value["success"]) is not bool
        or type(value["canceled"]) is not bool
    ):
        raise ValueError("response does not match the standard envelope")
    if value["aborted_by"] is not None and value["aborted_by"] not in (
        "user",
        "policy",
        "timeout",
    ):
        raise ValueError("response aborted_by is invalid")
    if value["data"] is not None and not isinstance(value["data"], dict):
        raise ValueError("response data must be an object or null")
    metadata = value["metadata"]
    if (
        not isinstance(metadata, dict)
        or set(metadata)
        - {"duration_ms", "tool_calls", "retry_count", "correlation_id"}
        or not {"duration_ms", "tool_calls", "retry_count"}.issubset(metadata)
    ):
        raise ValueError("response metadata is invalid")
    if any(
        type(metadata[key]) is not int or metadata[key] < 0
        for key in ("duration_ms", "tool_calls", "retry_count")
    ):
        raise ValueError("response telemetry is invalid")
    if "correlation_id" in metadata and not isinstance(metadata["correlation_id"], str):
        raise ValueError("response correlation_id is invalid")
    error = value["error"]
    if value["success"]:
        if error is not None or value["canceled"] or value["aborted_by"] is not None:
            raise ValueError("successful response has contradictory fields")
    else:
        error_keys = {"code", "message", "recoverable", "suggested_action"}
        if not isinstance(error, dict) or set(error) != error_keys:
            raise ValueError("failure response has no standard error")
        if (
            any(
                not isinstance(error[key], str) or not error[key]
                for key in ("code", "message", "suggested_action")
            )
            or type(error["recoverable"]) is not bool
        ):
            raise ValueError("failure response error is invalid")
        if value["canceled"] != (value["aborted_by"] is not None):
            raise ValueError("failure cancellation fields are contradictory")
    return cast(dict[str, Any], _redact(value))


def _audit(
    *,
    agent: str,
    version: str,
    digest: str,
    outcome: str,
    duration_ms: int,
    correlation_id: str | None,
    repository_root: Path,
) -> None:
    identifier = hashlib.sha256(
        (correlation_id or uuid.uuid4().hex).encode()
    ).hexdigest()
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "agent": agent,
        "version_frontmatter": version,
        "file_sha256": digest,
        "invoker": "raptor-agent-runner",
        "outcome": outcome,
        "duration_ms": duration_ms,
    }
    if correlation_id is not None:
        record["correlation_id"] = identifier
    current = repository_root
    for relative in (".raptor", ".raptor/state", ".raptor/state/logs"):
        path = repository_root / relative
        if path.is_symlink():
            raise ValueError("audit path contains a symlink")
        path.mkdir(exist_ok=True)
        resolved = path.resolve()
        if repository_root not in resolved.parents:
            raise ValueError("audit path escapes repository root")
        current = path
    destination = current / f"{identifier}.json"
    if destination.is_symlink():
        raise ValueError("audit destination is a symlink")
    atomic_json(destination, record)


def run_agent(
    *,
    agent: str,
    params: Mapping[str, JsonValue],
    version_constraint: str | None = None,
    timeout_s: int = 120,
    correlation_id: str | None = None,
    backend: AgentBackend,
    repository_root: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    plugin_root = _plugin_root()
    version = "unknown"
    digest = "unknown"
    result: dict[str, Any] | None = None
    repository_root = repository_root.resolve()
    if not repository_root.is_dir() or not (
        (repository_root / ".git").exists() or (repository_root / ".raptor").is_dir()
    ):
        raise ValueError("repository_root must identify a repository")
    try:
        registry = parse_registry(
            (plugin_root / "agents/registry.yaml").read_text(encoding="utf-8")
        )
        entry = registry["agents"].get(agent)
        if not isinstance(entry, dict):
            raise LookupError("agent is not registered")
        version = entry["version"]
        constraint = version_constraint or version
        if not _version_matches(version, constraint):
            result = _error(
                "REGISTRY.VERSION", "Agent version constraint is not satisfied."
            )
            return result
        agents_root = (plugin_root / "agents").resolve()
        agent_path = (plugin_root / entry["path"]).resolve()
        if agent_path.parent != agents_root or not agent_path.is_file():
            raise LookupError("registered agent path is outside the allowlist")
        digest = _sha256(agent_path)
        manifest = json.loads(
            (plugin_root / "plugin-manifest.json").read_text(encoding="utf-8")
        )
        if (
            manifest.get("agents", {}).get(agent) != digest
            or entry.get("sha256") != digest
        ):
            result = _error(
                "REGISTRY.HASH", "Registered agent hash does not match inventory."
            )
            return result
        try:
            parameter_value = dict(params)
            if not is_value(parameter_value):
                raise ValueError("parameters are not recursive JSON values")
            prompt = json.dumps(
                {"agent": agent, "params": parameter_value},
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            return _error("EXECUTION.RESPONSE", "Agent parameters are not valid JSON.")
        for attempt in range(2):
            try:
                response = backend.invoke(
                    agent_path=agent_path,
                    prompt=prompt,
                    timeout_s=timeout_s,
                )
                result = _parse_envelope(response)
            except (TimeoutError, subprocess.TimeoutExpired):
                result = _error(
                    "EXECUTION.TIMEOUT", "Agent exceeded its timeout.", canceled=True
                )
            except Exception as error:
                result = _error(
                    "EXECUTION.RESPONSE",
                    f"Agent response failed validation: {type(error).__name__}",
                )
            result["metadata"]["retry_count"] = attempt
            error_value = result.get("error")
            if (
                result["success"]
                or not isinstance(error_value, dict)
                or not error_value.get("recoverable")
                or attempt == 1
            ):
                break
        assert result is not None
        return result
    except (KeyError, OSError, ValueError, LookupError, json.JSONDecodeError):
        return _error("REGISTRY.RESOLUTION", "Agent registry resolution failed.")
    finally:
        duration = int((time.monotonic() - started) * 1000)
        outcome = (
            "success"
            if "result" in locals() and result and result.get("success")
            else "failure"
        )
        _audit(
            agent=agent,
            version=version,
            digest=digest,
            outcome=outcome,
            duration_ms=duration,
            correlation_id=correlation_id,
            repository_root=repository_root,
        )


__all__ = ["AgentBackend", "JsonValue", "run_agent"]
