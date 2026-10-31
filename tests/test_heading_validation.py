"""The splitter recognizes structure; Rust owns the record ID policy."""

import pytest

from corpus_support import document, qualify


@pytest.mark.parametrize("invalid", ["REQ-FIX-12", "REQ-project-0001", "OTHER-FIX-0001"])
def test_invalid_heading_id_is_a_bad_value(document, invalid):
    root, text = document
    text = text.replace("## REQ-FIX-0001:", f"## {invalid}:")
    result = qualify(root, text)
    assert any(issue["rule"] == "BAD_VALUE" for issue in result.issues)
    assert not any(issue["rule"] == "MISSING_ID" for issue in result.issues)
    assert not result.rows["requirements"]
