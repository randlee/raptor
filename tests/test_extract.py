import json
import subprocess
import sys
from pathlib import Path

import raptor_schema

ROOT = Path(__file__).parents[1]


def run(script: str, *args: str, cwd: Path = ROOT, check: bool = True):
    return subprocess.run([sys.executable, ROOT / "scripts" / script, *args], cwd=cwd, text=True, capture_output=True, check=check)


def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    config = root / ".raptor"
    config.mkdir(parents=True)
    (config / "raptor.toml").write_text('repository_id = "urn:test"\n')
    (config / "sources.toml").write_text('[[sources]]\nroot = "docs"\ninclude = ["**/*.md"]\nexclude = []\n')
    run("render.py", str(ROOT / "tests/fixtures/records.json"), "--output-dir", str(root / "docs"))
    return root


def extract(root: Path, output: Path, check: bool = True):
    return run("extract.py", "--project-root", str(root), "--output", str(output), check=check)


def test_round_trip_and_project_root(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    result = extract(root, index)
    payload, fixture = json.loads(index.read_text()), json.loads((ROOT / "tests/fixtures/records.json").read_text())
    for table in ("requirements", "decisions"):
        assert sorted(payload[table], key=lambda item: item["id"]) == sorted(fixture[table], key=lambda item: item["id"])
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
    requirement.write_text(requirement.read_text() + next((root / "docs/decisions").glob("ADR*.md")).read_text())
    result = extract(root, index, check=False)
    payload = json.loads(index.read_text())
    assert result.returncode == 1
    assert [issue["rule"] for issue in payload["diagnostics"]["issues"]].count("DUPLICATE_ID") == 2
    assert len(payload["requirements"]) + len(payload["decisions"]) == 5
    assert next(row for row in payload["decisions"] if row["id"] == "ADR-FIX-0002")["status"] == "Approved"
    (root / "docs/empty.md").write_text("# Empty\n")
    result = extract(root, index, check=False)
    assert result.returncode == 1
    assert any(issue["rule"] == "MISSING_ID" for issue in json.loads(index.read_text())["diagnostics"]["issues"])


def test_splitter_owns_no_schema_label():
    source = (ROOT / "scripts/extract.py").read_text()
    for table in ("requirements", "decisions"):
        for field in json.loads(raptor_schema.field_table(table)):
            assert field["label"] not in source


def test_extractor_ignores_file_level_labels_outside_records(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = next((root / "docs" / "requirements").glob("REQ*.md"))
    file.write_text(file.read_text() + "\n## Appendix\n**Unmapped:** prose\n- item\n")
    assert extract(root, index).returncode == 0


def test_b3_section_diagnostics(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = next((root / "docs/requirements").glob("REQ*.md"))
    for needle, replacement, rule, allowed in [
        ("**Acceptance Criteria:**", "**Acceptance:**", "UNKNOWN_LABEL", ["Acceptance Criteria", "Test Evidence"]),
        ("NFR-FIX-0001 — quality prerequisite", "not-an-id", "BAD_VALUE", None),
        ("NFR-FIX-0001 — quality prerequisite", "NFR-FIX-9999", "DANGLING_REFERENCE", None),
    ]:
        original = file.read_text()
        file.write_text(original.replace(needle, replacement, 1))
        result = extract(root, index, check=False)
        diagnostics = json.loads(index.read_text())["diagnostics"]
        issues = diagnostics["issues"]
        issue = next(issue for issue in issues if issue["rule"] == rule)
        assert result.returncode == 1
        assert any(group["rule"] == rule and group["remedy"] for group in diagnostics["summary"]["groups"])
        if allowed:
            assert issue["allowed"] == allowed
        file.write_text(original)


def test_b4_group_and_supersession_diagnostics(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    file = next((root / "docs/decisions").glob("ADR*.md"))
    for needle, replacement, rule in [("### Consequences", "### Consequences\n\n#### Option A", "UNKNOWN_SECTION"), ("**Supersedes:** ADR-FIX-0001", "**Supersedes:** REQ-FIX-0001", "BAD_VALUE")]:
        original = file.read_text()
        file.write_text(original.replace(needle, replacement, 1))
        assert extract(root, index, check=False).returncode == 1
        assert any(issue["rule"] == rule for issue in json.loads(index.read_text())["diagnostics"]["issues"])
        file.write_text(original)
