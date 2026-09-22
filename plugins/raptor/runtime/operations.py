from __future__ import annotations

import hashlib
import os
import tempfile
import tomllib
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel

from raptor_schema import (
    DocumentKey,
    Diagnostic,
    IdentityManifest,
    IngressDiagnostic,
    IngressReport,
    IngressReportEntry,
    ProfileSelection,
    RepositoryConfigManifest,
    RepositoryRoutingConfig,
    RepositoryScanConfig,
    SQLiteArtifactStore,
    SourceDocument,
    SourceRoute,
    dump_canonical_json,
    load_canonical_json,
    validate_repository_manifest_identity,
    validate_source_routing,
)
from raptor_schema.canonical import dump_canonical_fragment
from raptor_schema.profiles import ParsedDocument, SourceInput

from .identity import document_identity
from .io import atomic_repository_bytes, read_repository_bytes, repository_parts
from .profiles import resolve_profile

_MANIFEST_PATH = ".raptor/raptor.toml"


def _fragment_sha256(value: BaseModel) -> str:
    return hashlib.sha256(dump_canonical_fragment(value).encode()).hexdigest()


def _document_sha256(document: SourceDocument) -> str:
    return hashlib.sha256(dump_canonical_json(document).encode()).hexdigest()


def _report_bytes(report: IngressReport) -> bytes:
    return (dump_canonical_fragment(report) + "\n").encode("utf-8")


def _load_toml(repository_root: Path, relative: str) -> dict[str, object]:
    try:
        value = tomllib.loads(read_repository_bytes(repository_root, relative).decode())
    except Exception as error:
        raise ValueError(f"RAPTOR.CONFIG.LOAD: cannot read {relative}") from error
    if not isinstance(value, dict):
        raise ValueError(f"RAPTOR.CONFIG.LOAD: {relative} must be a TOML table")
    return value


def _configured_ingress(
    repository_root: Path, config_path: str
) -> tuple[RepositoryConfigManifest, RepositoryScanConfig, tuple[SourceRoute, ...], IdentityManifest]:
    _, config_relative = repository_path(repository_root, config_path, must_exist=True)
    if config_relative != _MANIFEST_PATH:
        raise ValueError("RAPTOR.CONFIG.MANIFEST: config must be .raptor/raptor.toml")
    try:
        manifest = RepositoryConfigManifest.model_validate(
            _load_toml(repository_root, config_relative)
        )
        scan = RepositoryScanConfig.model_validate(
            _load_toml(repository_root, f".raptor/{manifest.files.scan}")
        )
        routing = RepositoryRoutingConfig.model_validate(
            _load_toml(repository_root, f".raptor/{manifest.files.routing}")
        )
        identity = IdentityManifest.model_validate_json(
            read_repository_bytes(repository_root, f".raptor/{manifest.files.identity}")
        )
        validate_repository_manifest_identity(manifest, identity)
        routes = validate_source_routing(scan, routing)
    except ValueError as error:
        if str(error).startswith("RAPTOR."):
            raise
        raise ValueError("RAPTOR.CONFIG.VALIDATION: invalid configured ingress") from error
    return manifest, scan, routes, identity


def _authorized_inventory(
    repository_root: Path, scan: RepositoryScanConfig
) -> tuple[tuple[str, str], ...]:
    selected: list[tuple[str, str]] = []
    root = repository_root.resolve()
    for source in scan.sources:
        directory, _ = repository_path(repository_root, source.root, must_exist=True)
        if not directory.is_dir():
            raise ValueError(
                f"RAPTOR.CONFIG.SOURCE_ROOT: configured source root is not a directory: {source.root}"
            )
        for parent, directories, files in os.walk(directory, followlinks=False):
            directories.sort()
            files.sort()
            for name in files:
                candidate = Path(parent) / name
                relative = candidate.relative_to(root).as_posix()
                matching = scan.matching_source(relative)
                if matching is not None and matching.name == source.name:
                    selected.append((relative, source.name))
    selected.sort()
    if len({path for path, _ in selected}) != len(selected):
        raise ValueError("RAPTOR.CONFIG.INVENTORY: authorized paths must be unique")
    return tuple(selected)


def _canonicalize_source(profile: Any, source: SourceInput) -> SourceDocument:
    try:
        parsed = profile.parse(source)
    except Exception as error:
        raise ValueError("RAPTOR.PROFILE.PARSE: profile parse failed") from error
    if not isinstance(parsed, ParsedDocument):
        raise ValueError("RAPTOR.PROFILE.RETURN_TYPE: parse returned an invalid value")
    try:
        diagnostics = profile.validate(parsed)
    except Exception as error:
        raise ValueError("RAPTOR.PROFILE.VALIDATION: profile validation failed") from error
    if not isinstance(diagnostics, list) or any(
        not isinstance(item, Diagnostic) for item in diagnostics
    ):
        raise ValueError("RAPTOR.PROFILE.RETURN_TYPE: validate returned an invalid value")
    if diagnostics:
        raise ValueError(f"RAPTOR.PROFILE.VALIDATION: {diagnostics[0].code}")
    try:
        document = profile.canonicalize(parsed)
    except Exception as error:
        raise ValueError("RAPTOR.PROFILE.CANONICALIZE: canonical conversion failed") from error
    if not isinstance(document, SourceDocument):
        raise ValueError(
            "RAPTOR.PROFILE.RETURN_TYPE: canonicalize returned an invalid value"
        )
    return document


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
        documents.append(_canonicalize_source(profile, source))
    return tuple(documents), is_directory


