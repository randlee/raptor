"""Source duplicates cannot hide behind failed content qualification."""

import json

import pytest

from corpus_support import ROOT, project, replace_present
from scripts.import_corpus import build_index
from scripts.markdown_splitter import split


@pytest.mark.parametrize("same_file", [False, True])
@pytest.mark.parametrize("invalid_first", [False, True])
def test_duplicate_with_rejected_content_excludes_every_occurrence(
    tmp_path, same_file, invalid_first
):
    root = project(tmp_path)
    source = root / "docs/requirements/REQ-FIX-0001.md"
    original = source.read_text()
    invalid = replace_present(original, "### Rationale", "### Removed Rationale", 1)
    first, second = (invalid, original) if invalid_first else (original, invalid)
    if same_file:
        source.write_text(first + "\n" + second)
        paths = [source]
    else:
        source.write_text(first)
        other = source.with_name("copy.md")
        other.write_text(second)
        paths = [source, other]
    expected = sorted(
        (str(path.relative_to(root)), record["line"], record["column"])
        for path in paths
        for record in split(path, path.read_text())["records"]
    )
    payload = build_index(root)
    issues = payload["diagnostics"]["issues"]
    duplicates = [issue for issue in issues if issue["rule"] == "DUPLICATE_ID"]
    assert [(item["file"], item["line"], item["column"]) for item in duplicates] == expected
    assert len(duplicates) == 2
    first_location = ":".join(str(value) for value in expected[0])
    assert all(f"First occurrence: {first_location}." in issue["message"] for issue in duplicates)
    assert all(issue["value"] == "REQ-FIX-0001" and issue["remedy"] for issue in duplicates)
    assert any(
        issue["rule"] == "MISSING_FIELD" and issue["label"] == "Rationale" for issue in issues
    )
    assert any(
        issue["rule"] == "UNKNOWN_SECTION" and issue["value"] == "Removed Rationale"
        for issue in issues
    )
    assert all(row["id"] != "REQ-FIX-0001" for row in payload["requirements"])
    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    assert payload["requirements"] == [
        row for row in fixture["requirements"] if row["id"] != "REQ-FIX-0001"
    ]
    assert payload["decisions"] == fixture["decisions"]
    assert payload["diagnostics"]["summary"]["counts"]["DUPLICATE_ID"] == 2
