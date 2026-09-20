from __future__ import annotations

import json
from pathlib import Path

import pytest
from raptor_schema import (
    DocumentKey,
    SQLiteArtifactStore,
    SourceDocument,
    load_canonical_json,
)

from runtime.identity import register_identity
from runtime.io import repository_lock
from runtime.profiles import RaptorMarkdownProfile
from runtime.rendering import RenderedDocument, render_markdown, resolve_sc_compose
from runtime.transactions import apply_render_transaction, recover_render_transaction

REPO = Path(__file__).resolve().parents[4]
FIXTURE = REPO / "plugins/raptor/tests/fixtures/raptor/requirement.json"


def _recover(root: Path, key: DocumentKey) -> dict[str, object]:
    return recover_render_transaction(
        root,
        key,
        old_path="docs/requirements.md",
        new_path="docs/rendered.md",
        database="raptor.sqlite",
    )


def _repository(tmp_path: Path) -> tuple[Path, SourceDocument, RenderedDocument]:
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    previous = load_canonical_json(FIXTURE.read_bytes())
    (root / "docs/requirements.md").write_bytes(b"prior\n")
    register_identity(
        root,
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
        repository_path="docs/requirements.md",
        apply=True,
    )
    database = root / "raptor.sqlite"
    store = SQLiteArtifactStore(database)
    store.initialize()
    store.put_document(previous)
    store.close()
    rendered = render_markdown(
        previous,
        profile=RaptorMarkdownProfile(),
        template_set="raptor",
        output_path="docs/rendered.md",
        repository_root=root,
        executable=resolve_sc_compose(),
    )
    return root, previous, rendered


def test_transaction_commits_output_identity_and_database(tmp_path: Path) -> None:
    root, previous, rendered = _repository(tmp_path)
    result = apply_render_transaction(
        root, previous, rendered.document, rendered.content, "raptor.sqlite"
    )
    assert result["state"] == "complete"
    assert (root / "docs/rendered.md").read_bytes() == rendered.content


@pytest.mark.parametrize(
    "boundary",
    [
        "after_prepared",
        "before_output_committed",
        "after_output_committed",
        "before_identity_committed",
    ],
)
def test_pre_identity_crash_recovers_by_rollback(tmp_path: Path, boundary: str) -> None:
    root, previous, rendered = _repository(tmp_path)
    with pytest.raises(RuntimeError, match="injected failure"):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at=boundary,
        )
    key = DocumentKey(
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
    )
    assert _recover(root, key)["state"] == "rolled_back"


@pytest.mark.parametrize(
    "boundary",
    [
        "before_db_pending",
        "after_identity_committed",
        "after_db_pending",
        "before_db_commit",
        "after_db_commit",
        "before_complete",
        "after_complete",
    ],
)
def test_post_identity_crash_recovers_by_roll_forward(
    tmp_path: Path, boundary: str
) -> None:
    root, previous, rendered = _repository(tmp_path)
    with pytest.raises(RuntimeError, match="injected failure"):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at=boundary,
        )
    key = DocumentKey(
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
    )
    result = _recover(root, key)
    assert result["state"] == "complete"
    store = SQLiteArtifactStore(root / "raptor.sqlite")
    assert store.get_document(key) == rendered.document
    store.close()


def test_failure_before_prepared_has_no_transaction(tmp_path: Path) -> None:
    root, previous, rendered = _repository(tmp_path)
    with pytest.raises(RuntimeError):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at="before_prepared",
        )
    assert not list((root / ".raptor/transactions").glob("*.json"))


def test_lock_exclusion_db_pending_conflict_and_cleanup(tmp_path: Path) -> None:
    root, previous, rendered = _repository(tmp_path)
    key = DocumentKey(
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
    )
    transaction_id = (
        __import__("hashlib")
        .sha256(f"{key.repository_id}\0{key.document_id}".encode())
        .hexdigest()[:32]
    )
    with repository_lock(root, f".raptor/transactions/{transaction_id}.lock"):
        with pytest.raises(ValueError, match="TRANSACTION.BUSY"):
            apply_render_transaction(
                root, previous, rendered.document, rendered.content, "raptor.sqlite"
            )

    with pytest.raises(RuntimeError):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at="after_identity_committed",
        )
    database = root / "raptor.sqlite"
    saved = database.read_bytes()
    database.unlink()
    with pytest.raises(ValueError, match="DB_PENDING"):
        _recover(root, key)
    database.write_bytes(saved)
    assert _recover(root, key)["state"] == "complete"
    sidecars = [
        path
        for path in (root / ".raptor/transactions").iterdir()
        if not path.name.endswith(".lock")
    ]
    assert sidecars == []


def test_recovery_refuses_changed_committed_output(tmp_path: Path) -> None:
    root, previous, rendered = _repository(tmp_path)
    with pytest.raises(RuntimeError):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at="after_identity_committed",
        )
    (root / "docs/rendered.md").write_text("tampered")
    key = DocumentKey(
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
    )
    with pytest.raises(ValueError, match="RECOVERY_CONFLICT"):
        _recover(root, key)


def test_forged_marker_path_is_rejected_without_deleting_target(tmp_path: Path) -> None:
    root, previous, rendered = _repository(tmp_path)
    with pytest.raises(RuntimeError):
        apply_render_transaction(
            root,
            previous,
            rendered.document,
            rendered.content,
            "raptor.sqlite",
            fail_at="after_prepared",
        )
    marker_path = next((root / ".raptor/transactions").glob("*.json"))
    marker = json.loads(marker_path.read_text())
    victim = root / "do-not-delete.txt"
    victim.write_text("safe")
    marker["output_stage_path"] = "do-not-delete.txt"
    marker_path.write_text(json.dumps(marker))
    key = DocumentKey(
        repository_id=previous.provenance.origin.repository_id,
        document_id=previous.provenance.origin.document_id,
    )
    with pytest.raises(ValueError, match="RECOVERY_CONFLICT"):
        _recover(root, key)
    assert victim.read_text() == "safe"
