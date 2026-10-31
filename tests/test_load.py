import json
import subprocess
import sys
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parents[1]


def run(*args: str):
    return subprocess.run([sys.executable, ROOT / "scripts/load_sqlite.py", *args], text=True, capture_output=True, check=True)


def test_load_and_dump_are_idempotent(tmp_path: Path):
    index, database = ROOT / "tests/fixtures/records.json", tmp_path / "records.sqlite"
    run(str(index), str(database))
    first = run(str(database), "--dump")
    run(str(index), str(database))
    second = run(str(database), "--dump")
    assert json.loads(first.stdout) == json.loads(second.stdout) == json.loads(index.read_text())


def test_dump_keeps_text_that_looks_like_json(tmp_path: Path):
    index, database = ROOT / "tests/fixtures/records.json", tmp_path / "records.sqlite"
    payload = json.loads(index.read_text())
    payload["requirements"][0]["rationale"] = "[literal text]"
    source = tmp_path / "index.json"
    source.write_text(json.dumps(payload))
    run(str(source), str(database))
    assert json.loads(run(str(database), "--dump").stdout)["requirements"][0]["rationale"] == "[literal text]"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM edges").fetchone()[0] == 3


def test_missing_or_null_optional_sections_load_as_canonical_empty(tmp_path):
    payload = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    payload["requirements"][0]["implementation_notes"] = None
    del payload["decisions"][1]["alternatives"]
    source, database = tmp_path / "empty.json", tmp_path / "empty.sqlite"
    source.write_text(json.dumps(payload))
    run(str(source), str(database))
    dumped = json.loads(run(str(database), "--dump").stdout)
    assert dumped["requirements"][0]["implementation_notes"] == {"text": "", "key_considerations": []}
    assert dumped["decisions"][1]["alternatives"] == {"text": "", "groups": []}
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT supersedes IS NULL FROM requirements LIMIT 1").fetchone()[0]
