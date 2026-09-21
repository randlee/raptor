from __future__ import annotations

import hashlib
import json
import tempfile
from contextlib import contextmanager
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterator

from raptor_schema import (
    DocumentKey,
    IdentityDocument,
    IdentityManifest,
    SQLiteArtifactStore,
    SourceDocument,
    dump_canonical_json,
)
from raptor_schema.profiles import SourceInput

from .identity import IDENTITY_RELATIVE, load_identity
from .io import (
    atomic_repository_bytes,
    read_repository_bytes,
    remove_repository_file,
    repository_lock,
    repository_parts,
)
from .strict_json import loads
from .profiles import RaptorMarkdownProfile

TRANSACTION_VERSION = "1"
_STATES = {
    "prepared",
    "output_committed",
    "identity_committed",
    "db_pending",
    "complete",
}


class TransactionError(ValueError):
    pass


def apply_render_transaction(
    repository_root: Path,
    previous: SourceDocument,
    rendered: SourceDocument,
    content: bytes,
    database: str,
    *,
    fail_at: str | None = None,
) -> dict[str, object]:
    _fail(fail_at, "before_prepared")
    root = repository_root.resolve()
    key = _document_key(previous)
    if _document_key(rendered) != key:
        raise TransactionError(
            "RAPTOR.PROVENANCE.ORIGIN_MUTATION: document key changed"
        )
    transaction_id = _transaction_id(key)
    marker_path = f".raptor/transactions/{transaction_id}.json"
    with _lock(root, transaction_id):
        with repository_lock(root, ".raptor/identity.lock"):
            if _exists(root, marker_path):
                return _recover_locked(
                    root,
                    marker_path,
                    key=key,
                    old_path=previous.provenance.materialization.repository_path,
                    new_path=rendered.provenance.materialization.repository_path,
                    database=_relative(database),
                    fail_at=fail_at,
                )
            return _start(
                root, previous, rendered, content, database, marker_path, fail_at
            )


def recover_render_transaction(
    repository_root: Path,
    key: DocumentKey,
    *,
    old_path: str,
    new_path: str,
    database: str,
    fail_at: str | None = None,
) -> dict[str, object]:
    root = repository_root.resolve()
    transaction_id = _transaction_id(key)
    marker_path = f".raptor/transactions/{transaction_id}.json"
    with _lock(root, transaction_id):
        with repository_lock(root, ".raptor/identity.lock"):
            if not _exists(root, marker_path):
                return {"recovered": False, "state": None}
            return _recover_locked(
                root,
                marker_path,
                key=key,
                old_path=_relative(old_path),
                new_path=_relative(new_path),
                database=_relative(database),
                fail_at=fail_at,
            )


def validate_render_transaction(
    repository_root: Path,
    previous: SourceDocument,
    rendered: SourceDocument,
    database: str,
) -> None:
    _validate_context(
        repository_root.resolve(), previous, rendered, _relative(database)
    )


def _start(
    root: Path,
    previous: SourceDocument,
    rendered: SourceDocument,
    content: bytes,
    database: str,
    marker_path: str,
    fail_at: str | None,
) -> dict[str, object]:
    key = _document_key(previous)
    old_path = previous.provenance.materialization.repository_path
    new_path = rendered.provenance.materialization.repository_path
    database = _relative(database)
    manifest = _validate_context(root, previous, rendered, database)
    documents = dict(manifest.documents)
    documents[key.document_id] = IdentityDocument(path=new_path)
    next_manifest = IdentityManifest.model_validate(
        {**manifest.model_dump(mode="json"), "documents": documents}
    )
    identity_bytes = _identity_bytes(next_manifest)
    transaction_id = _transaction_id(key)
    output_stage = f"{new_path}.raptor-{transaction_id}.stage"
    output_backup = f"{new_path}.raptor-{transaction_id}.backup"
    identity_stage = f".raptor/identity.json.raptor-{transaction_id}.stage"
    identity_backup = f".raptor/identity.json.raptor-{transaction_id}.backup"
    output_before = _read_optional(root, new_path)
    identity_before = read_repository_bytes(root, IDENTITY_RELATIVE)
    atomic_repository_bytes(root, output_stage, content)
    atomic_repository_bytes(root, identity_stage, identity_bytes)
    if output_before is not None:
        atomic_repository_bytes(root, output_backup, output_before)
    atomic_repository_bytes(root, identity_backup, identity_before)
    marker: dict[str, Any] = {
        "transaction_version": TRANSACTION_VERSION,
        "transaction_id": transaction_id,
        "document_key": key.model_dump(mode="json"),
        "old_path": old_path,
        "new_path": new_path,
        "output_stage_path": output_stage,
        "output_backup_path": output_backup if output_before is not None else None,
        "identity_stage_path": identity_stage,
        "identity_backup_path": identity_backup,
        "database_path": database,
        "output_before_sha256": _digest(output_before),
        "output_after_sha256": _digest(content),
        "identity_before_sha256": _digest(identity_before),
        "identity_after_sha256": _digest(identity_bytes),
        "state": "prepared",
    }
    _write_marker(root, marker_path, marker, "prepared")
    _fail(fail_at, "after_prepared")
    return _commit(root, marker_path, marker, fail_at=fail_at)


