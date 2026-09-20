from __future__ import annotations

import json
import hashlib
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from raptor_schema import SourceDocument

from runtime.profiles import RaptorMarkdownProfile
from runtime import rendering
from runtime.rendering import (
    compare_semantics,
    project_render_input,
    render_markdown,
    resolve_sc_compose,
    resolve_template_set,
    validate_render_projection,
)

REPO = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("index", range(5))
def test_every_family_renders_deterministically_and_round_trips(index: int) -> None:
    value = json.loads((REPO / "schema/tests/corpus/all-families.json").read_text())
    value["artifacts"] = [value["artifacts"][index]]
    document = SourceDocument.model_validate(value)
    profile = RaptorMarkdownProfile()
    executable = resolve_sc_compose()
    first = render_markdown(
        document,
        profile=profile,
        template_set="raptor",
        output_path="docs/rendered.md",
        repository_root=REPO,
        executable=executable,
    )
    second = render_markdown(
        document,
        profile=profile,
        template_set="raptor",
        output_path="docs/rendered.md",
        repository_root=REPO,
        executable=executable,
    )
    assert first.content == second.content
    assert compare_semantics(
        document, first.document, profile=profile, content=first.content
    ).equal
    assert first.document.provenance.origin == document.provenance.origin
    assert first.document.provenance.materialization.operation == "rendered"
    expected_labels = (
        (b"Statement:", b"Canonical Artifact:"),
        (b"Statement:", b"Canonical Artifact:"),
        (b"Decision:", b"Canonical Artifact:"),
        (b"Overview:", b"Canonical Artifact:"),
        (b"Objective:", b"Canonical Artifact:"),
    )
    assert all(label in first.content for label in expected_labels[index])


def test_comparator_reports_payload_mutation() -> None:
    value = json.loads((REPO / "schema/tests/corpus/all-families.json").read_text())
    value["artifacts"] = [value["artifacts"][0]]
    expected = SourceDocument.model_validate(value)
    changed = expected.model_copy(
        update={
            "artifacts": [expected.artifacts[0].model_copy(update={"title": "changed"})]
        }
    )
    result = compare_semantics(expected, changed, profile=RaptorMarkdownProfile())
    assert "/artifacts/0/title" in result.differences


@pytest.mark.parametrize(
    ("version", "accepted"),
    [
        ("1.6.0", False),
        ("1.6.1", True),
        ("1.9.9", True),
        ("2.0.0", False),
        ("bad", False),
    ],
)
def test_sc_compose_version_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str, accepted: bool
) -> None:
    executable = tmp_path / "sc-compose"
    executable.write_text(f"#!/bin/sh\necho 'sc-compose {version}'\n")
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(rendering.shutil, "which", lambda _name: str(executable))
    if accepted:
        assert resolve_sc_compose() == executable.resolve()
    else:
        with pytest.raises(ValueError, match="SC_COMPOSE_VERSION"):
            resolve_sc_compose()


def test_sc_compose_missing_and_non_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rendering, "_sc_compose_candidates", lambda: ())
    with pytest.raises(ValueError, match="SC_COMPOSE_MISSING"):
        resolve_sc_compose()
    candidate = tmp_path / "sc-compose"
    candidate.write_text("#!/bin/sh\necho 'sc-compose 1.6.1'\n")
    monkeypatch.setattr(rendering, "_sc_compose_candidates", lambda: (candidate,))
    with pytest.raises(ValueError, match="SC_COMPOSE_MISSING"):
        resolve_sc_compose()


def test_sc_compose_candidates_include_user_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rendering.shutil, "which", lambda _name: None)
    expected = Path(rendering.site.getuserbase()) / "bin/sc-compose"
    assert expected in rendering._sc_compose_candidates()


