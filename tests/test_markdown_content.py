"""Round-trip and source-boundary checks for Markdown content reconstruction."""
import json

import pytest

from test_extract import ROOT, project, run
from test_qualify import document, qualify


@pytest.mark.parametrize("table,path,value", [
    ("requirements", ("rationale",), "before\n- middle\nafter"),
    ("requirements", ("rationale",), "first paragraph\n\nsecond paragraph"),
    ("decisions", ("context", "background"), "before\n- middle\nafter"),
    ("decisions", ("implementation", "code_examples"), "```text\n- literal\n```"),
    ("decisions", ("implementation", "code_examples"),
     "```markdown\n# literal heading\n\n**Status:** literal label\n---\n```"),
    ("requirements", ("requirement_statement", "statements", 0, "text"), "parent\n  - nested child"),
    ("requirements", ("success_criteria", "acceptance_criteria", 0, "text"), "checked\n  continuation"),
    ("requirements", ("dependencies", "requires", 0, "note"), "quality prerequisite\n  continuation"),
    ("requirements", ("related_documents", "design_documents", 0, "note"), "guide note\n  continuation"),
])
def test_round_trip_preserves_multiline_content(tmp_path, table, path, value):
    fixture = json.loads((ROOT / "tests/fixtures/records.json").read_text())
    record = fixture[table][0]
    target = record
    for member in path[:-1]:
        target = target[member]
    target[path[-1]] = value
    source = tmp_path / "records.json"
    source.write_text(json.dumps(fixture))
    root = project(tmp_path)
    run("render.py", str(source), "--output-dir", str(root / "docs"))
    text = (root / "docs" / table / f"{record['id']}.md").read_text()
    result = qualify(root, text)
    assert result.issues == []
    assert result.rows[table] == [record]


@pytest.mark.parametrize("needle", ["persist records", "NFR-FIX-0001 — quality prerequisite",
                                    "[guide](https://example.test/guide)"])
def test_detached_prose_is_not_absorbed_into_a_list_item(document, needle):
    root, text = document
    changed = text.replace(needle, needle + "\n\nUnrelated prose.", 1)
    result = qualify(root, changed)
    issue = next(issue for issue in result.issues if issue["rule"] == "BAD_VALUE")
    assert issue["value"] == "Unrelated prose."
    assert issue["line"] == changed.splitlines().index("Unrelated prose.") + 1
    assert not result.rows["requirements"]