def _markdown_reference_mode(is_directory: bool, requested: str | None) -> str:
    """Relationships are emitted raw and resolved by the SQLite projection."""
    del is_directory
    if requested not in {None, "structural", "document", "batch", "store"}:
        raise ValueError("RAPTOR.REFERENCE.MODE_MISMATCH: unsupported mode")
    return "emitted"


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
    del repository_root, documents, mode_value, database


def _field_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_field_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_field_count(item) for item in value)
    return 1


def _canonical_reference_count(document: SourceDocument) -> int:
    return sum(len(artifact.relationships) for artifact in document.artifacts)


def _ingress_diagnostic(error: Exception) -> IngressDiagnostic:
    code = str(error).split(":", 1)[0]
    if not code.startswith("RAPTOR."):
        code = "RAPTOR.INGRESS.ERROR"
    return IngressDiagnostic(code=code, message="configured ingress did not import this path")


def _diagnosed_entry(
    repository_path_value: str,
    route: SourceRoute,
    error: Exception,
    *,
    document_id: str | None = None,
) -> IngressReportEntry:
    return IngressReportEntry(
        repository_path=repository_path_value,
        outcome="diagnosed",
        document_id=document_id,
        route=route.source,
        profile=route.profile,
        sqlite_outcome="not_attempted",
        diagnostic=_ingress_diagnostic(error),
    )


def _persist_documents(
    repository_root: Path,
    documents: tuple[SourceDocument, ...],
    database: str,
    *,
    apply: bool,
) -> tuple[str, Literal["persisted", "validated"]]:
    destination, relative = repository_path(repository_root, database)
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory) / "staged.sqlite"
        if destination.exists():
            staged.write_bytes(read_repository_bytes(repository_root.resolve(), relative))
        store = SQLiteArtifactStore(staged)
        try:
            store.initialize()
            store.put_documents(documents)
        finally:
            store.close()
        if apply:
            atomic_repository_bytes(repository_root.resolve(), relative, staged.read_bytes())
    return relative, "persisted" if apply else "validated"


