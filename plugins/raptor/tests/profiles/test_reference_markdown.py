from pathlib import Path, PurePosixPath

import pytest
from raptor_schema.profiles import SourceInput

from runtime.profiles import RaptorMarkdownProfile


ROOT = Path(__file__).parents[4]
FIXTURES = ROOT / "plugins/raptor/tests/fixtures/reference"


def _source(path: Path) -> SourceInput:
    return SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id=f"DOC-CORE-{list(sorted(FIXTURES.glob('*.md'))).index(path) + 1:04}", repository_path=PurePosixPath(path.relative_to(ROOT).as_posix()), content=path.read_bytes())


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.md")))
def test_reference_fixture_extracts(path: Path) -> None:
    document = RaptorMarkdownProfile().canonicalize(RaptorMarkdownProfile().parse(_source(path)))
    assert document.schema_version == "2.0.0"
    assert document.artifacts


def test_non_colon_item_heading_is_a_named_malformed_heading() -> None:
    source = SourceInput(repo_root=ROOT, repository_id="urn:raptor:repo:alpha", document_id="DOC-CORE-0099", repository_path=PurePosixPath("docs/bad.md"), content="## ADR-CORE-0001 — Not a colon\n".encode())
    with pytest.raises(ValueError, match=r"RAPTOR\.REFERENCE\.MALFORMED_HEADING: line 1"):
        RaptorMarkdownProfile().parse(source)
