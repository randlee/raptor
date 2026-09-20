from __future__ import annotations

from pathlib import Path

from runtime.identity import register_identity
from runtime.rendering import migration_round_trip


def test_round_trip_validate_is_non_mutating(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs/input.md").write_text(
        "### REQ-RAP-001 — Requirement\nStatement.\nAcceptance: accepted.\n"
    )
    register_identity(
        root,
        repository_id="urn:raptor:repo:raptor",
        document_id="DOC-RAP-001",
        repository_path="docs/input.md",
        apply=True,
    )
    before = {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    result = migration_round_trip(
        root,
        "docs/input.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
    )
    assert result["applied"] is False
    assert result["steps"] == [
        "markdown-json",
        "json-sqlite",
        "sqlite-json",
        "json-markdown",
    ]
    assert result["differences"] == []
    assert before == {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