def configured_markdown_to_sqlite(
    repository_root: Path,
    config_path: str,
    database: str,
    report_path: str,
    *,
    allow_profile_code: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: repository root does not exist")
    manifest, scan, routes, identity = _configured_ingress(root, config_path)
    _, database_relative = repository_path(root, database)
    _, report_relative = repository_path(root, report_path)
    if database_relative == report_relative:
        raise ValueError("RAPTOR.INGRESS.REPORT_PATH: report and database paths differ")
    routes_by_source = {route.source: route for route in routes}
    identities_by_path = {
        document.path: document_id for document_id, document in identity.documents.items()
    }
    entries: dict[str, IngressReportEntry] = {}
    staged: list[tuple[str, SourceRoute, SourceDocument]] = []
    for relative, source_name in _authorized_inventory(root, scan):
        route = routes_by_source[source_name]
        document_id = identities_by_path.get(relative)
        if document_id is None:
            entries[relative] = _diagnosed_entry(
                relative,
                route,
                ValueError("RAPTOR.IDENTITY.MISSING: selected path is not registered"),
            )
            continue
        try:
            profile = resolve_profile(
                root,
                route.profile.profile_id,
                route.profile.profile_version,
                allow_profile_code=allow_profile_code,
            )
            document = _canonicalize_source(
                profile,
                SourceInput(
                    repo_root=root,
                    repository_id=manifest.repository_id,
                    document_id=document_id,
                    repository_path=PurePosixPath(relative),
                    content=read_repository_bytes(root, relative),
                    routed_artifact_type=(
                        route.artifact_types[0]
                        if len(route.artifact_types) == 1
                        else None
                    ),
                ),
            )
            if any(artifact.artifact_type not in route.artifact_types for artifact in document.artifacts):
                raise ValueError("RAPTOR.INGRESS.ARTIFACT_TYPE: artifact is outside route allowlist")
        except Exception as error:
            entries[relative] = _diagnosed_entry(
                relative, route, error, document_id=document_id
            )
            continue
        staged.append((relative, route, document))
    if not entries and staged:
        try:
            _validate_references(root, tuple(item[2] for item in staged), "batch", None)
        except Exception as error:
            affected = getattr(getattr(error, "document_key", None), "document_id", None)
            for relative, route, document in staged:
                if affected is None or document.provenance.origin.document_id == affected:
                    entries[relative] = _diagnosed_entry(
                        relative,
                        route,
                        error,
                        document_id=document.provenance.origin.document_id,
                    )
    if entries:
        for relative, route, document in staged:
            entries.setdefault(
                relative,
                _diagnosed_entry(
                    relative,
                    route,
                    ValueError("RAPTOR.INGRESS.BATCH_ABORTED: another selected path failed"),
                    document_id=document.provenance.origin.document_id,
                ),
            )
        sqlite_outcome = "not_attempted"
    else:
        try:
            _, sqlite_outcome = _persist_documents(
                root, tuple(item[2] for item in staged), database_relative, apply=apply
            )
        except Exception as error:
            for relative, route, document in staged:
                entries[relative] = _diagnosed_entry(
                    relative,
                    route,
                    error,
                    document_id=document.provenance.origin.document_id,
                )
        else:
            for relative, route, document in staged:
                entries[relative] = IngressReportEntry(
                    repository_path=relative,
                    outcome="imported",
                    document_id=document.provenance.origin.document_id,
                    route=route.source,
                    profile=route.profile,
                    canonical_digest=_document_sha256(document),
                    sqlite_outcome=sqlite_outcome,
                    field_count=_field_count(
                        document.model_dump(mode="json", exclude_none=True)
                    ),
                    relationship_count=_canonical_reference_count(document),
                    origin_digest=_fragment_sha256(document.provenance.origin),
                    materialization_digest=_fragment_sha256(document.provenance.materialization),
                )
    report = IngressReport(
        report_version="1.0.0",
        repository_id=manifest.repository_id,
        config_path=_MANIFEST_PATH,
        database_path=database_relative,
        entries=tuple(entries[path] for path in sorted(entries)),
    )
    if apply:
        atomic_repository_bytes(root, report_relative, _report_bytes(report))
    return {
        "applied": apply,
        "database": database_relative,
        "report": report_relative,
        "report_data": report.model_dump(mode="json"),
    }


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
    relative, _ = _persist_documents(
        repository_root, documents, database, apply=apply
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


def sqlite_export_proof(
    repository_root: Path,
    database: str,
    repository_id: str,
    document_id: str,
    output_path: str,
    report_path: str,
    *,
    profile_id: str = "raptor",
    profile_version: str | None = None,
    template_set: str = "raptor",
    apply: bool = False,
) -> dict[str, Any]:
    """Prove SQLite recovery plus sc-compose rendering for one stored document."""
    from .rendering import (
        compare_semantics,
        render_markdown,
        resolve_sc_compose,
        resolve_template_set,
    )

    root = repository_root.resolve()
    _, database_relative = repository_path(root, database, must_exist=True)
    _, output_relative = repository_path(root, output_path)
    _, report_relative = repository_path(root, report_path)
    with _read_only_store(root, database_relative) as store:
        document = store.get_document(
            DocumentKey(repository_id=repository_id, document_id=document_id)
        )
        relationships = store.traceability_relationships(
            DocumentKey(repository_id=repository_id, document_id=document_id)
        )
    profile = resolve_profile(root, profile_id, profile_version)
    rendered = render_markdown(
        document,
        profile=profile,
        template_set=template_set,
        output_path=output_relative,
        repository_root=root,
        executable=resolve_sc_compose(),
    )
    comparison = compare_semantics(
        document,
        rendered.document,
        profile=profile,
        content=rendered.content,
        expected_output_path=output_relative,
        template_set=template_set,
        template_version=resolve_template_set(root, template_set).version,
    )
    if not comparison.equal:
        raise ValueError("RAPTOR.ROUND_TRIP.SEMANTIC_LOSS: " + ",".join(comparison.differences))
    entry = IngressReportEntry(
        repository_path=document.provenance.origin.initial_repository_path,
        outcome="imported",
        document_id=document.provenance.origin.document_id,
        route="sqlite-export",
        profile=ProfileSelection(
            profile_id=profile.profile_id, profile_version=profile.profile_version
        ),
        canonical_digest=_document_sha256(document),
        sqlite_outcome="validated",
        field_count=_field_count(document.model_dump(mode="json", exclude_none=True)),
        relationship_count=relationships.total_count,
        origin_digest=_fragment_sha256(document.provenance.origin),
        materialization_digest=_fragment_sha256(document.provenance.materialization),
    )
    report = IngressReport(
        report_version="1.0.0",
        repository_id=repository_id,
        config_path=".raptor/raptor.toml",
        database_path=database_relative,
        entries=(entry,),
    )
    if apply:
        atomic_repository_bytes(root, output_relative, rendered.content)
        atomic_repository_bytes(root, report_relative, _report_bytes(report))
    return {
        "applied": apply,
        "output": output_relative,
        "report": report_relative,
        "document": rendered.document.model_dump(mode="json", exclude_none=True),
        "report_data": report.model_dump(mode="json"),
    }


def validate_sqlite(repository_root: Path, database: str) -> dict[str, Any]:
    _, relative = repository_path(repository_root, database, must_exist=True)
    with _read_only_store(repository_root, database) as store:
        keys = store.list_document_keys()
    return {"diagnostics": [], "database": relative, "document_count": len(keys)}


__all__ = [
    "export_sqlite",
    "sqlite_export_proof",
    "configured_markdown_to_sqlite",
    "import_sqlite",
    "markdown_to_json",
    "repository_path",
    "validate_json",
    "validate_markdown",
    "validate_sqlite",
]
