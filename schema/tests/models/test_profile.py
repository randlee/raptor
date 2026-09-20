from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

import pytest

from raptor_schema import (
    ParsedDocument,
    ProfileError,
    SourceInput,
    canonicalize_with_profile,
    load_profile,
    parse_with_profile,
    resolve_profile_descriptor,
    validate_with_profile,
)


MODULE = '''
class Profile:
    profile_id = "sample"
    profile_version = "1.2.0"
    def parse(self, source): return source
    def validate(self, parsed): return []
    def canonicalize(self, parsed): return parsed
    def project_render_input(self, document): return {}
    def normalize(self, document): return document
'''.lstrip()


def write_profile(root: Path, version: str = "1.2.0", *, api: str = "1", content: str = MODULE) -> Path:
    directory = root / version
    directory.mkdir(parents=True)
    module = directory / "profile.py"
    module.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode()).hexdigest()
    descriptor = directory / "profile.toml"
    descriptor.write_text(
        f'profile_id = "sample"\nprofile_version = "{version}"\napi_version = "{api}"\nentrypoint = "profile.py:Profile"\nmodule_sha256 = "{digest}"\n',
        encoding="utf-8",
    )
    return descriptor


def test_profile_precedence_version_and_loading(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = repo / ".raptor/profiles/sample"
    write_profile(local, "1.1.0", content=MODULE.replace('1.2.0', '1.1.0'))
    selected = write_profile(local, "1.2.0")
    resolved = resolve_profile_descriptor("sample", "1.x", repo_root=repo, allow_profile_code=True)
    assert resolved.descriptor_path == selected.resolve()
    assert load_profile(resolved).profile_version == "1.2.0"
    exact = resolve_profile_descriptor("sample", "1.1.0", repo_root=repo, allow_profile_code=True)
    assert exact.descriptor.profile_version == "1.1.0"


def test_explicit_precedence_and_trust(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = repo / ".raptor/profiles/sample"
    write_profile(local, "1.1.0", content=MODULE.replace('1.2.0', '1.1.0'))
    external = write_profile(tmp_path / "consumer-profile")
    with pytest.raises(ProfileError) as caught:
        resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, explicit_descriptor=external)
    assert caught.value.code == "RAPTOR.PROFILE.UNTRUSTED"
    resolved = resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, explicit_descriptor=external, allow_profile_code=True)
    assert resolved.source == "explicit"


def test_profile_failures(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = repo / ".raptor/profiles/sample"
    descriptor = write_profile(local)
    with pytest.raises(ProfileError) as version:
        resolve_profile_descriptor("sample", "2.x", repo_root=repo, allow_profile_code=True)
    assert version.value.code == "RAPTOR.PROFILE.VERSION"
    descriptor.write_text(descriptor.read_text().replace('api_version = "1"', 'api_version = "2"'))
    with pytest.raises(ProfileError) as api:
        resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, allow_profile_code=True)
    assert api.value.code == "RAPTOR.PROFILE.API"
    descriptor.write_text(descriptor.read_text().replace('api_version = "2"', 'api_version = "1"').replace('profile.py:Profile', 'broken'))
    with pytest.raises(ProfileError) as entrypoint:
        resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, allow_profile_code=True)
    assert entrypoint.value.code == "RAPTOR.PROFILE.ENTRYPOINT"


def test_profile_entrypoint_symbol_mismatch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    descriptor = write_profile(repo / ".raptor/profiles/sample")
    descriptor.write_text(descriptor.read_text().replace("profile.py:Profile", "profile.py:Missing"))
    resolved = resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, allow_profile_code=True)
    with pytest.raises(ProfileError) as caught:
        load_profile(resolved)
    assert caught.value.code == "RAPTOR.PROFILE.ENTRYPOINT"


def test_profile_hash_ambiguity_and_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    local = repo / ".raptor/profiles/sample"
    descriptor = write_profile(local)
    descriptor.write_text(descriptor.read_text().replace("0" * 0 + hashlib.sha256(MODULE.encode()).hexdigest(), "0" * 64))
    with pytest.raises(ProfileError) as hashed:
        resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, allow_profile_code=True)
    assert hashed.value.code == "RAPTOR.PROFILE.HASH"
    descriptor.unlink()
    write_profile(local / "duplicate-a")
    write_profile(local / "duplicate-b")
    with pytest.raises(ProfileError) as ambiguous:
        resolve_profile_descriptor("sample", "1.2.0", repo_root=repo, allow_profile_code=True)
    assert ambiguous.value.code == "RAPTOR.PROFILE.AMBIGUOUS"

    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    repo.mkdir(exist_ok=True)
    link = repo / "link.md"
    link.symlink_to(outside)
    with pytest.raises(ProfileError) as escaped:
        SourceInput(
            repo_root=repo,
            repository_id="urn:raptor:repo:raptor",
            document_id="DOC-RAP-001",
            repository_path=PurePosixPath("link.md"),
            content=b"outside",
        )
    assert escaped.value.code == "RAPTOR.PATH.OUTSIDE_ROOT"


def test_profile_operation_error_contract(tmp_path: Path) -> None:
    class Broken:
        def parse(self, source: SourceInput) -> object:
            return object()

        def validate(self, parsed: ParsedDocument) -> object:
            return object()

        def canonicalize(self, parsed: ParsedDocument) -> object:
            raise RuntimeError("secret implementation detail")

    repo = tmp_path / "repo"
    repo.mkdir()
    source = SourceInput(
        repo_root=repo,
        repository_id="urn:raptor:repo:raptor",
        document_id="DOC-RAP-001",
        repository_path=PurePosixPath("source.md"),
        content=b"source",
    )
    profile = Broken()  # type: ignore[assignment]
    with pytest.raises(ProfileError) as returned:
        parse_with_profile(profile, source)
    assert returned.value.code == "RAPTOR.PROFILE.RETURN_TYPE"
    parsed = ParsedDocument(source=source, frontmatter={}, sections=())
    with pytest.raises(ProfileError) as validated:
        validate_with_profile(profile, parsed)
    assert validated.value.code == "RAPTOR.PROFILE.RETURN_TYPE"
    with pytest.raises(ProfileError) as canonicalized:
        canonicalize_with_profile(profile, parsed)
    assert canonicalized.value.code == "RAPTOR.PROFILE.CANONICALIZE"
    assert "secret" not in str(canonicalized.value)
