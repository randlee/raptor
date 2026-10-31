import json
from pathlib import Path

from scripts.extract import split
from corpus_support import ROOT, extract, project


def test_round_trip_and_project_root(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    result = extract(root, index)
    payload, fixture = json.loads(index.read_text()), json.loads(
        (ROOT / "tests/fixtures/records.json").read_text()
    )
    for table in ("requirements", "decisions"):
        assert sorted(payload[table], key=lambda item: item["id"]) == sorted(
            fixture[table], key=lambda item: item["id"]
        )
    assert payload["diagnostics"]["issues"] == []
    assert json.loads(result.stdout)["records"] == 4
    second = tmp_path / "second.json"
    extract(root, second)
    assert json.loads(second.read_text())["requirements"] == payload["requirements"]


def test_binder_diagnostics_and_row_effects(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = next((root / "docs/requirements").glob("REQ*.md"))
    for part, needle, replacement, rule, records in [
        (0, "**Version:** 1.0.0", "", "MISSING_FIELD", 3),
        (0, "**Created:** 2026-01-01", "**Created:** 2026-02-30", "BAD_VALUE", 3),
        (1, "**Status:** Active", "**Status:** Whenever", "BAD_VALUE", 3),
        (1, "**Status:** Active", "**Status:** Active\n**Priority:** High", "UNKNOWN_LABEL", 4),
        (1, "**Status:** Active", "**Status:** Active\n### Notes", "UNKNOWN_SECTION", 4),
    ]:
        original = file.read_text()
        pieces = original.split("## ", 1)
        pieces[part] = pieces[part].replace(needle, replacement, 1)
        file.write_text("## ".join(pieces))
        result = extract(root, index, check=False)
        payload = json.loads(index.read_text())
        assert result.returncode == 1
        assert any(issue["rule"] == rule for issue in payload["diagnostics"]["issues"])
        assert len(payload["requirements"]) + len(payload["decisions"]) == records
        file.write_text(original)


def test_document_level_label_after_record_does_not_crash(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    (root / "docs" / "history.md").write_text(
        "# History\n## REQ-FIX-0009: Record\ntext\n## Document History\n**Requires:** old record\n"
    )
    result = extract(root, index, check=False)
    assert result.returncode == 1
    assert json.loads(index.read_text())["metadata"]["files"] == 5


def test_duplicate_and_missing_id(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    requirement = next((root / "docs/requirements").glob("REQ*.md"))
    requirement.write_text(
        requirement.read_text() + next((root / "docs/decisions").glob("ADR*.md")).read_text()
    )
    result = extract(root, index, check=False)
    payload = json.loads(index.read_text())
    assert result.returncode == 1
    assert [issue["rule"] for issue in payload["diagnostics"]["issues"]].count("DUPLICATE_ID") == 2
    assert [
        record
        for record in split(requirement, requirement.read_text())["records"]
        if record["heading_id"] == "ADR-FIX-0002"
    ][-1]["fields"]["Decision Date"]["value"].strip() == "2026-01-07"
    assert len(payload["requirements"]) + len(payload["decisions"]) == 5
    (root / "docs/empty.md").write_text("# Empty\n")
    result = extract(root, index, check=False)
    assert result.returncode == 1
    assert any(
        issue["rule"] == "MISSING_ID"
        for issue in json.loads(index.read_text())["diagnostics"]["issues"]
    )


def test_extractor_ignores_file_level_labels_outside_records(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = next((root / "docs" / "requirements").glob("REQ*.md"))
    file.write_text(file.read_text() + "\n## Appendix\n**Unmapped:** prose\n- item\n")
    assert extract(root, index).returncode == 0


def test_thematic_break_is_not_content():
    tree = split(
        Path("records.md"),
        "## REQ-FIX-0009: Record\n### Notes\n**Status:**\n- old record\n"
        "- item\n---\n### Consequences\ntext\n",
    )
    encoded = json.dumps(tree)
    assert "---" not in encoded
    assert [item["value"] for item in tree["records"][0]["sections"][0]["labels"][0]["items"]] == [
        "old record",
        "item",
    ]
