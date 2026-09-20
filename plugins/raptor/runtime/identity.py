from __future__ import annotations

from pathlib import Path

from raptor_schema import (
    IdentityDocument,
    IdentityManifest,
    validate_identity_registration,
)

from .io import atomic_json


def identity_path(repository_root: Path) -> Path:
    root = repository_root.resolve()
    directory = root / ".raptor"
    if directory.exists():
        try:
            directory.resolve().relative_to(root)
        except ValueError as error:
            raise ValueError(
                "RAPTOR.PATH.OUTSIDE_ROOT: identity path escapes repository root"
            ) from error
        if directory.is_symlink():
            raise ValueError(
                "RAPTOR.PATH.OUTSIDE_ROOT: identity directory may not be a symlink"
            )
    path = directory / "identity.json"
    if path.is_symlink():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: identity file may not be a symlink")
    return path


def load_identity(repository_root: Path) -> IdentityManifest:
    path = identity_path(repository_root)
    if not path.is_file():
        raise ValueError(
            "RAPTOR.IDENTITY.MISSING: run `raptor identity register` with explicit repository, document, and path values"
        )
    return IdentityManifest.model_validate_json(path.read_text(encoding="utf-8"))


def register_identity(
    repository_root: Path,
    *,
    repository_id: str,
    document_id: str,
    repository_path: str,
    apply: bool = False,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: repository root does not exist")
    path = identity_path(root)
    current: IdentityManifest | None = None
    if path.exists():
        current = IdentityManifest.model_validate_json(path.read_text(encoding="utf-8"))
        proposed = validate_identity_registration(
            current,
            repository_id=repository_id,
            document_id=document_id,
            path=repository_path,
        )
    else:
        proposed = IdentityManifest(
            identity_version="1.0.0",
            repository_id=repository_id,
            documents={document_id: IdentityDocument(path=repository_path)},
        )
    changed = current is None or proposed != current
    if apply and changed:
        atomic_json(path, proposed.model_dump(mode="json"), indent=2)
    return {
        "applied": bool(apply and changed),
        "changed": changed,
        "manifest": proposed.model_dump(mode="json"),
    }


def document_identity(repository_root: Path, repository_path: str) -> tuple[str, str]:
    manifest = load_identity(repository_root)
    matches = [
        document_id
        for document_id, document in manifest.documents.items()
        if document.path == repository_path
    ]
    if not matches:
        raise ValueError(
            "RAPTOR.IDENTITY.MISSING: register the Markdown path before validation or import"
        )
    return manifest.repository_id, matches[0]


__all__ = [
    "document_identity",
    "identity_path",
    "load_identity",
    "register_identity",
]
