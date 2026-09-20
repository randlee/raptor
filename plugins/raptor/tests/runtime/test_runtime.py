from __future__ import annotations

import sys
import shutil
from subprocess import CompletedProcess
from pathlib import Path

import pytest

from runtime.bootstrap import BootstrapError, bootstrap
from runtime.client_adapters.claude import ClaudeBackend
from runtime.client_adapters.codex import CodexBackend
from runtime.client_adapters.environment import allowed_environment

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
    calls: list[tuple[list[str], int, dict[str, str]]] = []

    def invoke(command: list[str], **values: object) -> CompletedProcess[str]:
        calls.append((command, int(values["timeout"]), values["env"]))  # type: ignore[arg-type]
        return CompletedProcess(command, 0, "response", "")

    monkeypatch.setattr("subprocess.run", invoke)
    result = backend.invoke(
        agent_path=tmp_path / "agent.md", prompt="prompt", timeout_s=9
    )  # type: ignore[attr-defined]
    assert result == "response" and calls[0][1] == 9
    assert calls[0][2] == allowed_environment()


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
