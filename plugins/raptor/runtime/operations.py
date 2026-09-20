from __future__ import annotations

import tempfile
from contextlib import contextmanager
from collections.abc import Iterator
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
from .io import atomic_repository_bytes, read_repository_bytes, repository_parts
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
    relative = PurePosixPath(*repository_parts(raw))
    candidate = root.joinpath(*relative.parts)
    if any(
        item.is_symlink()
        for item in (candidate, *candidate.parents)
        if item != root.parent
    ):
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: symlinks are not allowed")
    if must_exist and not candidate.exists():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: input does not exist")
    return candidate, relative.as_posix()


def _markdown_sources(
    repository_root: Path,
    input_path: str,
    *,
    profile_id: str,
    profile_version: str | None,
    allow_profile_code: bool,
) -> tuple[tuple[SourceDocument, ...], bool]:
    source_path, _ = repository_path(repository_root, input_path, must_exist=True)
    is_directory = source_path.is_dir()
    paths = tuple(sorted(source_path.rglob("*.md"))) if is_directory else (source_path,)
    if not paths:
        raise ValueError("RAPTOR.OPERATION.EMPTY_INPUT: no Markdown documents found")
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
            content=read_repository_bytes(root, relative),
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
    return tuple(documents), is_directory


def _markdown_reference_mode(is_directory: bool, requested: str | None) -> str:
    expected = "batch" if is_directory else "document"
    selected = requested or expected
    if selected != expected:
        kind = "directories" if is_directory else "single Markdown files"
        raise ValueError(
            f"RAPTOR.REFERENCE.MODE_MISMATCH: {kind} require {expected} mode"
        )
    return selected


def validate_markdown(
    repository_root: Path,
    input_path: str,
    *,
    profile_id: str = "raptor",
    profile_version: str | None = None,
    reference_mode: str | None = None,
    database: str | None = None,
    allow_profile_code: bool = False,
) -> dict[str, Any]:
    documents, is_directory = _markdown_sources(
        repository_root,
        input_path,
        profile_id=profile_id,
        profile_version=profile_version,
        allow_profile_code=allow_profile_code,
    )
    selected_mode = _markdown_reference_mode(is_directory, reference_mode)
    _validate_references(repository_root, documents, selected_mode, database)
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
    reference_mode: str | None = None,
    database: str | None = None,
    allow_profile_code: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    documents, is_directory = _markdown_sources(
        repository_root,
        input_path,
        profile_id=profile_id,
        profile_version=profile_version,
        allow_profile_code=allow_profile_code,
    )
    selected_mode = _markdown_reference_mode(is_directory, reference_mode)
    _validate_references(repository_root, documents, selected_mode, database)
    canonical = dump_canonical_json(documents[0]) if len(documents) == 1 else None
    if output_path == "-":
        if canonical is None:
            raise ValueError(
                "RAPTOR.OPERATION.CARDINALITY: directory import requires an output directory"
            )
        return {"applied": False, "canonical_json": canonical}
    _, relative = repository_path(repository_root, output_path)
    outputs = (
        [(relative, documents[0], canonical)]
        if canonical is not None
        else [
            (
                f"{relative}/{item.provenance.origin.document_id}.json",
                item,
                dump_canonical_json(item),
            )
            for item in documents
        ]
    )
    if apply:
        for target, _, body in outputs:
            atomic_repository_bytes(repository_root.resolve(), target, body.encode())
    result: dict[str, Any] = {
        "applied": apply,
        "outputs": [target for target, _, _ in outputs],
        "documents": [
            {
                "repository_id": item.provenance.origin.repository_id,
                "document_id": item.provenance.origin.document_id,
            }
            for _, item, _ in outputs
        ],
    }
    if len(outputs) == 1:
        target, item, _ = outputs[0]
        result.update(
            output=target,
            document={
                "repository_id": item.provenance.origin.repository_id,
                "document_id": item.provenance.origin.document_id,
            },
        )
    return result


def _json_documents(
    repository_root: Path, input_path: str
) -> tuple[SourceDocument, ...]:
    path, _ = repository_path(repository_root, input_path, must_exist=True)
    paths = tuple(sorted(path.rglob("*.json"))) if path.is_dir() else (path,)
    if not paths:
        raise ValueError("RAPTOR.OPERATION.EMPTY_INPUT: no JSON documents found")
    root = repository_root.resolve()
    return tuple(
        load_canonical_json(
            read_repository_bytes(root, item.relative_to(root).as_posix())
        )
        for item in paths
    )


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


@contextmanager
def _read_only_store(
    repository_root: Path, database: str
) -> Iterator[SQLiteArtifactStore]:
    database_path, _ = repository_path(repository_root, database, must_exist=True)
    if any(
        database_path.with_name(f"{database_path.name}{suffix}").exists()
        for suffix in ("-wal", "-journal")
    ):
        raise ValueError(
            "RAPTOR.STORAGE.READ_ONLY_SIDECAR: validation will not recover journal state"
        )
    payload = read_repository_bytes(repository_root.resolve(), database)
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory) / "store.sqlite"
        snapshot.write_bytes(payload)
        store = SQLiteArtifactStore.open_read_only(snapshot)
        try:
            store.validate()
            yield store
        finally:
            store.close()


def _validate_references(
    repository_root: Path,
    documents: tuple[SourceDocument, ...],
    mode_value: str,
    database: str | None,
) -> None:
    mode = ReferenceValidationMode(mode_value)
    if mode is ReferenceValidationMode.STORE:
        if database is None:
            raise ValueError(
                "RAPTOR.REFERENCE.RESOLVER_REQUIRED: store mode requires --database"
            )
        with _read_only_store(repository_root, database) as store:
            validate_documents(
                documents,
                reference_mode=mode,
                resolver=_Resolver(documents, store),
            )
        return
    if len(documents) == 1 and mode is not ReferenceValidationMode.BATCH:
        validate_document(documents[0], reference_mode=mode)
    else:
        validate_documents(documents, reference_mode=mode)


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
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory) / "staged.sqlite"
        if destination.exists():
            staged.write_bytes(
                read_repository_bytes(repository_root.resolve(), relative)
            )
        store = SQLiteArtifactStore(staged)
        try:
            store.initialize()
            store.put_documents(documents)
        finally:
            store.close()
        if apply:
            atomic_repository_bytes(
                repository_root.resolve(), relative, staged.read_bytes()
            )
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
    repository_path(repository_root, database, must_exist=True)
    with _read_only_store(repository_root, database) as store:
        document = store.get_document(
            DocumentKey(repository_id=repository_id, document_id=document_id)
        )
    canonical = dump_canonical_json(document)
    if output_path == "-":
        return {"applied": False, "canonical_json": canonical}
    _, relative = repository_path(repository_root, output_path)
    if apply:
        atomic_repository_bytes(repository_root.resolve(), relative, canonical.encode())
    return {"applied": apply, "output": relative}


def validate_sqlite(repository_root: Path, database: str) -> dict[str, Any]:
    _, relative = repository_path(repository_root, database, must_exist=True)
    with _read_only_store(repository_root, database) as store:
        keys = store.list_document_keys()
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
