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
    assert {item["id"] for item in payload["requirements"]} == {item["id"] for item in fixture["requirements"]}
    assert {item["id"] for item in payload["decisions"]} == {item["id"] for item in fixture["decisions"]}
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
        assert payload["diagnostics"]["issues"][0]["rule"] == rule
        assert len(payload["requirements"]) + len(payload["decisions"]) == records
        file.write_text(original)


def test_duplicate_and_missing_id(tmp_path: Path):
    root, index = project(tmp_path), tmp_path / "index.json"
    requirement = next((root / "docs/requirements").glob("REQ*.md"))
    requirement.write_text(requirement.read_text() + next((root / "docs/decisions").glob("ADR*.md")).read_text())
    result = extract(root, index, check=False)
    payload = json.loads(index.read_text())
    assert result.returncode == 1
    assert [issue["rule"] for issue in payload["diagnostics"]["issues"]].count("DUPLICATE_ID") == 2
    assert len(payload["requirements"]) + len(payload["decisions"]) == 5
    (root / "docs/empty.md").write_text("# Empty\n")
    result = extract(root, index, check=False)
    assert result.returncode == 1
    assert any(issue["rule"] == "MISSING_ID" for issue in json.loads(index.read_text())["diagnostics"]["issues"])


def test_splitter_owns_no_schema_label():
    source = (ROOT / "scripts/extract.py").read_text()
    for table in ("requirements", "decisions"):
        for field in json.loads(raptor_schema.field_table(table)):
            assert field["label"] not in source
