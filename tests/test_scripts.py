import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=True)


def test_extract_and_load_are_idempotent(tmp_path: Path) -> None:
    source = ROOT / "tests" / "fixtures"
    index, database = tmp_path / "index.json", tmp_path / "artifacts.sqlite"
    run(str(SCRIPTS / "extract.py"), str(source), "--output", str(index), cwd=ROOT)
    payload = json.loads(index.read_text())
    assert [item["id"] for item in payload["requirements"]] == ["REQ-CORE-0001", "ADR-CORE-0001"]
    assert payload["requirements"][0]["content"]["markdown"].startswith("Body mentions")
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    run(str(SCRIPTS / "load_sqlite.py"), str(index), str(database), cwd=ROOT)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM relationships").fetchone()[0] == 2


def test_render_one_record(tmp_path: Path) -> None:
    pytest = __import__("pytest")
    pytest.importorskip("jinja2")
    index = tmp_path / "index.json"
    run(str(SCRIPTS / "extract.py"), str(ROOT / "tests" / "fixtures"), "--output", str(index), cwd=ROOT)
    output = tmp_path / "rendered"
    run(str(SCRIPTS / "render.py"), str(index), "--id", "REQ-CORE-0001", "--output-dir", str(output), cwd=ROOT)
    assert output.joinpath("REQ-CORE-0001.md").read_text().startswith("## REQ-CORE-0001: First item")
