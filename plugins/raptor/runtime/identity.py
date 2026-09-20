from __future__ import annotations

import json
from pathlib import Path

from raptor_schema import (
    IdentityDocument,
    IdentityManifest,
    validate_identity_registration,
)

from .io import atomic_repository_bytes, read_repository_bytes

IDENTITY_RELATIVE = ".raptor/identity.json"


class IdentityResolutionError(ValueError):
    code = "RAPTOR.IDENTITY.MISSING"

    def __init__(
        self,
        *,
        repository_id: str = "<repository-id>",
        document_id: str = "<document-id>",
        repository_path: str = "<repository-path>",
    ) -> None:
        self.suggested_action = (
            "python plugins/raptor/scripts/identity.py register "
            "--repo-root <repo-root> "
            f"--repository-id {repository_id} "
            f"--document-id {document_id} "
            f"--path {repository_path} --apply"
        )
        super().__init__(
            f"{self.code}: explicit repository, document, and path registration is required"
        )


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


def load_identity(
    repository_root: Path, *, repository_path: str = "<repository-path>"
) -> IdentityManifest:
    path = identity_path(repository_root)
    if not path.is_file():
        raise IdentityResolutionError(repository_path=repository_path)
    return IdentityManifest.model_validate_json(
        read_repository_bytes(repository_root.resolve(), IDENTITY_RELATIVE)
    )


def register_identity(
    repository_root: Path,
    *,
    repository_id: str,
    document_id: str,
    repository_path: str,
    registered_repository_id: str | None = None,
    apply: bool = False,
) -> dict[str, object]:
    root = repository_root.resolve()
    if not root.is_dir():
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: repository root does not exist")
    if (
        registered_repository_id is not None
        and registered_repository_id != repository_id
    ):
        raise ValueError(
            "RAPTOR.IDENTITY.REUSE: registered repository ownership does not match"
        )
    path = identity_path(root)
    current: IdentityManifest | None = None
    if path.exists():
        current = IdentityManifest.model_validate_json(
            read_repository_bytes(root, IDENTITY_RELATIVE)
        )
        proposed = validate_identity_registration(
            current,
            repository_id=repository_id,
            document_id=document_id,
            path=repository_path,
            registered_repository_id=registered_repository_id,
        )
    else:
        proposed = IdentityManifest(
            identity_version="1.0.0",
            repository_id=repository_id,
            documents={document_id: IdentityDocument(path=repository_path)},
        )
    changed = current is None or proposed != current
    if apply and changed:
        atomic_repository_bytes(
            root,
            IDENTITY_RELATIVE,
            (
                json.dumps(proposed.model_dump(mode="json"), sort_keys=True, indent=2)
                + "\n"
            ).encode(),
        )
    return {
        "applied": bool(apply and changed),
        "changed": changed,
        "manifest": proposed.model_dump(mode="json"),
    }


def document_identity(repository_root: Path, repository_path: str) -> tuple[str, str]:
    manifest = load_identity(repository_root, repository_path=repository_path)
    matches = [
        document_id
        for document_id, document in manifest.documents.items()
        if document.path == repository_path
    ]
    if not matches:
        raise IdentityResolutionError(
            repository_id=manifest.repository_id,
            repository_path=repository_path,
        )
    return manifest.repository_id, matches[0]


__all__ = [
    "document_identity",
    "IdentityResolutionError",
    "identity_path",
    "load_identity",
    "register_identity",
]
