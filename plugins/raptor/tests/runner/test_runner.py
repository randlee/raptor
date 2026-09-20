from __future__ import annotations

import json
import shutil
import hashlib
import math
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
    logs = list((tmp_path / ".raptor/state/logs").glob("*.json"))
    assert len(logs) == 1 and logs[0].stem != key
    audit = json.loads(logs[0].read_text())
    assert audit["correlation_id"] == key
    assert audit["invocation_id"] == logs[0].stem
    assert set(audit) == {
        "timestamp",
        "agent",
        "version_frontmatter",
        "file_sha256",
        "invoker",
        "outcome",
        "duration_ms",
        "correlation_id",
        "invocation_id",
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


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra=True),
        lambda value: value["agents"]["json-validate"].update(extra=True),
        lambda value: value["agents"]["json-validate"].pop("version"),
        lambda value: value["agents"]["json-validate"].update(path="/tmp/agent.md"),
        lambda value: value["agents"]["json-validate"].update(path=1),
        lambda value: value["agents"]["json-validate"].update(version="v1"),
        lambda value: value["agents"]["json-validate"].update(sha256="ABC"),
        lambda value: value["skills"]["validate"].update(extra=True),
        lambda value: value["skills"]["validate"].update(depends_on=[]),
    ],
)
def test_every_malformed_registry_shape_is_resolution_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: object
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(ROOT / "agents", plugin / "agents")
    shutil.copy2(ROOT / "plugin-manifest.json", plugin / "plugin-manifest.json")
    path = plugin / "agents/registry.yaml"
    value = json.loads(path.read_text())
    mutation(value)  # type: ignore[operator]
    path.write_text(json.dumps(value))
    monkeypatch.setattr(agent_runner, "_plugin_root", lambda: plugin)
    result = run(monkeypatch, tmp_path, Backend([envelope()]))
    assert result["error"]["code"] == "REGISTRY.RESOLUTION"  # type: ignore[index]


@pytest.mark.parametrize(
    "response",
    [
        '```json\n{"success":true,"success":false}\n```',
        envelope().replace('"duration_ms": 1', '"duration_ms": NaN'),
        envelope().replace('"duration_ms": 1', '"duration_ms": Infinity'),
    ],
)
def test_duplicate_keys_and_nonfinite_constants_never_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, response: str
) -> None:
    backend = Backend([response])
    result = run(monkeypatch, tmp_path, backend)
    assert result["error"]["code"] == "EXECUTION.RESPONSE" and backend.calls == 1  # type: ignore[index]


def test_nonfinite_nested_params_never_invoke_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".raptor").mkdir()
    backend = Backend([envelope()])
    result = agent_runner.run_agent(
        agent="json-validate",
        params={"nested": [math.inf]},  # type: ignore[list-item]
        backend=backend,
        repository_root=tmp_path,
    )
    assert result["error"]["code"] == "EXECUTION.RESPONSE" and backend.calls == 0


@pytest.mark.parametrize("params", [{"tuple": (1, 2)}, {"bad-key": {1: "value"}}])
def test_non_json_recursive_params_never_invoke_backend(
    tmp_path: Path, params: object
) -> None:
    (tmp_path / ".raptor").mkdir()
    backend = Backend([envelope()])
    result = agent_runner.run_agent(
        agent="json-validate",
        params=params,  # type: ignore[arg-type]
        backend=backend,
        repository_root=tmp_path,
    )
    assert result["error"]["code"] == "EXECUTION.RESPONSE" and backend.calls == 0


def test_duplicate_registry_key_is_resolution_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(ROOT / "agents", plugin / "agents")
    shutil.copy2(ROOT / "plugin-manifest.json", plugin / "plugin-manifest.json")
    path = plugin / "agents/registry.yaml"
    text = path.read_text()
    path.write_text(text.replace('"agents": {', '"agents": {}, "agents": {', 1))
    monkeypatch.setattr(agent_runner, "_plugin_root", lambda: plugin)
    result = run(monkeypatch, tmp_path, Backend([envelope()]))
    assert result["error"]["code"] == "REGISTRY.RESOLUTION"  # type: ignore[index]


