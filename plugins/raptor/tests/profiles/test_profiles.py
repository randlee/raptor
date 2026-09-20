from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest
from raptor_schema import (
    ComparableDocument,
    ParsedDocument,
    ParsedSection,
    ProfileDescriptor,
    SourceInput,
    SourceProfile,
)

from runtime.profiles import RaptorMarkdownProfile, resolve_profile
from runtime import profiles as profile_runtime
from runtime.identity import register_identity
from runtime.operations import validate_markdown


def _external(root: Path, source: str, *, version: str = "1.0.0") -> Path:
    directory = root / ".raptor/profiles/consumer" / version
    directory.mkdir(parents=True)
    module = directory / "implementation.json"
    module.write_text(source)
    descriptor = {
        "profile_id": "consumer",
        "profile_version": version,
        "api_version": "1",
        "entrypoint": "implementation.json:raptor-markdown",
        "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
    }
    (directory / "profile.json").write_text(json.dumps(descriptor))
    return directory


GOOD = json.dumps(
    {
        "kind": "raptor-markdown-profile",
        "profile_id": "consumer",
        "profile_version": "1.0.0",
    }
)


def test_builtin_implements_a1_boundary_without_redefinition(tmp_path: Path) -> None:
    profile: SourceProfile = RaptorMarkdownProfile()
    assert profile.profile_id == "raptor"
    text = (Path(__file__).parents[2] / "runtime/profiles.py").read_text()
    boundaries = (
        SourceInput,
        ParsedSection,
        ParsedDocument,
        ComparableDocument,
        ProfileDescriptor,
    )
    for boundary in boundaries:
        assert f"class {boundary.__name__}" not in text
    tree = ast.parse(text)
    imported = {
        item.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "raptor_schema.profiles"
        for item in node.names
    }
    assert {item.__name__ for item in boundaries} | {"SourceProfile"} <= imported


def test_external_profile_requires_trust_and_resolves_compatible_version(
    tmp_path: Path,
) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    _external(root, GOOD)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.UNTRUSTED"):
        resolve_profile(root, "consumer")
    profile = resolve_profile(root, "consumer", "1.x", allow_profile_code=True)
    assert profile.profile_version == "1.0.0"
    (root / "docs").mkdir()
    (root / "docs/source.md").write_text(
        "### REQ-RAP-001 — Requirement\nStatement.\nAcceptance: accepted.\n"
    )
    register_identity(
        root,
        repository_id="urn:raptor:repo:consumer",
        document_id="DOC-RAP-001",
        repository_path="docs/source.md",
        apply=True,
    )
    assert (
        validate_markdown(
            root,
            "docs/source.md",
            profile_id="consumer",
            allow_profile_code=True,
        )["diagnostics"]
        == []
    )
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.VERSION"):
        resolve_profile(root, "consumer", "2.x", allow_profile_code=True)
    assert resolve_profile(root, "raptor").profile_id == "raptor"


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda value: value.update(api_version="2"), "API"),
        (lambda value: value.update(entrypoint="../escape.py:Profile"), "ENTRYPOINT"),
        (lambda value: value.update(module_sha256="0" * 64), "HASH"),
    ],
)
def test_descriptor_api_entrypoint_and_hash_fail_closed(
    tmp_path: Path, mutation: object, code: str
) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    directory = _external(root, GOOD)
    path = directory / "profile.json"
    value = json.loads(path.read_text())
    mutation(value)  # type: ignore[operator]
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match=f"RAPTOR.PROFILE.{code}"):
        resolve_profile(root, "consumer", allow_profile_code=True)


@pytest.mark.parametrize(
    "source",
    [
        "import importlib; importlib.import_module('socket')",
        "import smtplib; smtplib.SMTP('example.test')",
        "import subprocess; subprocess.run(['true'])",
    ],
)
def test_symlink_and_executable_profiles_are_rejected(
    tmp_path: Path, source: str
) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    directory = _external(root, GOOD)
    module = directory / "implementation.json"
    real = directory / "real.py"
    module.rename(real)
    module.symlink_to(real.name)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.ENTRYPOINT"):
        resolve_profile(root, "consumer", allow_profile_code=True)
    root2 = tmp_path / "executable"
    root2.mkdir()
    _external(root2, source)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.NETWORK"):
        resolve_profile(root2, "consumer", allow_profile_code=True)


def test_duplicate_profile_version_is_ambiguous(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    first = _external(root, GOOD)
    second = first.parent / "duplicate"
    second.mkdir()
    (second / "implementation.json").write_bytes(
        (first / "implementation.json").read_bytes()
    )
    (second / "profile.json").write_bytes((first / "profile.json").read_bytes())
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.AMBIGUOUS"):
        resolve_profile(root, "consumer", allow_profile_code=True)


def test_profile_root_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    outside = tmp_path / "profiles"
    (root / ".raptor").mkdir(parents=True)
    outside.mkdir()
    (root / ".raptor/profiles").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.ENTRYPOINT"):
        resolve_profile(root, "consumer", allow_profile_code=True)


def test_verified_declaration_bytes_are_not_reopened_by_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    directory = _external(root, GOOD)
    original = profile_runtime.read_repository_bytes

    def swap_after_open(repository_root: Path, relative: str) -> bytes:
        value = original(repository_root, relative)
        if relative.endswith("implementation.json"):
            (directory / "implementation.json").write_text("import subprocess")
        return value

    monkeypatch.setattr(profile_runtime, "read_repository_bytes", swap_after_open)
    profile = resolve_profile(root, "consumer", allow_profile_code=True)
    assert profile.profile_id == "consumer"


def test_invalid_profile_contract_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    _external(root, json.dumps({"kind": "other"}))
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.NETWORK"):
        resolve_profile(root, "consumer", allow_profile_code=True)


def test_identity_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / ".raptor").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="RAPTOR.PATH.OUTSIDE_ROOT"):
        register_identity(
            root,
            repository_id="urn:raptor:repo:consumer",
            document_id="DOC-RAP-001",
            repository_path="docs/source.md",
        )
