from pathlib import Path, PurePosixPath

import pytest
from raptor_schema import ArtifactType
from raptor_schema.profiles import SourceInput

from runtime.profiles import RaptorMarkdownProfile
from runtime.rendering import render_markdown


ROOT = Path(__file__).parents[4]
FIXTURES = sorted((ROOT / "plugins/raptor/tests/fixtures/reference").glob("*.md"))
_ROUTED_FAMILIES = {
    "design.md": ArtifactType.DESIGN_DOCUMENT,
    "test-plan.md": ArtifactType.TEST_PLAN,
}


@pytest.mark.parametrize("path", FIXTURES)
def test_reference_markdown_reparses_and_renders_byte_exact(path: Path) -> None:
    profile = RaptorMarkdownProfile()
    content = path.read_bytes()
    source = SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id=f"DOC-CORE-{FIXTURES.index(path) + 1:04}", repository_path=PurePosixPath(path.relative_to(ROOT).as_posix()), content=content, routed_artifact_type=_ROUTED_FAMILIES.get(path.name))
    document = profile.canonicalize(profile.parse(source))
    rendered = render_markdown(document, profile=profile, template_set="raptor", output_path=source.repository_path, repository_root=ROOT)
    assert rendered.content == content.replace(b"\r\n", b"\n").replace(b"\r", b"\n").rstrip(b"\n") + b"\n"
    reparsed = profile.canonicalize(profile.parse(SourceInput(repo_root=ROOT, repository_id=source.repository_id, document_id=source.document_id, repository_path=source.repository_path, content=rendered.content, routed_artifact_type=source.routed_artifact_type)))
    assert [item.model_dump(exclude={"source_location"}) for item in reparsed.artifacts] == [item.model_dump(exclude={"source_location"}) for item in document.artifacts]
    if path.name == "design.md":
        assert document.artifacts[0].id == source.document_id
    if path.name == "test-plan.md":
        assert document.artifacts[0].status.value == "Active"
        assert document.document_metadata["id_range"] == "TEST-CORE-0001 through TEST-CORE-0002"