def _validate_context(
    root: Path,
    previous: SourceDocument,
    rendered: SourceDocument,
    database: str,
) -> IdentityManifest:
    key = _document_key(previous)
    old_path = previous.provenance.materialization.repository_path
    new_path = rendered.provenance.materialization.repository_path
    if _document_key(rendered) != key:
        raise TransactionError(
            "RAPTOR.PROVENANCE.ORIGIN_MUTATION: document key changed"
        )
    if not _exists(root, database):
        raise TransactionError(
            "RAPTOR.TRANSACTION.DB_PENDING: SQLite database is unavailable"
        )
    manifest = load_identity(root, repository_path=old_path)
    if manifest.repository_id != key.repository_id:
        raise TransactionError("RAPTOR.PROVENANCE.ORIGIN_MUTATION: repository changed")
    current = manifest.documents.get(key.document_id)
    if current is None or current.path != old_path:
        raise TransactionError("RAPTOR.IDENTITY.MISSING: prior path is not registered")
    if any(
        document_id != key.document_id and document.path == new_path
        for document_id, document in manifest.documents.items()
    ):
        raise TransactionError(
            "RAPTOR.IDENTITY.PATH_CONFLICT: output path is registered"
        )
    try:
        stored = _read_stored_document(root, database, key)
    except Exception as error:
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: stored document is unavailable"
        ) from error
    if dump_canonical_json(stored) != dump_canonical_json(previous):
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: stored document changed"
        )
    return manifest


def _commit(
    root: Path, marker_path: str, marker: dict[str, Any], *, fail_at: str | None
) -> dict[str, object]:
    state = marker["state"]
    if state == "prepared":
        _fail(fail_at, "before_output_committed")
        output = read_repository_bytes(root, marker["output_stage_path"])
        _require_hash(output, marker["output_after_sha256"])
        current_output = _read_optional(root, marker["new_path"])
        if _digest(current_output) == marker["output_before_sha256"]:
            atomic_repository_bytes(root, marker["new_path"], output)
        elif _digest(current_output) != marker["output_after_sha256"]:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: output changed"
            )
        _fail(fail_at, "after_output_replace")
        _write_marker(root, marker_path, marker, "output_committed")
        _fail(fail_at, "after_output_committed")
        state = "output_committed"
    if state == "output_committed":
        _fail(fail_at, "before_identity_committed")
        identity = read_repository_bytes(root, marker["identity_stage_path"])
        _require_hash(identity, marker["identity_after_sha256"])
        current = read_repository_bytes(root, IDENTITY_RELATIVE)
        if _digest(current) == marker["identity_before_sha256"]:
            atomic_repository_bytes(root, IDENTITY_RELATIVE, identity)
        elif _digest(current) != marker["identity_after_sha256"]:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: identity changed"
            )
        _fail(fail_at, "after_identity_replace")
        _write_marker(root, marker_path, marker, "identity_committed")
        _fail(fail_at, "after_identity_committed")
        state = "identity_committed"
    if state == "identity_committed":
        _fail(fail_at, "before_db_pending")
        _write_marker(root, marker_path, marker, "db_pending")
        _fail(fail_at, "after_db_pending")
    document = _verified_document(root, marker)
    _fail(fail_at, "before_db_commit")
    try:
        _put_stored_document(root, marker["database_path"], document)
    except Exception as error:
        _write_marker(root, marker_path, marker, "db_pending")
        raise TransactionError(
            "RAPTOR.TRANSACTION.DB_PENDING: SQLite update requires recovery"
        ) from error
    _fail(fail_at, "after_db_commit")
    _require_live_hashes(root, marker)
    _fail(fail_at, "before_complete")
    _write_marker(root, marker_path, marker, "complete")
    _fail(fail_at, "after_complete")
    _fail(fail_at, "before_cleanup")
    _cleanup(root, marker_path, marker)
    _fail(fail_at, "after_cleanup")
    return {
        "recovered": False,
        "state": "complete",
        "transaction_id": marker["transaction_id"],
    }


