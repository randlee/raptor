from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_empty_pythonpath_bootstraps_only_vendor(tmp_path: Path) -> None:
    script = tmp_path / "probe.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from runtime.bootstrap import bootstrap\n"
        f"module = bootstrap(__import__('pathlib').Path({str(ROOT)!r}))\n"
        "print(module.__file__)\n"
    )
    environment = {"PATH": os.environ["PATH"], "PYTHONPATH": ""}
    result = subprocess.run(
        [sys.executable, str(script)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert str(ROOT / "_vendor/raptor_schema") in result.stdout
