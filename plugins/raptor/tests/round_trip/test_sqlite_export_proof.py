from __future__ import annotations

import json
from pathlib import Path

import pytest
from raptor_schema import IngressReport, SourceDocument

from runtime.identity import register_identity
from runtime.operations import import_sqlite, markdown_to_json, sqlite_export_proof
from runtime.profiles import RaptorMarkdownProfile
from runtime.rendering import render_markdown, resolve_sc_compose

REPO = Path(__file__).resolve().parents[4]


def _document(index: int) -> SourceDocument:
    payload = json.loads((REPO / "schema/tests/corpus/all-families.json").read_text())
    artifact = payload["artifacts"][index]
    artifact_id = artifact["id"]
    if index == 1:
        artifact["relationships"][0]["target"]["artifact_id"] = artifact_id
    elif index == 3:
        artifact["components"][0]["dependencies"][0]["artifact_id"] = artifact_id
    elif index == 4:
        artifact["test_cases"][0]["verifies"] = [
            {"repository_id": "urn:raptor:repo:raptor", "artifact_id": artifact_id}
        ]
    payload["artifacts"] = [artifact]
    return SourceDocument.model_validate(payload)


@pytest.mark.parametrize("index", range(5))
def test_sqlite_export_render_reparse_has_zero_loss(tmp_path: Path, index: int) -> None:
    root = tmp_path / "repository"
    (root / "docs").mkdir(parents=True)
    document = _document(index)
    input_path = "docs/input.md"
    source = render_markdown(
        document,
        profile=RaptorMarkdownProfile(),
        template_set="raptor",
        output_path=input_path,
        repository_root=root,
        executable=resolve_sc_compose(),
    )
    (root / input_path).write_bytes(source.content)
    origin = document.provenance.origin
    register_identity(
        root,
        repository_id=origin.repository_id,
        document_id=origin.document_id,
        repository_path=input_path,
        apply=True,
    )
    markdown_to_json(root, input_path, "canonical.json", apply=True)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)

    result = sqlite_export_proof(
        root,
        "raptor.sqlite",
        origin.repository_id,
        origin.document_id,
        "docs/output.md",
        "proof.json",
        apply=True,
    )

    report = IngressReport.model_validate(result["report_data"])
    entry = report.entries[0]
    assert entry.zero_loss is True
    assert entry.artifact_order_preserved is True
    assert entry.identity_preserved is True
    assert entry.origin_preserved is True
    assert entry.materialization_preserved is True
    assert (root / "docs/output.md").is_file()
    assert (root / "proof.json").is_file()


def test_sqlite_export_proof_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "docs").mkdir(parents=True)
    document = _document(0)
    source = render_markdown(
        document,
        profile=RaptorMarkdownProfile(),
        template_set="raptor",
        output_path="docs/input.md",
        repository_root=root,
        executable=resolve_sc_compose(),
    )
    (root / "docs/input.md").write_bytes(source.content)
    origin = document.provenance.origin
    register_identity(root, repository_id=origin.repository_id, document_id=origin.document_id, repository_path="docs/input.md", apply=True)
    markdown_to_json(root, "docs/input.md", "canonical.json", apply=True)
    import_sqlite(root, "canonical.json", "raptor.sqlite", apply=True)
    arguments = (root, "raptor.sqlite", origin.repository_id, origin.document_id, "docs/output.md", "proof.json")

    sqlite_export_proof(*arguments, apply=True)
    first = (root / "docs/output.md").read_bytes(), (root / "proof.json").read_bytes()
    sqlite_export_proof(*arguments, apply=True)
    second = (root / "docs/output.md").read_bytes(), (root / "proof.json").read_bytes()

    assert first == second