def _recover_locked(
    root: Path,
    marker_path: str,
    *,
    key: DocumentKey,
    old_path: str,
    new_path: str,
    database: str,
    fail_at: str | None,
) -> dict[str, object]:
    marker = _load_marker(
        root,
        marker_path,
        key=key,
        old_path=old_path,
        new_path=new_path,
        database=database,
    )
    state = marker["state"]
    if state == "complete":
        _verify_complete(root, marker)
        _cleanup(root, marker_path, marker)
        return {"recovered": True, "state": "complete"}
    if state in {"prepared", "output_committed"}:
        _rollback(root, marker)
        _cleanup(root, marker_path, marker)
        return {"recovered": True, "state": "rolled_back"}
    _require_live_hashes(root, marker)
    result = _commit(root, marker_path, marker, fail_at=fail_at)
    result["recovered"] = True
    return result


def _rollback(root: Path, marker: dict[str, Any]) -> None:
    if marker["output_backup_path"] is None:
        current = _read_optional(root, marker["new_path"])
        if current is not None:
            _require_hash(current, marker["output_after_sha256"])
            _remove(root, marker["new_path"])
    else:
        backup = read_repository_bytes(root, marker["output_backup_path"])
        _require_hash(backup, marker["output_before_sha256"])
        current = read_repository_bytes(root, marker["new_path"])
        if _digest(current) == marker["output_after_sha256"]:
            atomic_repository_bytes(root, marker["new_path"], backup)
        elif _digest(current) != marker["output_before_sha256"]:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: output changed"
            )
    identity = read_repository_bytes(root, marker["identity_backup_path"])
    _require_hash(identity, marker["identity_before_sha256"])
    current_identity = read_repository_bytes(root, IDENTITY_RELATIVE)
    if _digest(current_identity) == marker["identity_after_sha256"]:
        atomic_repository_bytes(root, IDENTITY_RELATIVE, identity)
    elif _digest(current_identity) != marker["identity_before_sha256"]:
        raise TransactionError("RAPTOR.TRANSACTION.RECOVERY_CONFLICT: identity changed")


def _require_live_hashes(root: Path, marker: dict[str, Any]) -> None:
    _require_hash(
        read_repository_bytes(root, marker["new_path"]),
        marker["output_after_sha256"],
    )
    _require_hash(
        read_repository_bytes(root, IDENTITY_RELATIVE),
        marker["identity_after_sha256"],
    )


def _verify_complete(root: Path, marker: dict[str, Any]) -> None:
    try:
        _require_live_hashes(root, marker)
        document = _verified_document(root, marker)
        stored = _read_stored_document(
            root, marker["database_path"], _document_key(document)
        )
    except Exception as error:
        if isinstance(error, TransactionError):
            raise
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: complete state is invalid"
        ) from error
    if dump_canonical_json(stored) != dump_canonical_json(document):
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: stored document changed"
        )


def _read_stored_document(
    root: Path, database: str, key: DocumentKey
) -> SourceDocument:
    payload = read_repository_bytes(root, database)
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "store.sqlite"
        snapshot.write_bytes(payload)
        store = SQLiteArtifactStore.open_read_only(snapshot)
        try:
            return store.get_document(key)
        finally:
            store.close()


def _put_stored_document(root: Path, database: str, document: SourceDocument) -> None:
    before = read_repository_bytes(root, database)
    lock_name = hashlib.sha256(database.encode()).hexdigest()[:24]
    with repository_lock(root, f".raptor/transactions/database-{lock_name}.lock"):
        if read_repository_bytes(root, database) != before:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: database changed"
            )
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "store.sqlite"
            snapshot.write_bytes(before)
            store = SQLiteArtifactStore(snapshot)
            try:
                store.put_document(document)
                if dump_canonical_json(
                    store.get_document(_document_key(document))
                ) != dump_canonical_json(document):
                    raise TransactionError(
                        "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: stored document changed"
                    )
            finally:
                store.close()
            after = snapshot.read_bytes()
        if read_repository_bytes(root, database) != before:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: database changed"
            )
        atomic_repository_bytes(root, database, after)


def _verified_document(root: Path, marker: dict[str, Any]) -> SourceDocument:
    value = read_repository_bytes(root, marker["new_path"])
    _require_hash(value, marker["output_after_sha256"])
    key = DocumentKey.model_validate(marker["document_key"])
    source = SourceInput(
        repo_root=root,
        repository_id=key.repository_id,
        document_id=key.document_id,
        repository_path=PurePosixPath(marker["new_path"]),
        content=value,
    )
    profile = RaptorMarkdownProfile()
    return profile.canonicalize(profile.parse(source))


