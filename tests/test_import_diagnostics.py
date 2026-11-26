from pathlib import Path
import ast
import json

import raptor_schema
from corpus_support import ROOT, extract, project, replace_present


def test_b3_section_diagnostics(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = root / "docs/requirements/REQ-FIX-0001.md"
    for needle, replacement, rule, allowed in [
        (
            "**Acceptance Criteria:**",
            "**Acceptance:**",
            "UNKNOWN_LABEL",
            ["Acceptance Criteria", "Test Evidence"],
        ),
        ("NFR-FIX-0001 — quality prerequisite", "not-an-id", "BAD_VALUE", None),
        ("NFR-FIX-0001 — quality prerequisite", "NFR-FIX-9999", "DANGLING_REFERENCE", None),
    ]:
        original = file.read_text()
        file.write_text(replace_present(original, needle, replacement, 1))
        result = extract(root, index, check=False)
        diagnostics = json.loads(index.read_text())["diagnostics"]
        issues = diagnostics["issues"]
        issue = next(issue for issue in issues if issue["rule"] == rule)
        assert result.returncode == 1
        assert any(
            group["rule"] == rule and group["remedy"] for group in diagnostics["summary"]["groups"]
        )
        if allowed:
            assert issue["allowed"] == allowed
        file.write_text(original)


def test_b4_group_and_supersession_diagnostics(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = root / "docs/decisions/ADR-FIX-0002.md"
    for needle, replacement, rule in [
        ("### Consequences", "### Consequences\n\n#### Option A", "UNKNOWN_SECTION"),
        ("**Supersedes:** ADR-FIX-0001", "**Supersedes:** REQ-FIX-0001", "BAD_VALUE"),
    ]:
        original = file.read_text()
        file.write_text(replace_present(original, needle, replacement, 1))
        assert extract(root, index, check=False).returncode == 1
        assert any(
            issue["rule"] == rule
            for issue in json.loads(index.read_text())["diagnostics"]["issues"]
        )
        file.write_text(original)


DEFECTIVE = ROOT / "tests/fixtures/defective/atm-bd-shape.md"


def defective_project(tmp_path: Path) -> Path:
    root = project(tmp_path)
    for old in (root / "docs").rglob("*.md"):
        old.unlink()
    (root / "docs/requirements/REQ-DEF.md").write_text(DEFECTIVE.read_text())
    return root


def import_issues(root: Path, index: Path):
    result = extract(root, index, check=False)
    return result, json.loads(index.read_text())["diagnostics"]["issues"]


def apply_edits(path: Path, issues):
    issues = [i for i in issues if i["edit"]]
    """Apply each diagnostic's machine edit, last line first so positions stay valid."""
    lines = path.read_text().splitlines()
    for edit in sorted((i["edit"] for i in issues), key=lambda e: e["line"], reverse=True):
        start = edit["line"] - 1
        stop = start + 1 if edit["op"] == "replace" else start
        lines[start:stop] = edit["lines"]
    path.write_text("\n".join(lines) + "\n")


def test_empty_and_absent_sections_are_located_and_distinguished(tmp_path: Path):
    root = defective_project(tmp_path)
    result, issues = import_issues(root, tmp_path / "index.json")
    text = (root / "docs/requirements/REQ-DEF.md").read_text().splitlines()
    by = {(i["id"], i["label"]): i for i in issues}
    empty = by[("REQ-DEF-0001", "Rationale")]
    assert text[empty["line"] - 1] == "### Rationale" == empty["source"]
    assert "is empty" in empty["message"] and "write at least one sentence" in empty["fix"]
    absent = by[("REQ-DEF-0002", "Rationale")]
    assert "is missing" in absent["message"]
    assert text[absent["line"] - 1] == "### Success Criteria"
    assert "add `### Rationale` before line" in absent["fix"]
    assert absent["edit"] is None and empty["edit"] is None
    assert result.returncode == 1
    assert f"REQ-DEF.md:{empty['line']}:{empty['column']}: error[MISSING_FIELD]" in result.stderr
    assert "= help: " in result.stderr and "^" in result.stderr


def test_every_defect_is_reported_in_one_run(tmp_path: Path):
    root = defective_project(tmp_path)
    file = root / "docs/requirements/REQ-DEF.md"
    file.write_text(replace_present(file.read_text(), "### Rationale\n\nDefects are fixed one edit at a time.\n", "", 1))
    _, issues = import_issues(root, tmp_path / "index.json")
    found = {(i["id"], i["label"]) for i in issues}
    assert found >= {
        ("REQ-DEF-0001", "Rationale"),
        ("REQ-DEF-0001", "Success Criteria"),
        ("REQ-DEF-0002", "Rationale"),
        ("REQ-DEF-0003", "Rationale"),
    }
    for issue in issues:
        assert issue["file"] and issue["line"] >= 1 and issue["column"] >= 1
        assert issue["rule"] and issue["record"] and issue["label"]
        assert "source" in issue and issue["fix"] and issue["message"]


def content_keys(issues):
    return {(i["id"], i["label"]) for i in issues if i["edit"] is None}


def test_content_diagnostics_never_carry_placeholder_edits(tmp_path: Path):
    root = defective_project(tmp_path)
    _, issues = import_issues(root, tmp_path / "index.json")
    content = [i for i in issues if i["label"] in ("Rationale", "Success Criteria") and "section" in i["message"]]
    assert content and all(i["edit"] is None for i in content)
    for issue in issues:
        assert "Describe" not in json.dumps(issue["edit"])
        assert "write" in issue["fix"] or "add" in issue["fix"] or issue["edit"]


def test_applying_every_edit_leaves_content_errors_until_real_content_is_written(tmp_path: Path):
    root = defective_project(tmp_path)
    file = root / "docs/requirements/REQ-DEF.md"
    file.write_text(replace_present(file.read_text(), "**Status:** Approved  \n", ""))
    file.write_text(replace_present(file.read_text(), "### Rationale\n\nDefects are fixed one edit at a time.\n", "", 1))
    index = tmp_path / "index.json"
    _, issues = import_issues(root, index)
    assert any(i["label"] == "Status" and "missing" in i["message"] for i in issues)
    before = content_keys(issues)
    assert ("REQ-DEF-0001", "Rationale") in before
    apply_edits(file, issues)
    result, after = import_issues(root, index)
    assert result.returncode == 1
    assert content_keys(after) == before
    assert not any(i["label"] == "Status" for i in after)
    assert "Describe" not in file.read_text()


def test_writing_real_content_clears_the_content_errors(tmp_path: Path):
    root = defective_project(tmp_path)
    file = root / "docs/requirements/REQ-DEF.md"
    index = tmp_path / "index.json"
    _, issues = import_issues(root, index)
    by = {(i["id"], i["label"]): i for i in issues}
    empty = by[("REQ-DEF-0001", "Rationale")]
    lines = file.read_text().splitlines()
    lines[empty["line"]:empty["line"]] = ["", "Defects are fixed one edit at a time."]
    file.write_text("\n".join(lines) + "\n")
    _, after = import_issues(root, index)
    assert ("REQ-DEF-0001", "Rationale") not in {(i["id"], i["label"]) for i in after}
    assert ("REQ-DEF-0002", "Rationale") in {(i["id"], i["label"]) for i in after}


def test_modal_mismatch_fix_clears_the_diagnostic(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = root / "docs/requirements/REQ-FIX-0001.md"
    file.write_text(replace_present(file.read_text(), "- persist records\n", "- Records SHOULD be kept\n", 1))
    _, issues = import_issues(root, index)
    [issue] = [i for i in issues if i["rule"] == "MODAL_MISMATCH"]
    assert issue["source"] == "- Records SHOULD be kept" and "`SHOULD`" in issue["fix"]
    apply_edits(file, [issue])
    assert import_issues(root, index)[1] == []
