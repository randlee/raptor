from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from raptor_schema import (
    ArtifactKey,
    DocumentKey,
    Diagnostic,
    ReferenceValidationMode,
    SQLiteArtifactStore,
    SourceDocument,
    dump_canonical_json,
    load_canonical_json,
    validate_document,
    validate_documents,
)
from raptor_schema.profiles import ParsedDocument, SourceInput

from .identity import document_identity
from .profiles import resolve_profile


def repository_path(
    repository_root: Path,
    value: str | Path,
    *,
    must_exist: bool = False,
) -> tuple[Path, str]:
    root = repository_root.resolve()
    raw = str(value)
    if not root.is_dir() or not raw or raw == "-" or "\\" in raw:
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: path must be repository-relative")
    relative = PurePosixPath(raw)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: path must be normalized")
    candidate = root.joinpath(*relative.parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(
            "RAPTOR.PATH.OUTSIDE_ROOT: path escapes repository root"
        ) from error
    if must_exist and not candidate.exists():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: input does not exist")
    return candidate, relative.as_posix()


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _markdown_sources(
    repository_root: Path,
    input_path: str,
    *,
    profile_id: str,
    profile_version: str | None,
    allow_profile_code: bool,
) -> tuple[SourceDocument, ...]:
    source_path, _ = repository_path(repository_root, input_path, must_exist=True)
    paths = (
        tuple(sorted(source_path.rglob("*.md")))
        if source_path.is_dir()
        else (source_path,)
    )
    profile = resolve_profile(
        repository_root,
        profile_id,
        profile_version,
        allow_profile_code=allow_profile_code,
    )
    documents: list[SourceDocument] = []
    root = repository_root.resolve()
    for path in paths:
        relative = path.relative_to(root).as_posix()
        repository_id, document_id = document_identity(root, relative)
        source = SourceInput(
            repo_root=root,
            repository_id=repository_id,
            document_id=document_id,
            repository_path=PurePosixPath(relative),
            content=path.read_bytes(),
        )
        try:
            parsed = profile.parse(source)
        except Exception as error:
            raise ValueError("RAPTOR.PROFILE.PARSE: profile parse failed") from error
        if not isinstance(parsed, ParsedDocument):
            raise ValueError(
                "RAPTOR.PROFILE.RETURN_TYPE: parse returned an invalid value"
            )
        try:
            diagnostics = profile.validate(parsed)
        except Exception as error:
            raise ValueError(
                "RAPTOR.PROFILE.VALIDATION: profile validation failed"
            ) from error
        if not isinstance(diagnostics, list) or any(
            not isinstance(item, Diagnostic) for item in diagnostics
        ):
            raise ValueError(
                "RAPTOR.PROFILE.RETURN_TYPE: validate returned an invalid value"
            )
        if diagnostics:
            raise ValueError(f"RAPTOR.PROFILE.VALIDATION: {diagnostics[0].code}")
        try:
            document = profile.canonicalize(parsed)
        except Exception as error:
            raise ValueError(
                "RAPTOR.PROFILE.CANONICALIZE: canonical conversion failed"
            ) from error
        if not isinstance(document, SourceDocument):
            raise ValueError(
                "RAPTOR.PROFILE.RETURN_TYPE: canonicalize returned an invalid value"
            )
        documents.append(document)
    return tuple(documents)


def validate_markdown(
    repository_root: Path,
    input_path: str,
    *,
    profile_id: str = "raptor",
    profile_version: str | None = None,
    reference_mode: str = "document",
    database: str | None = None,
    allow_profile_code: bool = False,
) -> dict[str, Any]:
    documents = _markdown_sources(
        repository_root,
        input_path,
        profile_id=profile_id,
        profile_version=profile_version,
        allow_profile_code=allow_profile_code,
    )
    _validate_references(repository_root, documents, reference_mode, database)
    return {
        "diagnostics": [],
        "documents": [
            {
                "repository_id": item.provenance.origin.repository_id,
                "document_id": item.provenance.origin.document_id,
                "repository_path": item.provenance.materialization.repository_path,
            }
            for item in documents
        ],
    }


def markdown_to_json(
    repository_root: Path,
    input_path: str,
    output_path: str,
    *,
    profile_id: str = "raptor",
    profile_version: str | None = None,
    reference_mode: str = "document",
    database: str | None = None,
    allow_profile_code: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    documents = _markdown_sources(
        repository_root,
        input_path,
        profile_id=profile_id,
        profile_version=profile_version,
        allow_profile_code=allow_profile_code,
    )
    _validate_references(repository_root, documents, reference_mode, database)
    if len(documents) != 1:
        raise ValueError(
            "RAPTOR.OPERATION.CARDINALITY: one output requires one document"
        )
    canonical = dump_canonical_json(documents[0])
    if output_path == "-":
        return {"applied": False, "canonical_json": canonical}
    destination, relative = repository_path(repository_root, output_path)
    if apply:
        _atomic_text(destination, canonical)
    return {
        "applied": apply,
        "output": relative,
        "document": {
            "repository_id": documents[0].provenance.origin.repository_id,
            "document_id": documents[0].provenance.origin.document_id,
        },
    }


def _json_documents(
    repository_root: Path, input_path: str
) -> tuple[SourceDocument, ...]:
    path, _ = repository_path(repository_root, input_path, must_exist=True)
    paths = tuple(sorted(path.rglob("*.json"))) if path.is_dir() else (path,)
    return tuple(load_canonical_json(item.read_bytes()) for item in paths)


class _Resolver:
    def __init__(
        self, staged: tuple[SourceDocument, ...], store: SQLiteArtifactStore | None
    ) -> None:
        self._keys = {
            (document.provenance.origin.repository_id, artifact.id)
            for document in staged
            for artifact in document.artifacts
        }
        self._store = store

    def contains(self, key: ArtifactKey) -> bool:
        return key.sort_key() in self._keys or bool(
            self._store and self._store.contains(key)
        )


def _validate_references(
    repository_root: Path,
    documents: tuple[SourceDocument, ...],
    mode_value: str,
    database: str | None,
) -> None:
    mode = ReferenceValidationMode(mode_value)
    store: SQLiteArtifactStore | None = None
    try:
        if mode is ReferenceValidationMode.STORE:
            if database is None:
                raise ValueError(
                    "RAPTOR.REFERENCE.RESOLVER_REQUIRED: store mode requires --database"
                )
            database_path, _ = repository_path(
                repository_root, database, must_exist=True
            )
            store = SQLiteArtifactStore(database_path)
            # Existing stores are opened read-only at the operation boundary.
        resolver = (
            _Resolver(documents, store)
            if mode is ReferenceValidationMode.STORE
            else None
        )
        if len(documents) == 1 and mode is not ReferenceValidationMode.BATCH:
            validate_document(documents[0], reference_mode=mode, resolver=resolver)
        else:
            validate_documents(documents, reference_mode=mode, resolver=resolver)
    finally:
        if store:
            store.close()


def validate_json(
    repository_root: Path,
    input_path: str,
    *,
    reference_mode: str = "structural",
    database: str | None = None,
) -> dict[str, Any]:
    documents = _json_documents(repository_root, input_path)
    _validate_references(repository_root, documents, reference_mode, database)
    return {"diagnostics": [], "document_count": len(documents)}


def import_sqlite(
    repository_root: Path,
    input_path: str,
    database: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    documents = _json_documents(repository_root, input_path)
    destination, relative = repository_path(repository_root, database)
    # Exercise the complete write against an isolated clone before touching the
    # requested resource. The real write remains one A2-managed transaction.
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory) / "validation.sqlite"
        if destination.exists():
            shutil.copy2(destination, staged)
        store = SQLiteArtifactStore(staged)
        try:
            store.initialize()
            store.put_documents(documents)
        finally:
            store.close()
    if apply:
        store = SQLiteArtifactStore(destination)
        try:
            store.initialize()
            store.put_documents(documents)
        finally:
            store.close()
    return {"applied": apply, "database": relative, "document_count": len(documents)}


def export_sqlite(
    repository_root: Path,
    database: str,
    repository_id: str,
    document_id: str,
    output_path: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    source, _ = repository_path(repository_root, database, must_exist=True)
    store = SQLiteArtifactStore(source)
    try:
        document = store.get_document(
            DocumentKey(repository_id=repository_id, document_id=document_id)
        )
    finally:
        store.close()
    canonical = dump_canonical_json(document)
    if output_path == "-":
        return {"applied": False, "canonical_json": canonical}
    destination, relative = repository_path(repository_root, output_path)
    if apply:
        _atomic_text(destination, canonical)
    return {"applied": apply, "output": relative}


def validate_sqlite(repository_root: Path, database: str) -> dict[str, Any]:
    path, relative = repository_path(repository_root, database, must_exist=True)
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError(
                "RAPTOR.STORAGE.INTEGRITY_CONFLICT: integrity check failed"
            )
        keys = connection.execute(
            "SELECT repository_id, document_id FROM source_documents ORDER BY repository_id, document_id"
        ).fetchall()
    finally:
        connection.close()
    store = SQLiteArtifactStore(path)
    try:
        for repository_id, document_id in keys:
            store.get_document(
                DocumentKey(repository_id=repository_id, document_id=document_id)
            )
    finally:
        store.close()
    return {"diagnostics": [], "database": relative, "document_count": len(keys)}


__all__ = [
    "export_sqlite",
    "import_sqlite",
    "markdown_to_json",
    "repository_path",
    "validate_json",
    "validate_markdown",
    "validate_sqlite",
]
