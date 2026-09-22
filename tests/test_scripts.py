import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=True)



def fixture_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / "scripts").mkdir(parents=True)
    documents = project / "calibration" / "requirements"
    documents.mkdir(parents=True)
    shutil.copy(ROOT / "tests" / "fixtures" / "items.md", documents / "items.md")
    return project


def configured_fixture_project(tmp_path: Path) -> Path:
    project = fixture_project(tmp_path)
    documents = project / "docs"
    shutil.copytree(project / "calibration" / "requirements", documents)
    config = project / ".raptor"
    config.mkdir()
    (config / "raptor.toml").write_text('[files]\nsources = "sources.toml"\nrouting = "routing.toml"\n')
    (config / "sources.toml").write_text(
        '[[sources]]\nname = "documentation"\nroot = "docs"\ninclude = ["*.md", "**/*.md"]\nexclude = []\n'
    )
    (config / "routing.toml").write_text(
        '[[routes]]\nsource = "documentation"\nartifact_types = ["REQ", "NFR", "ADR"]\n'
    )
    return project


def test_extract_and_load_are_idempotent(tmp_path: Path) -> None:
    source = fixture_project(tmp_path)
    index, database = tmp_path / "index.json", tmp_path / "artifacts.sqlite"
    run(str(SCRIPTS / "extract.py"), str(source), "--output", str(index), cwd=ROOT)
    payload = json.loads(index.read_text())
    assert [item["id"] for item in payload["requirements"]] == ["REQ-CORE-0001", "ADR-CORE-0001"]
    assert payload["requirements"][0]["content"]["markdown"].startswith("Body mentions")
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM relationships").fetchone()[0] == 0


def test_render_one_record(tmp_path: Path) -> None:
    pytest = __import__("pytest")
    pytest.importorskip("jinja2")
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), str(fixture_project(tmp_path)), "--output", str(index), cwd=ROOT)
    output = tmp_path / "rendered"
    run(str(SCRIPTS / "render.py"), str(index), "--id", "REQ-CORE-0001", "--output-dir", str(output), cwd=ROOT)
    assert output.joinpath("REQ-CORE-0001.md").read_text().startswith("## REQ-CORE-0001: First item")


def test_extract_uses_repository_configuration(tmp_path: Path) -> None:
    project = configured_fixture_project(tmp_path)
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), "--output", str(index), cwd=project)
    payload = json.loads(index.read_text())
    assert len(payload["requirements"]) == 2
    assert {item["domain"] for item in payload["requirements"]} == {"documentation"}
