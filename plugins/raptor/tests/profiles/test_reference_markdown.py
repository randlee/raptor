from pathlib import Path, PurePosixPath

import pytest
from raptor_schema import ArtifactType
from raptor_schema.profiles import SourceInput

from runtime.profiles import RaptorMarkdownProfile


ROOT = Path(__file__).parents[4]
FIXTURES = ROOT / "plugins/raptor/tests/fixtures/reference"
_ROUTED_FAMILIES = {
    "design.md": ArtifactType.DESIGN_DOCUMENT,
    "test-plan.md": ArtifactType.TEST_PLAN,
}


def _source(path: Path) -> SourceInput:
    return SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id=f"DOC-CORE-{list(sorted(FIXTURES.glob('*.md'))).index(path) + 1:04}", repository_path=PurePosixPath(path.relative_to(ROOT).as_posix()), content=path.read_bytes(), routed_artifact_type=_ROUTED_FAMILIES.get(path.name))


def _inline(content: bytes, *, document_id: str = "DOC-CORE-0099") -> SourceInput:
    return SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id=document_id, repository_path=PurePosixPath("docs/reference.md"), content=content)


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.md")))
def test_reference_fixture_extracts(path: Path) -> None:
    document = RaptorMarkdownProfile().canonicalize(RaptorMarkdownProfile().parse(_source(path)))
    assert document.schema_version == "2.0.0"
    assert document.artifacts


def test_non_colon_item_heading_is_a_named_malformed_heading() -> None:
    source = _inline("## ADR-CORE-0001 — Not a colon\n".encode())
    with pytest.raises(ValueError, match=r"RAPTOR\.REFERENCE\.MALFORMED_HEADING: line 1"):
        RaptorMarkdownProfile().parse(source)


def test_invalid_utf8_is_a_named_failure() -> None:
    with pytest.raises(ValueError, match=r"^RAPTOR\.REFERENCE\.INVALID_UTF8$"):
        RaptorMarkdownProfile().parse(_inline(b"\xff"))


def test_no_item_is_a_named_failure() -> None:
    with pytest.raises(ValueError, match=r"^RAPTOR\.REFERENCE\.NO_ITEM$"):
        RaptorMarkdownProfile().parse(_inline(b"# Empty\n"))


def test_duplicate_heading_is_a_named_failure() -> None:
    source = _inline(b"## REQ-CORE-0001: First\n\n## REQ-CORE-0001: Again\n")
    with pytest.raises(ValueError, match=r"^RAPTOR\.REFERENCE\.DUPLICATE_HEADING$"):
        RaptorMarkdownProfile().parse(source)


def test_plain_level_two_headings_remain_in_item_content() -> None:
    source = _inline(
        b"# Invented\n\n"
        b"## REQ-CORE-0001: First\n\n"
        b"**Status:** Draft\n\n"
        b"Body.\n\n"
        b"## Grouping heading\n\n"
        b"Group text.\n\n"
        b"## REQ-CORE-0002: Second\n\n"
        b"**Status:** Draft\n\n"
        b"## Trailing heading\n\n"
        b"Tail.\n"
    )
    document = RaptorMarkdownProfile().canonicalize(RaptorMarkdownProfile().parse(source))

    assert [item.id for item in document.artifacts] == ["REQ-CORE-0001", "REQ-CORE-0002"]
    assert document.artifacts[0].content.endswith("## Grouping heading\n\nGroup text.\n\n")
    assert document.artifacts[1].content.endswith("## Trailing heading\n\nTail.\n")
    assert document.artifacts[0].subsections == []
    assert document.artifacts[1].subsections == []
    envelope = [segment for segment in document.non_item_segments if segment.kind == "text"]
    assert len(envelope) == 1
    assert envelope[0].model_dump() == {
        "kind": "text",
        "content": "# Invented\n\n",
        "artifact_index": None,
    }


def test_unsupported_item_status_is_a_named_failure() -> None:
    source = _inline(b"## REQ-CORE-0001: Status\n\n**Status:** Other\n")
    parsed = RaptorMarkdownProfile().parse(source)
    with pytest.raises(ValueError, match=r"^RAPTOR\.REFERENCE\.UNSUPPORTED_STATUS$"):
        RaptorMarkdownProfile().canonicalize(parsed)


def test_failure_does_not_affect_another_document() -> None:
    profile = RaptorMarkdownProfile()
    with pytest.raises(ValueError, match=r"RAPTOR\.REFERENCE\.NO_ITEM"):
        profile.parse(_inline(b"# Not an item\n"))
    document = profile.canonicalize(
        profile.parse(_inline(b"## REQ-CORE-0001: Independent\n", document_id="DOC-CORE-0100"))
    )
    assert document.artifacts[0].id == "REQ-CORE-0001"


def test_whole_document_off_list_status_is_nullable_without_a_diagnostic() -> None:
    source = SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id="DOC-CORE-0101", repository_path=PurePosixPath("docs/design.md"), content=b"# Free form\n\n**Status:** Unlisted\n\n# Second title\n", routed_artifact_type=ArtifactType.DESIGN_DOCUMENT)
    document = RaptorMarkdownProfile().canonicalize(RaptorMarkdownProfile().parse(source))
    assert document.artifacts[0].id == "DOC-CORE-0101"
    assert document.artifacts[0].status is None
    assert document.non_item_segments == []
