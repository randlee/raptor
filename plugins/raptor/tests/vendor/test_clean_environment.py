from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.fixture(scope="module")
def clean_install(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("clean-plugin")
    plugin, dependencies = root / "raptor", root / "dependencies"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--quiet",
            "--target",
            str(dependencies),
            "pydantic>=2.10,<3",
        ],
        check=True,
        env={"PATH": os.environ["PATH"]},
    )
    return plugin, dependencies


def probe(
    plugin: Path,
    dependencies: Path | None,
    expression: str,
    ambient: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    paths = (
        ([] if ambient is None else [str(ambient)])
        + [str(plugin)]
        + ([] if dependencies is None else [str(dependencies)])
    )
    source = (
        "import sys; from pathlib import Path; "
        f"sys.path[:0] = {paths!r}; from runtime.bootstrap import bootstrap; "
        f"module = bootstrap(Path({str(plugin)!r})); {expression}"
    )
    return subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", source],
        capture_output=True,
        text=True,
        env={"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1"},
    )


def test_clean_declared_dependencies_load_vendor(
    clean_install: tuple[Path, Path],
) -> None:
    plugin, dependencies = clean_install
    result = probe(plugin, dependencies, "print(module.__file__)")
    assert result.returncode == 0, result.stderr
    assert str(plugin / "_vendor/raptor_schema") in result.stdout


def test_clean_environment_reports_missing_dependency(
    clean_install: tuple[Path, Path],
) -> None:
    plugin, _ = clean_install
    result = probe(plugin, None, "print(module.__file__)")
    assert result.returncode != 0 and "RAPTOR.BOOTSTRAP.DEPENDENCY" in result.stderr


def test_clean_environment_rejects_tampered_vendor(
    clean_install: tuple[Path, Path], tmp_path: Path
) -> None:
    _, dependencies = clean_install
    plugin = tmp_path / "raptor"
    shutil.copytree(
        ROOT, plugin, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc")
    )
    (plugin / "_vendor/raptor_schema/canonical.py").write_text(
        "tampered", encoding="utf-8"
    )
    result = probe(plugin, dependencies, "print(module.__file__)")
    assert result.returncode != 0 and "RAPTOR.BOOTSTRAP.VENDOR_HASH" in result.stderr


def test_clean_environment_vendor_beats_ambient_package(
    clean_install: tuple[Path, Path], tmp_path: Path
) -> None:
    plugin, dependencies = clean_install
    ambient = tmp_path / "ambient"
    (ambient / "raptor_schema").mkdir(parents=True)
    (ambient / "raptor_schema/__init__.py").write_text(
        "AMBIENT = True\n", encoding="utf-8"
    )
    result = probe(plugin, dependencies, "print(module.__file__)", ambient)
    assert result.returncode == 0, result.stderr
    assert str(plugin / "_vendor/raptor_schema") in result.stdout
