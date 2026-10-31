import raptor_schema
import json

import pytest
from corpus_support import document, qualify
from corpus_support import ROOT


def test_misspelling_keeps_verbatim_value_column_and_allowed(document):
    root, text = document
    text = text.replace("**Status:** Active", "**Status:** Status")
    result = qualify(root, text)
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert issue["value"] == "Status  "
    line = text.splitlines()[issue["line"] - 1]
    assert issue["column"] == line.rfind("Status") + 1
    assert "Active" in issue["allowed"]
    assert all(
        key in issue
        for key in [
            "file",
            "line",
            "column",
            "rule",
            "id",
            "label",
            "value",
            "allowed",
            "message",
            "remedy",
        ]
    )
    assert result.rows["requirements"] == []


def test_section_level_nested_label_is_diagnostic(document):
    root, _ = document
    text = (
        (root / "docs/decisions/ADR-FIX-0001.md")
        .read_text()
        .replace(
            "### Alternatives Considered", "### Alternatives Considered\n**Description:** stray", 1
        )
    )
    result = qualify(root, text)
    issues = [i for i in result.issues if i["rule"] == "UNKNOWN_LABEL"]
    assert (
        len(issues) == 1
        and (issues[0]["line"], issues[0]["column"], issues[0]["allowed"])
        == (text.splitlines().index("**Description:** stray") + 1, 3, [])
        and "Alternatives Considered" in issues[0]["message"]
    )
    assert len(result.rows["decisions"]) == 1


@pytest.mark.parametrize(
    "old,new,rule",
    [
        ("**Status:**", "**Unknown Label:**", "UNKNOWN_LABEL"),
        ("### Rationale", "### Unknown Section  ", "UNKNOWN_SECTION"),
    ],
)
def test_unknown_names_preserve_source_token_and_column(document, old, new, rule):
    root, text = document
    result = qualify(root, text.replace(old, new))
    issue = next(issue for issue in result.issues if issue["rule"] == rule)
    expected = "Unknown Label" if rule == "UNKNOWN_LABEL" else "Unknown Section  "
    assert issue["value"] == expected
    assert issue["column"] == new.index(expected) + 1
    assert issue["allowed"]


def test_inventory_maps_every_occurrence_to_its_token(document):
    root, text = document
    text = text + text
    result = qualify(root, text)
    accepted = json.loads(raptor_schema.accept(json.dumps(result.rows)))
    for error in accepted["errors"]:
        result.map_error(error)
    duplicates = [issue for issue in result.issues if issue["rule"] == "DUPLICATE_ID"]
    assert len(duplicates) == 2
    assert len({issue["line"] for issue in duplicates}) == 2
    dangling = [issue for issue in result.issues if issue["rule"] == "DANGLING_REFERENCE"]
    assert dangling
    for issue in duplicates + dangling:
        line = text.splitlines()[issue["line"] - 1]
        assert line[issue["column"] - 1 :].startswith(issue["value"])
        assert "Found" in issue["message"] and "expected" in issue["message"]
        assert "scalar format" not in issue["message"]