def _load_marker(
    root: Path,
    marker_path: str,
    *,
    key: DocumentKey,
    old_path: str,
    new_path: str,
    database: str,
) -> dict[str, Any]:
    try:
        value = loads(read_repository_bytes(root, marker_path).decode())
    except Exception as error:
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker"
        ) from error
    required = {
        "transaction_version",
        "transaction_id",
        "document_key",
        "old_path",
        "new_path",
        "output_stage_path",
        "output_backup_path",
        "identity_stage_path",
        "identity_backup_path",
        "database_path",
        "output_before_sha256",
        "output_after_sha256",
        "identity_before_sha256",
        "identity_after_sha256",
        "state",
    }
    if (
        not isinstance(value, dict)
        or set(value) != required
        or value.get("state") not in _STATES
    ):
        raise TransactionError("RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker")
    marker_key = DocumentKey.model_validate(value["document_key"])
    transaction_id = _transaction_id(key)
    if (
        marker_key != key
        or value["transaction_version"] != TRANSACTION_VERSION
        or value["transaction_id"] != transaction_id
        or marker_path != f".raptor/transactions/{transaction_id}.json"
        or value["old_path"] != old_path
        or value["new_path"] != new_path
        or value["database_path"] != database
        or value["output_stage_path"] != f"{new_path}.raptor-{transaction_id}.stage"
        or value["identity_stage_path"]
        != f".raptor/identity.json.raptor-{transaction_id}.stage"
        or value["identity_backup_path"]
        != f".raptor/identity.json.raptor-{transaction_id}.backup"
    ):
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker identity"
        )
    for name in (
        "old_path",
        "new_path",
        "output_stage_path",
        "identity_stage_path",
        "identity_backup_path",
        "database_path",
    ):
        if not isinstance(value[name], str) or _relative(value[name]) != value[name]:
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker path"
            )
    if value["output_backup_path"] is not None:
        _relative(value["output_backup_path"])
        if value["output_backup_path"] != f"{new_path}.raptor-{transaction_id}.backup":
            raise TransactionError(
                "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker path"
            )
    if (value["output_backup_path"] is None) != (value["output_before_sha256"] is None):
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid marker backup"
        )
    for name in (
        "output_after_sha256",
        "identity_before_sha256",
        "identity_after_sha256",
    ):
        if not isinstance(value[name], str) or re_full_hash(value[name]) is False:
            raise TransactionError("RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid hash")
    before = value["output_before_sha256"]
    if before is not None and (not isinstance(before, str) or not re_full_hash(before)):
        raise TransactionError("RAPTOR.TRANSACTION.RECOVERY_CONFLICT: invalid hash")
    return value


def _write_marker(root: Path, path: str, value: dict[str, Any], state: str) -> None:
    value["state"] = state
    atomic_repository_bytes(
        root,
        path,
        (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )


def _cleanup(root: Path, marker_path: str, marker: dict[str, Any]) -> None:
    for name in (
        "output_stage_path",
        "output_backup_path",
        "identity_stage_path",
        "identity_backup_path",
    ):
        path = marker.get(name)
        if isinstance(path, str):
            _remove(root, path)
    _remove(root, marker_path)


@contextmanager
def _lock(root: Path, transaction_id: str) -> Iterator[None]:
    try:
        with repository_lock(root, f".raptor/transactions/{transaction_id}.lock"):
            yield
    except BlockingIOError as error:
        raise TransactionError("RAPTOR.TRANSACTION.BUSY: document is locked") from error


def _identity_bytes(value: IdentityManifest) -> bytes:
    return (
        json.dumps(value.model_dump(mode="json"), sort_keys=True, indent=2) + "\n"
    ).encode()


def _document_key(document: SourceDocument) -> DocumentKey:
    origin = document.provenance.origin
    return DocumentKey(
        repository_id=origin.repository_id, document_id=origin.document_id
    )


def _transaction_id(key: DocumentKey) -> str:
    return hashlib.sha256(
        f"{key.repository_id}\0{key.document_id}".encode()
    ).hexdigest()[:32]


def _relative(value: str) -> str:
    return Path(*repository_parts(value)).as_posix()


def _exists(root: Path, relative: str) -> bool:
    try:
        read_repository_bytes(root, relative)
    except ValueError:
        return False
    return True


def _read_optional(root: Path, relative: str) -> bytes | None:
    try:
        return read_repository_bytes(root, relative)
    except ValueError:
        return None


def _remove(root: Path, relative: str) -> None:
    try:
        remove_repository_file(root, relative)
    except ValueError as error:
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: sidecar is unsafe"
        ) from error


def _digest(value: bytes | None) -> str | None:
    return hashlib.sha256(value).hexdigest() if value is not None else None


def _require_hash(value: bytes, expected: str | None) -> None:
    if expected is None or _digest(value) != expected:
        raise TransactionError(
            "RAPTOR.TRANSACTION.RECOVERY_CONFLICT: content hash mismatch"
        )


def re_full_hash(value: str) -> bool:
    return len(value) == 64 and all(item in "0123456789abcdef" for item in value)


def _fail(selected: str | None, boundary: str) -> None:
    if selected == boundary:
        raise RuntimeError(f"injected failure at {boundary}")


__all__ = [
    "TRANSACTION_VERSION",
    "TransactionError",
    "apply_render_transaction",
    "recover_render_transaction",
    "validate_render_transaction",
]
