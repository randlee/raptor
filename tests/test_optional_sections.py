import json
import re

import pytest
from corpus_support import document, extract, qualify, replace_present
from scripts.qualify import Qualifier


def drop_success_criteria(text):
    start = text.index("### Success Criteria")
    end = text.index("\n### ", start + 1)
    return text[:start] + text[end + 1 :]


def missing(result):
    return [issue["message"] for issue in result.issues if issue["rule"] == "MISSING_FIELD"]


def test_absent_section_is_reported_without_the_setting(document):
    root, text = document
    result = qualify(root, drop_success_criteria(text))
    assert any("Success Criteria" in message for message in missing(result))


def test_optional_section_may_be_absent_and_the_record_imports(document, tmp_path):
    root, text = document
    config = root / ".raptor/raptor.toml"
    config.write_text(config.read_text() + 'optional_sections = ["Success Criteria"]\n')
    path = root / "docs/requirements/REQ-FIX-0001.md"
    path.write_text(drop_success_criteria(text))
    result = qualify(root, path.read_text())
    assert result.issues == []
    output = tmp_path / "index.json"
    extract(root, output)
    index = json.loads(output.read_text())
    assert index["diagnostics"]["issues"] == []
    assert index["metadata"]["records"] >= 1


def test_optional_section_that_is_present_must_still_have_content(document):
    root, text = document
    config = root / ".raptor/raptor.toml"
    config.write_text(config.read_text() + 'optional_sections = ["Success Criteria"]\n')
    start = text.index("### Success Criteria")
    end = text.index("\n### ", start + 1)
    emptied = text[:start] + "### Success Criteria\n\n" + text[end + 1 :]
    assert any("is empty" in message for message in missing(qualify(root, emptied)))


@pytest.mark.parametrize("value", ['["No Such Section"]', '["Dependencies"]', '"Success Criteria"'])
def test_unknown_or_malformed_optional_sections_are_refused(document, value):
    root, _ = document
    config = root / ".raptor/raptor.toml"
    config.write_text(config.read_text() + f"optional_sections = {value}\n")
    with pytest.raises(ValueError, match=re.escape("optional_sections")):
        Qualifier(root)
