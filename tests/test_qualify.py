import json
from pathlib import Path

import pytest
import raptor_schema
from scripts.extract import split
from scripts.qualify import Qualifier
from test_extract import ROOT, project


@pytest.fixture
def document(tmp_path):
    root = project(tmp_path)
    return root, (root / "docs/requirements/REQ-FIX-0001.md").read_text()


def qualify(root, text):
    qualifier = Qualifier(root)
    qualifier.qualify(split(Path("records.md"), text), text)
    return qualifier


def test_normalization_of_labels_sections_status_and_modal(document):
    root, text = document
    for old, new in [("Acceptance Criteria", " aCcEpTaNcE   CrItErIa : "),
                     ("### Requirement Statement", "### rEqUiReMeNt  StAtEmEnT :  "),
                     ("Active", "aCtIvE  :  "), ("MUST NOT statements", "mUsT   nOt  StAtEmEnTs : ")]:
        text = text.replace(old, new)
    result = qualify(root, text)
    expected = json.loads((ROOT / "tests/fixtures/records.json").read_text())["requirements"][0]
    assert result.issues == []
    assert result.rows["requirements"] == [expected]


def test_misspelling_keeps_verbatim_value_column_and_allowed(document):
    root, text = document
    text = text.replace("**Status:** Active", "**Status:** Status")
    result = qualify(root, text)
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert issue["value"] == "Status  "
    line = text.splitlines()[issue["line"] - 1]
    assert issue["column"] == line.rfind("Status") + 1
    assert "Active" in issue["allowed"]
    assert all(key in issue for key in ["file", "line", "column", "rule", "id", "label",
                                       "value", "allowed", "message", "remedy"])
    assert result.rows["requirements"] == []


def test_declared_aliases_apply_after_normalization_and_are_counted(document):
    root, text = document
    (root / ".raptor/aliases.toml").write_text(
        '[labels]\nAcceptance = "Acceptance Criteria"\n[sections]\nStatement = "Requirement Statement"\n'
        '[values]\nReady = "Active"\nSHALL = "Must"\n')
    text = text.replace("Acceptance Criteria", " aCcEpTaNcE : ").replace("### Requirement Statement", "### Statement")
    text = text.replace("Active", "Ready").replace("MUST statements", "SHALL statements")
    result = qualify(root, text)
    assert result.issues == []
    assert result.counts == {"labels": {"Acceptance -> Acceptance Criteria": 1},
                            "sections": {"Statement -> Requirement Statement": 1},
                            "values": {"Ready -> Active": 1, "SHALL -> Must": 1}}


@pytest.mark.parametrize("config,line", [('[labels]\n\nAcceptance = "No Such Label"\n', 3),
    ('[labels]\nShared = "Acceptance Criteria"\n[sections]\nShared = "No Such Section"\n', 4)])
def test_unknown_alias_target_is_refused_before_markdown_is_read(document, monkeypatch, config, line):
    root, _ = document
    alias = root / ".raptor/aliases.toml"
    alias.write_text(config)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert path.suffix != ".md", "invalid configuration must precede Markdown reads"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    with pytest.raises(ValueError, match=rf"aliases.toml:{line}: unknown alias target"):
        Qualifier(root)


@pytest.mark.parametrize("old,new", [("[guide](https://example.test/guide)", "[guide](broken"),
                                     ("NFR-FIX-0001 — quality prerequisite", "not-an-id")])
def test_malformed_links_and_id_items_reject_the_record(document, old, new):
    root, text = document
    result = qualify(root, text.replace(old, new))
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert new in issue["value"]
    assert text.replace(old, new).splitlines()[issue["line"] - 1][issue["column"] - 1:].startswith(new)
    assert not result.rows["requirements"]


def test_statement_order_follows_source_labels(document):
    root, text = document
    text = text.replace("MUST statements", "TEMP").replace("SHOULD statements", "MUST statements")
    result = qualify(root, text.replace("TEMP", "SHOULD statements"))
    statements = result.rows["requirements"][0]["requirement_statement"]["statements"]
    assert [item["modal"] for item in statements] == ["Should", "Must", "MustNot"]
    assert [item["text"] for item in statements] == ["persist records", "report status", "lose content"]


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
    result = qualify(root, text.replace("A durable record is necessary.", ""))
    assert any(issue["rule"] == "MISSING_FIELD" and issue["label"] == "Rationale" for issue in result.issues)
    assert not result.rows["requirements"]


@pytest.mark.parametrize("old,new,rule", [("**Status:**", "**Unknown Label:**", "UNKNOWN_LABEL"),
    ("### Rationale", "### Unknown Section  ", "UNKNOWN_SECTION")])
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
        assert line[issue["column"] - 1:].startswith(issue["value"])
        assert "Found" in issue["message"] and "expected" in issue["message"]
        assert "scalar format" not in issue["message"]
