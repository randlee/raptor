import json

import pytest

from corpus_support import ROOT


def test_loader_rejects_missing_or_null_optional_sections(tmp_path):
    from scripts.load_sqlite import load
    import pytest

    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    for table, key in [("requirements", "implementation_notes"), ("decisions", "alternatives")]:
        for missing in (False, True):
            payload = json.loads(json.dumps(fixture))
            if missing:
                del payload[table][0][key]
            else:
                payload[table][0][key] = None
            with pytest.raises(ValueError) as error:
                load(payload, tmp_path / "invalid.sqlite")
            assert key in str(error.value)
            assert not (tmp_path / "invalid.sqlite").exists()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_late_in_input_is_rejected_before_any_database_change(
    tmp_path, existing, conflicting
):
    import copy
    import sqlite3

    from scripts.sqlite_records import dump, load

    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    database = tmp_path / "records.sqlite"
    if existing:
        load(fixture, database)
        before_bytes, before_rows = database.read_bytes(), dump(database)
    payload = copy.deepcopy(fixture)
    payload["requirements"][0]["title"] = "Earlier row must not be written on failure"
    duplicate = copy.deepcopy(payload["requirements"][0])
    if conflicting:
        duplicate["title"] = "Conflicting duplicate must not win"
    payload["requirements"].append(duplicate)
    with pytest.raises(ValueError) as failure:
        load(payload, database)
    errors = json.loads(str(failure.value))
    duplicates = [error for error in errors if error["category"] == "DuplicateId"]
    assert len(duplicates) == 2
    assert {error["record_position"] for error in duplicates} == {0, 2}
    assert all(error["field_path"] == "/id" for error in duplicates)
    if existing:
        assert database.read_bytes() == before_bytes
        assert dump(database) == before_rows == fixture
        with sqlite3.connect(database) as connection:
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    else:
        assert not database.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_filtered_index_with_duplicate_diagnostics_is_not_silently_loaded(tmp_path, existing):
    from scripts.sqlite_records import load

    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    issue = {"rule": "DUPLICATE_ID", "id": "REQ-FIX-0001", "line": 8, "column": 4}
    fixture["diagnostics"] = {"issues": [issue]}
    database = tmp_path / "filtered.sqlite"
    if existing:
        clean = {key: value for key, value in fixture.items() if key != "diagnostics"}
        load(clean, database)
        before = database.read_bytes()
    with pytest.raises(ValueError) as failure:
        load(fixture, database)
    assert json.loads(str(failure.value)) == [issue]
    if existing:
        assert database.read_bytes() == before
    else:
        assert not database.exists()


def test_unique_input_updates_existing_rows_without_replacing_identity(tmp_path):
    import copy
    import sqlite3

    from scripts.sqlite_records import dump, load

    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    database = tmp_path / "records.sqlite"
    load(fixture, database)
    with sqlite3.connect(database) as connection:
        before = connection.execute("SELECT id, rowid FROM requirements").fetchall()
    updated = copy.deepcopy(fixture)
    updated["requirements"][0]["title"] = "Updated unique input"
    load(updated, database)
    load(updated, database)
    assert dump(database) == updated
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT id, rowid FROM requirements").fetchall() == before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
