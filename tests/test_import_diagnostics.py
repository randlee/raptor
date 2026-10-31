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
