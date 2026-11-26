import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from corpus_support import ROOT, extract, load_run, project, run

from scripts.raptor_query import open_readonly

FIXTURE = {
    record["id"]: record
    for table in json.loads((ROOT / "tests/fixtures/records.json").read_text()).values()
    for record in table
}


@pytest.fixture(scope="module")
def database(tmp_path_factory) -> Path:
    """A database built by the importer from Markdown rendered out of the fixture."""
    work = tmp_path_factory.mktemp("query")
    index, database = work / "index.json", work / "records.sqlite"
    extract(project(work), index)
    load_run(str(index), str(database))
    return database


def query(*args: str, code: int = 0):
    result = run("raptor_query.py", *args, check=False)
    assert result.returncode == code, result.stdout + result.stderr
    assert result.stderr == ""
    return json.loads(result.stdout)


def failure(*args: str, code: int = 1):
    envelope = query(*args, code=code)
    assert envelope["success"] is False and envelope["data"] is None
    return envelope["error"]


def test_get_one_requirement_returns_the_stored_record(database):
    envelope = query("get", "REQ-FIX-0001", "--db", str(database))
    assert envelope == {
        "success": True,
        "data": [{**FIXTURE["REQ-FIX-0001"], "type": "req"}],
        "error": None,
    }


def test_get_returns_typed_statements_and_criteria(database):
    [record] = query("get", "REQ-FIX-0001", "--db", str(database))["data"]
    assert record["requirement_statement"]["statements"] == [
        {"modal": "Must", "text": "persist records"},
        {"modal": "Should", "text": "report status"},
        {"modal": "MustNot", "text": "lose content"},
    ]
    assert record["success_criteria"]["acceptance_criteria"] == [
        {"text": "stored", "checked": True},
        {"text": "retrieved", "checked": False},
        {"text": "reviewed", "checked": None},
    ]


def test_get_many_keeps_argument_order_across_tables(database):
    ids = ["ADR-FIX-0002", "REQ-FIX-0001", "NFR-FIX-0001", "ADR-FIX-0001"]
    data = query("get", *ids, "--db", str(database))["data"]
    assert [record["id"] for record in data] == ids
    assert [record["type"] for record in data] == ["adr", "req", "nfr", "adr"]
    for record in data:
        assert {key: value for key, value in record.items() if key != "type"} == FIXTURE[
            record["id"]
        ]


def test_get_returns_decision_sections_as_objects(database):
    [record] = query("get", "ADR-FIX-0001", "--db", str(database))["data"]
    for section in ("context", "decision", "rationale", "consequences", "alternatives"):
        assert isinstance(record[section], dict), section
    assert record["alternatives"] == FIXTURE["ADR-FIX-0001"]["alternatives"]
    assert record["superseded_by"] == FIXTURE["ADR-FIX-0001"]["superseded_by"]


def test_get_nfr_comes_from_the_requirements_table(database):
    [record] = query("get", "NFR-FIX-0001", "--db", str(database))["data"]
    assert record["type"] == "nfr"
    assert record["requirement_statement"] == FIXTURE["NFR-FIX-0001"]["requirement_statement"]


def test_get_unknown_ids_are_named_and_nothing_is_returned(database):
    error = failure("get", "REQ-FIX-0009", "NFR-FIX-0001", "ADR-ZZ-0003", "--db", str(database))
    assert error == {
        "code": "UNKNOWN_ID",
        "message": "no record with id: REQ-FIX-0009, ADR-ZZ-0003",
    }


def test_get_malformed_id_is_a_typed_error(database):
    error = failure("get", "REQ-0001", "--db", str(database))
    assert error["code"] == "INVALID_ID"
    assert "'REQ-0001'" in error["message"]


@pytest.mark.parametrize(
    ("filters", "expected"),
    [
        ((), ["ADR-FIX-0001", "ADR-FIX-0002", "NFR-FIX-0001", "REQ-FIX-0001"]),
        (("--type", "req"), ["REQ-FIX-0001"]),
        (("--type", "nfr"), ["NFR-FIX-0001"]),
        (("--type", "adr"), ["ADR-FIX-0001", "ADR-FIX-0002"]),
        (("--status", "Superseded"), ["ADR-FIX-0001"]),
        (("--status", "Draft"), ["NFR-FIX-0001"]),
        (("--type", "req", "--status", "Draft"), []),
        (("--type", "adr", "--status", "Approved"), ["ADR-FIX-0002"]),
    ],
)
def test_list_filters(database, filters, expected):
    data = query("list", "--db", str(database), *filters)["data"]
    assert [row["id"] for row in data] == expected
    for row in data:
        source = FIXTURE[row["id"]]
        assert row == {
            "id": source["id"],
            "type": source["id"].split("-")[0].lower(),
            "title": source["title"],
            "status": source["status"],
        }


@pytest.mark.parametrize(
    ("args", "named"),
    [
        (("list", "--type", "spec", "--db", "{db}"), "req"),
        (("list", "--status", "Done", "--db", "{db}"), "Approved"),
        (("get", "--db", "{db}"), "RECORD_ID"),
        (("list",), "--db"),
        ((), "get"),
    ],
)
def test_usage_errors_are_typed(database, args, named):
    error = failure(*(arg.format(db=database) for arg in args), code=2)
    assert error["code"] == "USAGE"
    assert named in error["message"]


def test_missing_and_foreign_files_are_typed_errors(tmp_path: Path):
    error = failure("list", "--db", str(tmp_path / "absent.sqlite"))
    assert error["code"] == "DB_NOT_FOUND"
    foreign = tmp_path / "foreign.sqlite"
    with sqlite3.connect(foreign) as connection:
        connection.execute("CREATE TABLE other (id TEXT)")
    for args in (("list",), ("get", "REQ-FIX-0001")):
        error = failure(*args, "--db", str(foreign))
        assert error["code"] == "DB_NOT_RAPTOR"
        assert "load_sqlite.py" in error["message"]
    text = tmp_path / "text.sqlite"
    text.write_text("not a database\n" * 100)
    assert failure("list", "--db", str(text))["code"] == "DB_NOT_RAPTOR"


def test_connection_is_read_only(database):
    connection = open_readonly(database)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("DELETE FROM requirements")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("CREATE TABLE scratch (id TEXT)")
    finally:
        connection.close()
    assert len(query("list", "--db", str(database))["data"]) == len(FIXTURE)


def test_queries_leave_the_database_file_unchanged(database):
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    query("list", "--db", str(database))
    query("get", *FIXTURE, "--db", str(database))
    failure("get", "REQ-FIX-0009", "--db", str(database))
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_help_documents_the_contract():
    result = run("raptor_query.py", "--help")
    for code in ("UNKNOWN_ID", "INVALID_ID", "DB_NOT_FOUND", "DB_NOT_RAPTOR", "USAGE"):
        assert code in result.stdout
    assert '"success": true' in result.stdout