@pytest.mark.parametrize(
    "component", [".raptor", ".raptor/state", ".raptor/state/logs"]
)
def test_audit_rejects_symlinked_path_components(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, component: str
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    target = tmp_path / component
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        run(monkeypatch, tmp_path, Backend([envelope()]))


def test_audit_rejects_symlinked_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    logs = tmp_path / ".raptor/state/logs"
    logs.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("safe")

    class Invocation:
        hex = "fixed-invocation"

    monkeypatch.setattr(agent_runner.uuid, "uuid4", lambda: Invocation())
    (logs / "fixed-invocation.json").symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        run(monkeypatch, tmp_path, Backend([envelope()]))
    assert outside.read_text() == "safe"


def test_audit_uuid_collision_regenerates_without_overwriting_existing_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    logs = tmp_path / ".raptor/state/logs"
    logs.mkdir(parents=True)
    existing = logs / "fixed-invocation.json"
    existing.write_text("original")

    class Invocation:
        def __init__(self, value: str) -> None:
            self.hex = value

    values = iter((Invocation("fixed-invocation"), Invocation("replacement")))
    monkeypatch.setattr(agent_runner.uuid, "uuid4", lambda: next(values))
    result = run(monkeypatch, tmp_path, Backend([envelope()]))
    assert result["success"] is True
    assert existing.read_text() == "original"
    replacement = json.loads((logs / "replacement.json").read_text())
    assert replacement["invocation_id"] == "replacement"


def test_windows_audit_verifies_open_handle_before_writing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime import io as runtime_io

    discarded: list[int] = []
    monkeypatch.setattr(
        runtime_io,
        "_windows_open_exclusive",
        lambda path: runtime_io.os.open(
            path, runtime_io.os.O_WRONLY | runtime_io.os.O_CREAT | runtime_io.os.O_EXCL
        ),
    )
    monkeypatch.setattr(
        runtime_io, "_windows_final_path", lambda descriptor: "C:\\attacker\\audit.json"
    )
    monkeypatch.setattr(
        runtime_io,
        "_discard_windows_file",
        lambda descriptor: discarded.append(descriptor),
    )
    with pytest.raises(ValueError, match="reparse"):
        runtime_io._secure_windows_json(
            tmp_path, (".raptor", "state", "logs"), "audit.json", {"secret": "x"}
        )
    assert discarded
    assert (tmp_path / ".raptor/state/logs/audit.json").read_bytes() == b""


def test_each_invocation_has_unique_filename_with_stable_hashed_correlation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    run(monkeypatch, tmp_path, Backend([envelope()]))
    run(monkeypatch, tmp_path, Backend([envelope()]))
    records = [
        json.loads(path.read_text())
        for path in (tmp_path / ".raptor/state/logs").glob("*.json")
    ]
    assert len(records) == 2
    assert len({item["invocation_id"] for item in records}) == 2
    assert {item["correlation_id"] for item in records} == {
        hashlib.sha256(b"test").hexdigest()
    }


@pytest.mark.parametrize("swap_component", [".raptor", "state", "logs"])
def test_descriptor_bound_audit_resists_path_swap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, swap_component: str
) -> None:
    from runtime import io as runtime_io

    logs = tmp_path / ".raptor/state/logs"
    logs.mkdir(parents=True)
    captured, attacker = tmp_path / "captured", tmp_path / "attacker"
    attacker.mkdir()
    original_open = runtime_io.os.open
    swapped = False

    def swapping_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        descriptor = original_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]
        if path == swap_component and not swapped:
            swapped = True
            target = {
                ".raptor": logs.parents[1],
                "state": logs.parent,
                "logs": logs,
            }[swap_component]
            target.rename(captured)
            target.symlink_to(attacker, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(runtime_io.os, "open", swapping_open)
    result = run(monkeypatch, tmp_path, Backend([envelope()]))
    assert result["success"] is True
    destination = {
        ".raptor": captured / "state/logs",
        "state": captured / "logs",
        "logs": captured,
    }[swap_component]
    assert list(destination.glob("*.json")) and not list(attacker.iterdir())


def test_agent_executes_verified_private_snapshot_during_original_swap(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(ROOT / "agents", plugin / "agents")
    shutil.copy2(ROOT / "plugin-manifest.json", plugin / "plugin-manifest.json")
    original = plugin / "agents/json-validate.md"
    expected = original.read_bytes()
    monkeypatch.setattr(agent_runner, "_plugin_root", lambda: plugin)

    class SnapshotBackend(Backend):
        def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
            original.write_text("swapped")
            assert agent_path != original and agent_path.read_bytes() == expected
            assert agent_path.stat().st_mode & 0o777 == 0o400
            assert agent_path.parent.stat().st_mode & 0o777 == 0o700
            return super().invoke(
                agent_path=agent_path, prompt=prompt, timeout_s=timeout_s
            )

    assert run(monkeypatch, tmp_path, SnapshotBackend([envelope()]))["success"] is True


def test_redactor_normalizes_trace_and_common_secret_forms() -> None:
    value = agent_runner.redact(
        {
            "Stack-Trace": "hidden",
            "nested": {
                "AWS_ACCESS_KEY": "AKIA1234567890ABCDEF",
                "github_token": "ghp_12345678901234567890",
                "url": "https://user:password@example.test/x?token=secret",
                "dsn": "postgresql://admin:database-secret@example.test/db",
                "pem": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
                "message": "TOKEN=supersecret AccountKey=storage-secret Basic YWRtaW46c2VjcmV0 AIza12345678901234567890123456789012345 sk_live_1234567890 xoxb-1234567890 xoxc-1234567890 glpat-1234567890 github_pat_12345678901234567890 eyJabc.def.ghi ASIA1234567890ABCDEF",
                "nested_url": "https://host/x?client_secret=deep-secret&ok=1",
            },
        }
    )
    assert "Stack-Trace" not in value
    text = json.dumps(value)
    assert "AKIA" not in text and "ghp_" not in text and "password@" not in text
    assert "BEGIN PRIVATE" not in text and "token=secret" not in text
    for secret in (
        "supersecret",
        "storage-secret",
        "database-secret",
        "YWRtaW",
        "AIza",
        "sk_live_",
        "xoxb-",
        "xoxc-",
        "glpat-",
        "github_pat_",
        "eyJabc",
        "ASIA",
        "deep-secret",
    ):
        assert secret not in text
