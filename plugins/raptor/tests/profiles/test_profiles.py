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
from runtime.identity import register_identity
from runtime.operations import validate_markdown


def _external(root: Path, source: str, *, version: str = "1.0.0") -> Path:
    directory = root / ".raptor/profiles/consumer" / version
    directory.mkdir(parents=True)
    module = directory / "profile.py"
    module.write_text(source)
    descriptor = {
        "profile_id": "consumer",
        "profile_version": version,
        "api_version": "1",
        "entrypoint": "profile.py:Profile",
        "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
    }
    (directory / "profile.json").write_text(json.dumps(descriptor))
    return directory


GOOD = """from runtime.profiles import RaptorMarkdownProfile
class Profile(RaptorMarkdownProfile):
    profile_id = 'consumer'
    profile_version = '1.0.0'
"""


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


def test_symlink_and_network_capable_profile_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    directory = _external(root, GOOD)
    module = directory / "profile.py"
    real = directory / "real.py"
    module.rename(real)
    module.symlink_to(real.name)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.ENTRYPOINT"):
        resolve_profile(root, "consumer", allow_profile_code=True)
    root2 = tmp_path / "network"
    root2.mkdir()
    _external(root2, "import socket\n" + GOOD)
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.NETWORK"):
        resolve_profile(root2, "consumer", allow_profile_code=True)


def test_duplicate_profile_version_is_ambiguous(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    first = _external(root, GOOD)
    second = first.parent / "duplicate"
    second.mkdir()
    (second / "profile.py").write_bytes((first / "profile.py").read_bytes())
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


def test_invalid_profile_contract_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    root.mkdir()
    _external(
        root, "class Profile:\n profile_id='consumer'\n profile_version='1.0.0'\n"
    )
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.RETURN_TYPE"):
        resolve_profile(root, "consumer", allow_profile_code=True)


def test_invalid_profile_return_type_is_rejected_at_runtime(tmp_path: Path) -> None:
    root = tmp_path / "consumer"
    (root / "docs").mkdir(parents=True)
    (root / "docs/source.md").write_text("source")
    source = """class Profile:
 profile_id='consumer'
 profile_version='1.0.0'
 def parse(self, source): return {}
 def validate(self, parsed): return []
 def canonicalize(self, parsed): return {}
 def project_render_input(self, document): return {}
 def normalize(self, document): return {}
"""
    _external(root, source)
    register_identity(
        root,
        repository_id="urn:raptor:repo:consumer",
        document_id="DOC-RAP-001",
        repository_path="docs/source.md",
        apply=True,
    )
    with pytest.raises(ValueError, match="RAPTOR.PROFILE.RETURN_TYPE"):
        validate_markdown(
            root, "docs/source.md", profile_id="consumer", allow_profile_code=True
        )


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
