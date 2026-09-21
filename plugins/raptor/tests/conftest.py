from __future__ import annotations

import os
import shlex
import stat
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture(autouse=True)
def sc_compose_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Expose the binding-backed test CLI before machine-local installations."""
    bin_path = tmp_path / "fixture-bin"
    bin_path.mkdir()
    executable = bin_path / "sc-compose"
    adapter = PLUGIN_ROOT / "tests/support/sc_compose_cli.py"
    executable.write_text(
        "#!/bin/sh\nexec "
        + shlex.quote(sys.executable)
        + " "
        + shlex.quote(str(adapter))
        + ' "$@"\n',
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{bin_path}{os.pathsep}{os.environ.get('PATH', '')}")
    return executable
