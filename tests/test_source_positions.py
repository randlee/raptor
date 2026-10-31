"""Diagnostic anchors come from structural parsing, including repeated tokens."""

import pytest

from corpus_support import document, qualify, replace_present
from scripts.extract import split
from scripts.record_context import RecordContext
from scripts.qualify import Qualifier


def test_splitter_preserves_distinct_heading_label_and_value_columns(document):
    root, text = document
    text = replace_present(text, "**Status:** Active", "**Status:** Status")
    tree = split(root / "positions.md", text)
    record = tree["records"][0]
    heading = text.splitlines()[record["line"] - 1]
    assert heading[record["column"] - 1 :].startswith(record["token"])
    assert heading[record["caption_column"] - 1 :] == record["caption"]
    node = record["fields"]["Status"]
    line = text.splitlines()[node["line"] - 1]
    assert node["token_column"] == line.index("Status") + 1
    assert node["column"] == line.rindex("Status") + 1


@pytest.mark.parametrize("position", [{"line": 1}, {"line": 1, "column": 0}])
def test_invalid_or_missing_diagnostic_anchor_fails_loudly(position):
    context = RecordContext(None, "broken.md", ["source"], {})
    with pytest.raises((KeyError, ValueError)):
        context.issue("BAD_VALUE", position, "absent")


def test_empty_document_has_explicit_document_anchor(document):
    root, _ = document
    result = qualify(root, "")
    assert len(result.issues) == 1
    assert result.issues[0]["rule"] == "MISSING_ID"
    assert (result.issues[0]["line"], result.issues[0]["column"]) == (1, 1)


def test_unknown_token_missing_from_source_is_not_given_a_fabricated_column(document):
    root, _ = document
    context = RecordContext(Qualifier(root), "broken.md", ["**Actual:** value"], {})
    node = {"line": 1, "column": 13, "token_column": 3}
    with pytest.raises(ValueError, match="absent at its source position"):
        context.match("labels", "Missing", [], node, "UNKNOWN_LABEL")
