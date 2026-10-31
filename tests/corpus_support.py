"""Shared corpus fixtures and bounded subprocess execution for import tests."""

import subprocess
import sys
from pathlib import Path

import pytest
from scripts.extract import split
from scripts.qualify import Qualifier

ROOT = Path(__file__).parents[1]


def run(script: str, *args: str, cwd: Path = ROOT, check: bool = True):
    return subprocess.run(
        [sys.executable, ROOT / "scripts" / script, *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=check,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )


def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    config = root / ".raptor"
    config.mkdir(parents=True)
    (config / "raptor.toml").write_text('repository_id = "urn:test"\n')
    (config / "sources.toml").write_text(
        '[[sources]]\nroot = "docs"\ninclude = ["**/*.md"]\nexclude = []\n'
    )
    run("render.py", str(ROOT / "tests/fixtures/records.json"), "--output-dir", str(root / "docs"))
    return root


def extract(root: Path, output: Path, check: bool = True):
    return run("extract.py", "--project-root", str(root), "--output", str(output), check=check)


@pytest.fixture
def document(tmp_path):
    root = project(tmp_path)
    return root, (root / "docs/requirements/REQ-FIX-0001.md").read_text()


def qualify(root, text):
    qualifier = Qualifier(root)
    qualifier.qualify(split(Path("records.md"), text), text)
    return qualifier


def load_run(*args):
    return run("load_sqlite.py", *args)
