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
    excluded = documents / "excluded"
    excluded.mkdir()
    shutil.copy(ROOT / "tests" / "fixtures" / "items.md", excluded / "ignored.md")
    config = project / ".raptor"
    config.mkdir()
    (config / "raptor.toml").write_text(
        'schema_version = "1.0.0"\nrepository_id = "urn:raptor:repo:test"\n\n'
        '[files]\nscan = "sources.toml"\nrouting = "routing.toml"\nidentity = "identity.json"\n'
    )
    (config / "sources.toml").write_text(
        'schema_version = "1.0.0"\n\n[[sources]]\nname = "documentation"\nroot = "docs"\ninclude = ["*.md", "**/*.md"]\nexclude = ["excluded/**"]\n'
    )
    (config / "routing.toml").write_text(
        'schema_version = "1.0.0"\n\n[[routes]]\nsource = "documentation"\n'
        'artifact_types = ["requirement", "non_functional_requirement", "architecture_decision"]\n'
        '[routes.profile]\nprofile_id = "raptor"\nprofile_version = "1.0.0"\n'
    )
    return project


def test_extract_and_load_are_idempotent(tmp_path: Path) -> None:
    source = fixture_project(tmp_path)
    index, database = tmp_path / "index.json", tmp_path / "artifacts.sqlite"
    run(str(SCRIPTS / "extract.py"), str(source), "--output", str(index), cwd=ROOT)
    payload = json.loads(index.read_text())
    assert [item["id"] for item in payload["requirements"]] == ["REQ-COR-0001", "ADR-COR-0001"]
    assert payload["requirements"][0]["content"]["markdown"].startswith("Body mentions")
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    with sqlite3.connect(database) as connection:
        first_counts = tuple(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("artifacts", "relationships"))
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    with sqlite3.connect(database) as connection:
        second_counts = tuple(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("artifacts", "relationships"))
    assert first_counts == second_counts == (2, 2)


def test_render_one_record(tmp_path: Path) -> None:
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), str(fixture_project(tmp_path)), "--output", str(index), cwd=ROOT)
    output = tmp_path / "rendered"
    run(str(SCRIPTS / "render.py"), str(index), "--id", "REQ-COR-0001", "--output-dir", str(output), cwd=ROOT)
    rendered = output.joinpath("calibration", "REQ-COR-0001.md").read_text()
    assert rendered.startswith("# REQ-COR-0001: First item")
    assert "## Rationale" in rendered


def test_render_each_record_type(tmp_path: Path) -> None:
    source = fixture_project(tmp_path)
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), str(source), "--output", str(index), cwd=ROOT)
    payload = json.loads(index.read_text())
    payload["requirements"].extend([
        {**payload["requirements"][0], "id": "NFR-COR-0001", "type": "NFR"},
        {**payload["requirements"][0], "id": "DESIGN-COR-0001", "type": "DESIGN"},
        {**payload["requirements"][0], "id": "TEST-COR-0001", "type": "TEST"},
    ])
    index.write_text(json.dumps(payload))
    output = tmp_path / "rendered"
    run(str(SCRIPTS / "render.py"), str(index), "--output-dir", str(output), cwd=ROOT)
    assert len(list(output.rglob("*.md"))) == 5
    assert output.joinpath("calibration", "ADR-COR-0001.md").read_text().count("## Decision") == 1


def test_extract_uses_repository_configuration(tmp_path: Path) -> None:
    project = configured_fixture_project(tmp_path)
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), "--output", str(index), cwd=project)
    payload = json.loads(index.read_text())
    assert len(payload["requirements"]) == 2
    assert {item["domain"] for item in payload["requirements"]} == {"docs"}
    assert payload["metadata"]["total_files"] == 1
