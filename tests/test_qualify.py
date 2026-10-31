import json

import pytest
from corpus_support import ROOT, document, qualify, replace_present


def test_normalization_of_labels_sections_status_and_modal(document):
    root, text = document
    for old, new in [
        ("Acceptance Criteria", " aCcEpTaNcE   CrItErIa : "),
        ("### Requirement Statement", "### rEqUiReMeNt  StAtEmEnT :  "),
        ("Active", "aCtIvE  :  "),
        ("MUST NOT statements", "mUsT   nOt  StAtEmEnTs : "),
    ]:
        text = replace_present(text, old, new)
    result = qualify(root, text)
    expected = json.loads((ROOT / "tests/fixtures/records.json").read_text())["requirements"][0]
    assert result.issues == []
    assert result.rows["requirements"] == [expected]


@pytest.mark.parametrize(
    "old,new",
    [
        ("[guide](https://example.test/guide)", "[guide](broken"),
        ("NFR-FIX-0001 — quality prerequisite", "not-an-id"),
    ],
)
def test_malformed_links_and_id_items_reject_the_record(document, old, new):
    root, text = document
    result = qualify(root, replace_present(text, old, new))
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert new in issue["value"]
    assert (
        replace_present(text, old, new)
        .splitlines()[issue["line"] - 1][issue["column"] - 1 :]
        .startswith(new)
    )
    assert not result.rows["requirements"]


def test_statement_order_follows_source_labels(document):
    root, text = document
    text = replace_present(
        replace_present(text, "MUST statements", "TEMP"), "SHOULD statements", "MUST statements"
    )
    result = qualify(root, replace_present(text, "TEMP", "SHOULD statements"))
    statements = result.rows["requirements"][0]["requirement_statement"]["statements"]
    assert [item["modal"] for item in statements] == ["Should", "Must", "MustNot"]
    assert [item["text"] for item in statements] == [
        "persist records",
        "report status",
        "lose content",
    ]


def test_new_document_header_carries_to_its_later_records(document):
    root, text = document
    first = (root / "docs/decisions/ADR-FIX-0001.md").read_text()
    second = (root / "docs/decisions/ADR-FIX-0002.md").read_text().split("## ADR-FIX-0002:", 1)[1]
    result = qualify(root, text + first + "## ADR-FIX-0002:" + second)
    assert result.issues == []
    assert len(result.rows["decisions"]) == 2
    assert all(row["decision_date"] == "2026-01-05" for row in result.rows["decisions"])


def test_empty_required_content_is_missing(document):
    root, text = document
    result = qualify(root, replace_present(text, "A durable record is necessary.", ""))
    assert any(
        issue["rule"] == "MISSING_FIELD" and issue["label"] == "Rationale"
        for issue in result.issues
    )
    assert not result.rows["requirements"]
