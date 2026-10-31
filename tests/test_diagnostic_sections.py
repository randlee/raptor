import json
from pathlib import Path

import raptor_schema

from scripts.extract import split
from scripts.qualify import Qualifier
from test_extract import extract, project


def test_groups_same_label_by_canonical_section_and_preserves_root(tmp_path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = root / "docs/requirements/REQ-FIX-0001.md"
    text = file.read_text().replace("### Requirement Statement", "### rEqUiReMeNt StAtEmEnT")
    text = text.replace("### rEqUiReMeNt StAtEmEnT", "### rEqUiReMeNt StAtEmEnT\n**Typo:** first")
    text = text.replace("### Success Criteria", "### Success Criteria\n**Typo:** second")
    text = text.replace("**Status:** Active", "**Status:** Active\n**Typo:** header")
    file.write_text(text)
    assert extract(root, index, check=False).returncode == 1
    diagnostics = json.loads(index.read_text())["diagnostics"]
    issues = [i for i in diagnostics["issues"] if i["rule"] == "UNKNOWN_LABEL" and i["value"] == "Typo"]
    assert {i["section"] for i in issues} == {None, "Requirement Statement", "Success Criteria"}
    groups = [g for g in diagnostics["summary"]["groups"] if g["rule"] == "UNKNOWN_LABEL" and g["label"] == "Typo"]
    assert {g["section"] for g in groups} == {None, "Requirement Statement", "Success Criteria"}
    assert all(g["count"] == 1 for g in groups)
    assert all(text.splitlines()[i["line"] - 1][i["column"] - 1:].startswith("Typo") for i in issues)


def test_mapped_inventory_and_typed_errors_use_schema_sections(tmp_path):
    root = project(tmp_path)
    text = (root / "docs/requirements/REQ-FIX-0001.md").read_text()
    text = text.replace("NFR-FIX-0001 — quality prerequisite", "NFR-FIX-9999")
    qualifier = Qualifier(root)
    qualifier.qualify(split(Path("record.md"), text), text)
    accepted = json.loads(raptor_schema.accept(json.dumps(qualifier.rows)))
    for error in accepted["errors"]:
        qualifier.map_error(error)
    issue = next(i for i in qualifier.issues if i["rule"] == "DANGLING_REFERENCE")
    assert issue["section"] == "Dependencies"
    assert text.splitlines()[issue["line"] - 1][issue["column"] - 1:].startswith("NFR-FIX-9999")
    error = next(e for e in accepted["errors"] if e["category"] == "DanglingReference")
    qualifier.map_error({**error, "category": "TypeMismatch", "field_path": "/success_criteria/acceptance_criteria/0/text"})
    assert qualifier.issues[-1]["section"] == "Success Criteria"
    qualifier.map_error({**error, "category": "TypeMismatch", "field_path": "/status", "item_index": None})
    assert qualifier.issues[-1]["section"] is None


def test_missing_required_section_and_unknown_section_context(tmp_path):
    root = project(tmp_path)
    text = (root / "docs/requirements/REQ-FIX-0001.md").read_text()
    text = text.replace("### Rationale", "### Unknown Section")
    qualifier = Qualifier(root)
    qualifier.qualify(split(Path("record.md"), text), text)
    assert next(i for i in qualifier.issues if i["rule"] == "UNKNOWN_SECTION")["section"] is None
    assert next(i for i in qualifier.issues if i["rule"] == "MISSING_FIELD" and i["label"] == "Rationale")["section"] == "Rationale"
