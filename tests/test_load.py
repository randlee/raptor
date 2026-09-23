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
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM edges").fetchone()[0] == 3