def test_external_template_set_is_hash_verified(tmp_path: Path) -> None:
    root = tmp_path / ".raptor/template-sets/consumer"
    root.mkdir(parents=True)
    names = {
        "requirement": "requirement.md.j2",
        "non_functional_requirement": "non-functional-requirement.md.j2",
        "architecture_decision": "architecture-decision.md.j2",
        "design_document": "design-document.md.j2",
        "test_plan": "test-plan.md.j2",
    }
    hashes = {}
    for name in names.values():
        shutil.copyfile(REPO / "plugins/raptor/templates" / name, root / name)
        hashes[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    (root / "template-set.json").write_text(
        json.dumps(
            {
                "name": "consumer",
                "version": "1.0.0",
                "templates": names,
                "sha256": hashes,
            }
        )
    )
    assert rendering.resolve_template_set(tmp_path, "consumer").templates == names


def test_template_strict_mode_rejects_missing_top_level_variable(
    tmp_path: Path,
) -> None:
    variables = tmp_path / "vars.json"
    variables.write_text(
        json.dumps(
            {
                "provenance_block": "<!-- provenance -->",
            }
        )
    )
    result = subprocess.run(
        [
            str(resolve_sc_compose()),
            "render",
            "--root",
            str(REPO / "plugins/raptor"),
            "--file",
            "templates/requirement.md.j2",
            "--var-file",
            str(variables),
            "--strict",
            "--unknown-var-mode",
            "error",
            "--check-render",
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert result.returncode != 0


def test_projection_boundary_rejects_missing_nested_family_field() -> None:
    document = SourceDocument.model_validate_json(
        (REPO / "plugins/raptor/tests/fixtures/raptor/requirement.json").read_bytes()
    )
    _, projection = project_render_input(
        document,
        profile=RaptorMarkdownProfile(),
        template_set=resolve_template_set(REPO, "raptor"),
    )
    artifacts = projection["artifacts"]
    assert isinstance(artifacts, list) and isinstance(artifacts[0], dict)
    del artifacts[0]["body"]
    with pytest.raises(ValueError, match="missing family field"):
        validate_render_projection("requirement", projection)


def test_visible_statement_mutation_is_rejected() -> None:
    document = SourceDocument.model_validate_json(
        (REPO / "plugins/raptor/tests/fixtures/raptor/requirement.json").read_bytes()
    )
    rendered = render_markdown(
        document,
        profile=RaptorMarkdownProfile(),
        template_set="raptor",
        output_path="docs/rendered.md",
        repository_root=REPO,
        executable=resolve_sc_compose(),
    )
    changed = rendered.content.replace(
        b"Statement: Define five consumer-neutral artifact families.",
        b"Statement: changed",
    )
    source = rendering.SourceInput(
        repo_root=REPO,
        repository_id=document.provenance.origin.repository_id,
        document_id=document.provenance.origin.document_id,
        repository_path=Path("docs/rendered.md"),
        content=changed,
    )
    profile = RaptorMarkdownProfile()
    with pytest.raises(ValueError, match="VISIBLE_MISMATCH"):
        profile.canonicalize(profile.parse(source))

    changed_title = rendered.content.replace(
        b"Canonical artifact families", b"Changed title", 1
    )
    titled = rendering.SourceInput(
        repo_root=REPO,
        repository_id=document.provenance.origin.repository_id,
        document_id=document.provenance.origin.document_id,
        repository_path=Path("docs/rendered.md"),
        content=changed_title,
    )
    with pytest.raises(ValueError, match="VISIBLE_MISMATCH"):
        profile.canonicalize(profile.parse(titled))


def test_comparator_reports_path_and_template_identity() -> None:
    document = SourceDocument.model_validate_json(
        (REPO / "plugins/raptor/tests/fixtures/raptor/requirement.json").read_bytes()
    )
    rendered = render_markdown(
        document,
        profile=RaptorMarkdownProfile(),
        template_set="raptor",
        output_path="docs/rendered.md",
        repository_root=REPO,
        executable=resolve_sc_compose(),
    )
    result = compare_semantics(
        document,
        rendered.document,
        profile=RaptorMarkdownProfile(),
        content=rendered.content,
        expected_output_path="docs/other.md",
        template_set="consumer",
        template_version="9.9.9",
    )
    assert result.differences == (
        "/provenance/materialization/repository_path",
        "/provenance/materialization/template_set",
        "/provenance/materialization/template_version",
    )
