from __future__ import annotations

import shutil
import json
import sys
import time
from pathlib import Path

import pytest

from runtime.bootstrap import BootstrapError, bootstrap
from runtime.client_adapters.claude import ClaudeBackend
from runtime.client_adapters.codex import CodexBackend
from runtime.client_adapters.environment import allowed_environment
from runtime.client_adapters.process import invoke_process
from runtime.client_adapters import process as process_runtime

ROOT = Path(__file__).parents[2]


def test_bootstrap_loads_verified_vendor(monkeypatch: pytest.MonkeyPatch) -> None:
    prior = sys.modules.pop("raptor_schema", None)
    monkeypatch.setattr(
        sys, "path", [item for item in sys.path if "schema/src" not in item]
    )
    try:
        module = bootstrap(ROOT)
        assert str(ROOT / "_vendor") in str(Path(module.__file__).resolve())
    finally:
        for name in tuple(sys.modules):
            if name == "raptor_schema" or name.startswith("raptor_schema."):
                sys.modules.pop(name)
        if prior is not None:
            sys.modules["raptor_schema"] = prior


def test_bootstrap_rejects_already_loaded_foreign_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Foreign:
        __file__ = "/tmp/foreign/raptor_schema/__init__.py"

    monkeypatch.setitem(sys.modules, "raptor_schema", Foreign())
    with pytest.raises(BootstrapError, match="PRECEDENCE"):
        bootstrap(ROOT)


def test_bootstrap_rejects_vendor_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = tmp_path / "raptor"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    (plugin / "_vendor/raptor_schema/canonical.py").write_text(
        "tampered", encoding="utf-8"
    )
    for name in tuple(sys.modules):
        if name == "raptor_schema" or name.startswith("raptor_schema."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    with pytest.raises(BootstrapError, match="VENDOR_HASH"):
        bootstrap(plugin)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.update(extra=True),
        lambda value: value.update(name="other"),
        lambda value: value["requires"].update(extra=True),
        lambda value: value["vendor"].update(algorithm="other"),
        lambda value: value["vendor"].update(canonical_schema_version="2.0.0"),
        lambda value: value["vendor"].update(package_version="2.0.0"),
        lambda value: value["vendor"].pop("inventory"),
        lambda value: value.update(inventory=["../escape"]),
        lambda value: value.update(inventory=[1]),
        lambda value: value["vendor"].update(inventory=[1]),
        lambda value: value["vendor"].update(tree_sha256=True),
        lambda value: value.update(agents={}),
    ],
)
def test_bootstrap_rejects_every_malformed_manifest_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: object
) -> None:
    plugin = tmp_path / "raptor"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    path = plugin / "plugin-manifest.json"
    value = json.loads(path.read_text())
    mutation(value)  # type: ignore[operator]
    path.write_text(json.dumps(value))
    for name in tuple(sys.modules):
        if name == "raptor_schema" or name.startswith("raptor_schema."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    with pytest.raises(BootstrapError, match="MANIFEST"):
        bootstrap(plugin)


def test_bootstrap_rejects_extra_packaged_file_and_agent_registry_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = tmp_path / "raptor"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    (plugin / "runtime/extra.py").write_text("extra")
    with pytest.raises(BootstrapError, match="packaged inventory"):
        bootstrap(plugin)
    (plugin / "runtime/extra.py").unlink()
    (plugin / "agents/json-validate.md").write_text("tampered")
    for name in tuple(sys.modules):
        if name == "raptor_schema" or name.startswith("raptor_schema."):
            monkeypatch.delitem(sys.modules, name, raising=False)
    with pytest.raises(BootstrapError, match="REGISTRY"):
        bootstrap(plugin)


def test_client_adapters_only_own_host_invocation() -> None:
    for path in (ROOT / "runtime/client_adapters").glob("*.py"):
        text = path.read_text()
        assert "registry" not in text
        assert "RAPTOR.UNSUPPORTED" not in text
        assert "json.loads" not in text


@pytest.mark.parametrize("backend", [ClaudeBackend("host"), CodexBackend("host")])
def test_client_adapters_satisfy_same_invocation_contract(
    monkeypatch: pytest.MonkeyPatch, backend: object, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    class Process:
        returncode = 0

        def __init__(self, command: list[str], **values: object) -> None:
            self.pid = 1234
            calls.append((command, values))

        def communicate(self, timeout: int) -> tuple[str, str]:
            assert timeout == 9
            return "response", ""

        def poll(self) -> int:
            return 0

    monkeypatch.setattr("subprocess.Popen", Process)
    result = backend.invoke(
        agent_path=tmp_path / "agent.md", prompt="prompt", timeout_s=9
    )  # type: ignore[attr-defined]
    assert result == "response"
    assert calls[0][1]["env"] == allowed_environment()
    assert calls[0][1].get("start_new_session") is True


def test_adapter_environment_excludes_ambient_credentials() -> None:
    values = allowed_environment(
        {
            "PATH": "/bin",
            "HOME": "/home/test",
            "AWS_SECRET_ACCESS_KEY": "secret",
            "RAPTOR_TOKEN": "token",
        }
    )
    assert values == {"PATH": "/bin", "HOME": "/home/test"}


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group assertion")
def test_timeout_terminates_and_reaps_descendant_tree(tmp_path: Path) -> None:
    marker = tmp_path / "descendant-survived"
    child = (
        "import os,signal,time; os.setsid(); signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        f"time.sleep(1.2); open({str(marker)!r}, 'w').write('alive')"
    )
    parent = f"import subprocess,time,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(5)"
    with pytest.raises(TimeoutError):
        invoke_process([sys.executable, "-c", parent], 0.05)
    time.sleep(1.3)
    assert not marker.exists()


def test_windows_timeout_uses_descendant_tree_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    class Process:
        pid = 42

        def poll(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 0

    monkeypatch.setattr(
        process_runtime.subprocess,
        "run",
        lambda command, **values: calls.append(command),
    )
    process_runtime._terminate_windows(Process())  # type: ignore[arg-type]
    assert calls == [["taskkill", "/PID", "42", "/T", "/F"]] * 3
