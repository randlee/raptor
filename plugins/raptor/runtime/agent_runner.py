from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import uuid
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from typing import Any, Protocol, cast

JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
_FENCE = re.compile(r"\A\s*```json\s*(\{.*\})\s*```\s*\Z", re.DOTALL)
_SECRET_KEY = re.compile(r"(?:secret|token|password|api[_-]?key|authorization)", re.I)
_SECRET_VALUE = re.compile(r"(?:Bearer\s+\S+|sk-[A-Za-z0-9_-]{8,})", re.I)
_TRACE_KEYS = {"tool_trace", "tool_traces", "raw_output", "transcript"}


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
        return {
            key: "[REDACTED]" if _SECRET_KEY.search(key) else _redact(item)
            for key, item in value.items()
            if key not in _TRACE_KEYS
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub("[REDACTED]", value)
    return value


def _parse_envelope(response: str) -> dict[str, Any]:
    match = _FENCE.fullmatch(response)
    if match is None:
        raise ValueError("response must contain exactly one fenced JSON object")
    value = json.loads(match.group(1))
    if not isinstance(value, dict):
        raise ValueError("response envelope must be an object")
    required = {"success", "canceled", "aborted_by", "data", "error", "metadata"}
    if (
        set(value) != required
        or not isinstance(value["success"], bool)
        or not isinstance(value["canceled"], bool)
    ):
        raise ValueError("response does not match the standard envelope")
    metadata = value["metadata"]
    if not isinstance(metadata, dict) or not all(
        isinstance(metadata.get(key), int)
        for key in ("duration_ms", "tool_calls", "retry_count")
    ):
        raise ValueError("response metadata is invalid")
    error = value["error"]
    if value["success"]:
        if error is not None or value["canceled"]:
            raise ValueError("successful response has contradictory fields")
    elif not isinstance(error, dict) or not all(
        key in error for key in ("code", "message", "recoverable", "suggested_action")
    ):
        raise ValueError("failure response has no standard error")
    return cast(dict[str, Any], _redact(value))


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _audit(
    *,
    agent: str,
    version: str,
    digest: str,
    outcome: str,
    duration_ms: int,
    correlation_id: str | None,
) -> None:
    identifier = re.sub(r"[^A-Za-z0-9_.-]", "_", correlation_id or uuid.uuid4().hex)
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
        record["correlation_id"] = correlation_id
    _atomic_json(
        _repository_root(Path.cwd()) / ".raptor/state/logs" / f"{identifier}.json",
        record,
    )


def _repository_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / ".raptor").is_dir():
            return candidate
    return current


def run_agent(
    *,
    agent: str,
    params: Mapping[str, JsonValue],
    version_constraint: str | None = None,
    timeout_s: int = 120,
    correlation_id: str | None = None,
    backend: AgentBackend,
) -> dict[str, Any]:
    started = time.monotonic()
    plugin_root = _plugin_root()
    version = "unknown"
    digest = "unknown"
    result: dict[str, Any] | None = None
    try:
        registry = json.loads(
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
            prompt = json.dumps(
                {"agent": agent, "params": params},
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            return _error("EXECUTION.RESPONSE", "Agent parameters are not valid JSON.")
        for attempt in range(2):
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(
                    backend.invoke,
                    agent_path=agent_path,
                    prompt=prompt,
                    timeout_s=timeout_s,
                )
                try:
                    response = future.result(timeout=timeout_s)
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                result = _parse_envelope(response)
            except (FutureTimeout, TimeoutError, subprocess.TimeoutExpired):
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
        )


__all__ = ["AgentBackend", "JsonValue", "run_agent"]
