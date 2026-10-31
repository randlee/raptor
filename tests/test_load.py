import json
import sqlite3
from pathlib import Path

from corpus_support import ROOT, load_run as run


def test_load_and_dump_are_idempotent(tmp_path: Path):
    index, database = ROOT / "tests/fixtures/records.json", tmp_path / "records.sqlite"
    run(str(index), str(database))
    first = run(str(database), "--dump")
    run(str(index), str(database))
    second = run(str(database), "--dump")
    assert json.loads(first.stdout) == json.loads(second.stdout) == json.loads(index.read_text())
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_dump_keeps_text_that_looks_like_json(tmp_path: Path):
    index, database = ROOT / "tests/fixtures/records.json", tmp_path / "records.sqlite"
    payload = json.loads(index.read_text())
    payload["requirements"][0]["rationale"] = "[literal text]"
    source = tmp_path / "index.json"
    source.write_text(json.dumps(payload))
    run(str(source), str(database))
    assert (
        json.loads(run(str(database), "--dump").stdout)["requirements"][0]["rationale"]
        == "[literal text]"
    )
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM edges").fetchone()[0] == 3
