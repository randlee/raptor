from __future__ import annotations

import json
import shutil
import hashlib
from pathlib import Path

import pytest

from runtime import agent_runner

ROOT = Path(__file__).parents[2]


def envelope(*, success: bool = True, recoverable: bool = False) -> str:
    error = (
        None
        if success
        else {
            "code": "TEST.RETRY",
            "message": "retry",
            "recoverable": recoverable,
            "suggested_action": "retry",
        }
    )
    value = {
        "success": success,
        "canceled": False,
        "aborted_by": None,
        "data": {"token": "sk-secret-value", "tool_trace": ["hidden"]}
        if success
        else None,
        "error": error,
        "metadata": {"duration_ms": 1, "tool_calls": 0, "retry_count": 0},
    }
    return f"```json\n{json.dumps(value)}\n```"


class Backend:
    def __init__(self, responses: list[str], delay: float = 0) -> None:
        self.responses = responses
        self.delay = delay
        self.calls = 0

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        self.calls += 1
        if self.delay:
            raise TimeoutError("backend-owned timeout")
        return self.responses[min(self.calls - 1, len(self.responses) - 1)]


def run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, backend: Backend, **values: object
) -> dict[str, object]:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".raptor").mkdir(exist_ok=True)
    return agent_runner.run_agent(
        agent=str(values.get("agent", "json-validate")),
        params={},
        version_constraint=values.get("version_constraint"),  # type: ignore[arg-type]
        timeout_s=int(values.get("timeout_s", 1)),
        correlation_id="test",
        backend=backend,
        repository_root=tmp_path,
    )


def test_success_redaction_and_atomic_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    result = run(monkeypatch, tmp_path, Backend([envelope()]))
    assert result["success"] is True
    assert result["data"] == {"token": "[REDACTED]"}
    key = hashlib.sha256(b"test").hexdigest()
    audit = json.loads((tmp_path / f".raptor/state/logs/{key}.json").read_text())
    assert audit["correlation_id"] == key
    assert set(audit) == {
        "timestamp",
        "agent",
        "version_frontmatter",
        "file_sha256",
        "invoker",
        "outcome",
        "duration_ms",
        "correlation_id",
    }


def test_repository_root_is_explicit_and_valid(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository_root"):
        agent_runner.run_agent(
            agent="json-validate",
            params={},
            backend=Backend([envelope()]),
            repository_root=tmp_path / "missing",
        )


@pytest.mark.parametrize(
    "field,value", [("duration_ms", True), ("tool_calls", -1), ("retry_count", 1.5)]
)
def test_telemetry_requires_non_bool_nonnegative_integers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, field: str, value: object
) -> None:
    body = json.loads(envelope().split("\n", 1)[1].rsplit("\n", 1)[0])
    body["metadata"][field] = value
    result = run(monkeypatch, tmp_path, Backend([f"```json\n{json.dumps(body)}\n```"]))
    assert result["error"]["code"] == "EXECUTION.RESPONSE"  # type: ignore[index]


def test_malformed_recoverable_never_retries(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = json.loads(envelope(success=False).split("\n", 1)[1].rsplit("\n", 1)[0])
    body["error"]["recoverable"] = "true"
    backend = Backend([f"```json\n{json.dumps(body)}\n```"])
    result = run(monkeypatch, tmp_path, backend)
    assert result["error"]["code"] == "EXECUTION.RESPONSE" and backend.calls == 1  # type: ignore[index]


@pytest.mark.parametrize(
    "updates",
    [
        {"aborted_by": "host"},
        {"data": []},
        {"success": True, "canceled": True, "aborted_by": "user"},
        {"success": False, "canceled": False, "aborted_by": "user"},
        {"success": False, "canceled": True, "aborted_by": None},
    ],
)
def test_envelope_cross_field_invariants(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, updates: dict[str, object]
) -> None:
    body = json.loads(envelope().split("\n", 1)[1].rsplit("\n", 1)[0])
    body.update(updates)
    if body["success"] is False:
        body["error"] = {
            "code": "X",
            "message": "x",
            "recoverable": False,
            "suggested_action": "x",
        }
    result = run(monkeypatch, tmp_path, Backend([f"```json\n{json.dumps(body)}\n```"]))
    assert result["error"]["code"] == "EXECUTION.RESPONSE"  # type: ignore[index]


@pytest.mark.parametrize(
    "response", ["{}", "```json\n{}\n```", f"{envelope()}\n{envelope()}"]
)
def test_malformed_unfenced_and_multiple_responses_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: str
) -> None:
    assert (
        run(monkeypatch, tmp_path, Backend([response]))["error"]["code"]
        == "EXECUTION.RESPONSE"
    )  # type: ignore[index]


def test_unknown_version_hash_and_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    assert (
        run(monkeypatch, tmp_path, Backend([envelope()]), agent="unknown")["error"][
            "code"
        ]
        == "REGISTRY.RESOLUTION"
    )  # type: ignore[index]
    assert (
        run(monkeypatch, tmp_path, Backend([envelope()]), version_constraint="2.x")[
            "error"
        ]["code"]
        == "REGISTRY.VERSION"
    )  # type: ignore[index]
    monkeypatch.setattr(agent_runner, "_sha256", lambda path: "0" * 64)
    assert (
        run(monkeypatch, tmp_path, Backend([envelope()]))["error"]["code"]
        == "REGISTRY.HASH"
    )  # type: ignore[index]
    monkeypatch.undo()
    assert (
        run(monkeypatch, tmp_path, Backend([envelope()], delay=0.05), timeout_s=0)[
            "error"
        ]["code"]
        == "EXECUTION.TIMEOUT"
    )  # type: ignore[index]


def test_recoverable_response_retries_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    backend = Backend([envelope(success=False, recoverable=True), envelope()])
    result = run(monkeypatch, tmp_path, backend)
    assert result["success"] is True and backend.calls == 2
    assert result["metadata"]["retry_count"] == 1  # type: ignore[index]


def test_retry_is_capped_at_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    backend = Backend([envelope(success=False, recoverable=True)])
    result = run(monkeypatch, tmp_path, backend)
    assert result["success"] is False and backend.calls == 2
    assert result["metadata"]["retry_count"] == 1  # type: ignore[index]


def test_registered_path_escape_is_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(ROOT / "agents", plugin / "agents")
    shutil.copy2(ROOT / "plugin-manifest.json", plugin / "plugin-manifest.json")
    registry_path = plugin / "agents/registry.yaml"
    registry = json.loads(registry_path.read_text())
    registry["agents"]["json-validate"]["path"] = "../escape.md"
    registry_path.write_text(json.dumps(registry))
    (tmp_path / "escape.md").write_text("escape")
    monkeypatch.setattr(agent_runner, "_plugin_root", lambda: plugin)
    assert (
        run(monkeypatch, tmp_path, Backend([envelope()]))["error"]["code"]
        == "REGISTRY.RESOLUTION"
    )  # type: ignore[index]
