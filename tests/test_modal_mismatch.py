"""MODAL_MISMATCH: a statement's own keyword disagrees with its label's modal."""

import json
import sqlite3
from pathlib import Path

import pytest
import raptor_schema
from corpus_support import document  # noqa: F401  (pytest fixture)
from corpus_support import extract, load_run, project, qualify, replace_present

FILE = "docs/requirements/REQ-FIX-0001.md"


def mismatches(issues):
    return [issue for issue in issues if issue["rule"] == "MODAL_MISMATCH"]


def position(text, needle):
    lines = text.splitlines()
    line = next(number for number, raw in enumerate(lines, 1) if needle in raw)
    return line, lines[line - 1].index(needle) + 1


def test_rendered_fixture_has_no_modal_mismatch(document):
    root, text = document
    assert mismatches(qualify(root, text).issues) == []


def test_rule_is_exported_as_non_rejecting():
    for schema in json.loads(raptor_schema.json_schema()).values():
        rule = schema["x-raptor-rules"]["MODAL_MISMATCH"]
        assert rule["rejects_record"] is False
        assert rule["categories"] == []
        assert rule["remedy"]


@pytest.mark.parametrize(
    "label,item,line,found,expected",
    [
        ("MUST statements", "persist records", "Records MUST NOT be lost", "MUST NOT", "MUST"),
        ("MUST statements", "persist records", "Records SHOULD be kept", "SHOULD", "MUST"),
        ("MUST statements", "persist records", "Records SHALL be kept", "SHALL", "MUST"),
        ("MUST statements", "persist records", "Records MAY be compacted", "MAY", "MUST"),
        ("SHOULD statements", "report status", "Status MUST be reported", "MUST", "SHOULD"),
        ("MUST NOT statements", "lose content", "Content MUST be kept", "MUST", "MUST NOT"),
    ],
)
def test_mismatch_names_file_line_label_and_keywords(document, label, item, line, found, expected):
    root, text = document
    text = replace_present(text, f"- {item}\n", f"- {line}\n", 1)
    result = qualify(root, text)
    [issue] = mismatches(result.issues)
    line_number, column = position(text, f"- {line}")
    assert (issue["line"], issue["column"]) == (line_number, column + 2 + line.index(found))
    assert issue["file"] == "records.md"
    assert issue["id"] == "REQ-FIX-0001"
    assert issue["section"] == "Requirement Statement"
    assert issue["label"] == label
    assert issue["value"] == found
    assert issue["allowed"] == [expected]
    assert repr(found) in issue["message"] and repr(expected) in issue["message"]
    # The record is kept and the label still decides the stored modal.
    [row] = result.rows["requirements"]
    [statement] = [s for s in row["requirement_statement"]["statements"] if s["text"] == line]
    [label_modal] = [
        field["modal"]
        for field in json.loads(raptor_schema.field_table("requirements"))
        if field["label"] == label
    ]
    assert statement["modal"] == label_modal


@pytest.mark.parametrize(
    "line",
    [
        "Records MUST persist",
        "records must not be lost",
        "the `MUST NOT` flag is parsed",
        "MUSTARD and MAYHEM are not keywords",
        "Records MUST be kept and MUST NOT be lost",
    ],
)
def test_matching_lowercase_quoted_or_absent_keyword_is_silent(document, line):
    root, text = document
    text = replace_present(text, "- persist records\n", f"- {line}\n", 1)
    result = qualify(root, text)
    assert mismatches(result.issues) == []
    assert len(result.rows["requirements"]) == 1


def test_keyword_on_continuation_line_points_at_that_line(document):
    root, text = document
    text = replace_present(
        text, "- persist records\n", "- persist records\n  and MAY compact them\n", 1
    )
    [issue] = mismatches(qualify(root, text).issues)
    assert (issue["line"], issue["column"]) == position(text, "MAY compact")
    assert issue["value"] == "MAY"


def test_import_reports_and_sqlite_round_trip_keeps_label_modal(tmp_path: Path):
    root, index, database = project(tmp_path), tmp_path / "index.json", tmp_path / "db.sqlite"
    file = root / FILE
    original = file.read_text()
    statement = "- lose nothing, MUST NOT drop\n"
    file.write_text(replace_present(original, "- persist records\n", statement, 1))
    result = extract(root, index, check=False)
    assert result.returncode == 1, result.stderr
    payload = json.loads(index.read_text())
    diagnostics = payload["diagnostics"]
    [issue] = mismatches(diagnostics["issues"])
    assert (issue["file"], issue["value"], issue["allowed"]) == (FILE, "MUST NOT", ["MUST"])
    assert diagnostics["summary"]["counts"] == {"MODAL_MISMATCH": 1}
    [group] = [g for g in diagnostics["summary"]["groups"] if g["rule"] == "MODAL_MISMATCH"]
    assert group["files"] == {FILE: [issue["line"]]} and group["remedy"]
    load_run(str(index), str(database))
    dumped = json.loads(load_run(str(database), "--dump").stdout)
    assert dumped["requirements"] == payload["requirements"]
    with sqlite3.connect(database) as connection:
        [stored] = connection.execute(
            "SELECT requirement_statement FROM requirements WHERE id = 'REQ-FIX-0001'"
        ).fetchone()
    [statement] = [
        s for s in json.loads(stored)["statements"] if s["text"] == "lose nothing, MUST NOT drop"
    ]
    assert statement["modal"] == "Must"


def test_binding_rejects_unknown_modal():
    with pytest.raises(raptor_schema.SchemaError) as caught:
        raptor_schema.modal_mismatch("Shall", "x")
    assert caught.value.category == "UnknownVariant"
