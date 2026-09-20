from __future__ import annotations

from pathlib import Path
import json
import shutil
import tempfile

import pytest
from raptor_schema import DocumentKey, SQLiteArtifactStore, SourceDocument

from runtime import agent_runner
from runtime.identity import register_identity
from runtime.profiles import RaptorMarkdownProfile
from runtime.rendering import (
    json_to_markdown,
    migration_round_trip,
    render_markdown,
    resolve_sc_compose,
)
from runtime.operations import export_sqlite, import_sqlite, markdown_to_json

REPO = Path(__file__).resolve().parents[4]


class _OperationBackend:
    def __init__(self, root: Path, *, validate: bool) -> None:
        self._temporary = tempfile.TemporaryDirectory() if validate else None
        self.root = Path(self._temporary.name) / "repo" if validate else root
        if validate:
            shutil.copytree(root, self.root)

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        del timeout_s
        params = json.loads(prompt)["params"]
        name = agent_path.stem
        if name == "markdown-json-import":
            data = markdown_to_json(
                self.root,
                params["input"],
                params["output"],
                profile_id=params["profile"],
                apply=True,
            )
        elif name == "json-sqlite-import":
            data = import_sqlite(
                self.root, params["input"], params["database"], apply=True
            )
        elif name == "sqlite-json-export":
            data = export_sqlite(
                self.root,
                params["database"],
                params["repository_id"],
                params["document_id"],
                params["output"],
                apply=True,
            )
        else:
            data = json_to_markdown(
                self.root,
                params["input"],
                params["output"],
                profile_id=params["profile"],
                template_set=params["template_set"],
                database=params["database"],
                apply=True,
            )
        envelope = {
            "success": True,
            "canceled": False,
            "aborted_by": None,
            "data": data,
            "error": None,
            "metadata": {"duration_ms": 0, "tool_calls": 0, "retry_count": 0},
        }
        return "```json\n" + json.dumps(envelope, sort_keys=True) + "\n```"


@pytest.mark.parametrize("family", ["requirement", "nfr", "adr", "design", "test-plan"])
@pytest.mark.parametrize("apply", [False, True])
def test_round_trip_composes_registered_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, apply: bool, family: str
) -> None:
    calls: list[dict[str, object]] = []

    def composed(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        data: dict[str, object] = {"composed": True}
        if kwargs.get("agent") == "markdown-json-import":
            data["documents"] = [
                {
                    "repository_id": "urn:raptor:repo:raptor",
                    "document_id": "DOC-RAP-001",
                }
            ]
        return {"success": True, "data": data}

    monkeypatch.setattr(agent_runner, "run_agent", composed)
    result = migration_round_trip(
        tmp_path,
        f"docs/{family}.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
        backend=object(),
        apply=apply,
    )
    assert result["success"] is True, result
    assert len(calls) == 4
    first = calls[0]["params"]
    assert isinstance(first, dict) and first["apply"] is apply
    assert first["input"] == f"docs/{family}.md"


def test_round_trip_failure_short_circuits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0

    def failed(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        data = (
            {
                "documents": [
                    {
                        "repository_id": "urn:raptor:repo:raptor",
                        "document_id": "DOC-RAP-001",
                    }
                ]
            }
            if calls == 1
            else None
        )
        return {
            "success": calls < 2,
            "data": data,
            "error": None if calls < 2 else {"code": "RAPTOR.STEP.FAILED"},
        }

    monkeypatch.setattr(agent_runner, "run_agent", failed)
    result = migration_round_trip(
        tmp_path,
        "docs/input.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
        backend=object(),
    )
    assert result["success"] is False and calls == 2


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("apply", [False, True])
def test_real_five_family_pipeline(tmp_path: Path, index: int, apply: bool) -> None:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    value = json.loads((REPO / "schema/tests/corpus/all-families.json").read_text())
    artifact = value["artifacts"][index]
    artifact_id = artifact["id"]
    # A single Markdown file is document-mode by contract. Keep each focused
    # family self-contained while retaining its typed reference projection.
    if index == 1:
        artifact["relationships"][0]["target"]["artifact_id"] = artifact_id
    elif index == 3:
        artifact["components"][0]["dependencies"][0]["artifact_id"] = artifact_id
    elif index == 4:
        artifact["test_cases"][0]["verifies"] = [
            {
                "repository_id": "urn:raptor:repo:raptor",
                "artifact_id": artifact_id,
            }
        ]
    value["artifacts"] = [artifact]
    document = SourceDocument.model_validate(value)
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
    register_identity(
        root,
        repository_id=origin.repository_id,
        document_id=origin.document_id,
        repository_path="docs/input.md",
        apply=True,
    )
    backend = _OperationBackend(root, validate=not apply)
    result = migration_round_trip(
        root,
        "docs/input.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
        backend=backend,
        apply=apply,
    )
    assert result["success"] is True, result
    evidence_root = backend.root
    assert (evidence_root / "docs/output.md").is_file()
    store = SQLiteArtifactStore.open_read_only(evidence_root / "raptor.sqlite")
    recovered = store.get_document(
        DocumentKey(repository_id=origin.repository_id, document_id=origin.document_id)
    )
    store.close()
    assert recovered.provenance.origin == origin
    if not apply:
        assert not (root / "canonical.json").exists()
