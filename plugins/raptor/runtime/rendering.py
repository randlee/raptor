from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import site
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import TypeAdapter
from raptor_schema import (
    RepositoryPath,
    SourceDocument,
    load_canonical_json,
    validate_provenance_transition,
)
from raptor_schema.profiles import SourceInput, SourceProfile

from .strict_json import loads
from .requirements import load_sc_compose_requirement
from .agent_runner import JsonValue

TEMPLATE_VERSION = "1.0.0"
_TEMPLATES = {
    "requirement": "requirement.md.j2",
    "non_functional_requirement": "non-functional-requirement.md.j2",
    "architecture_decision": "architecture-decision.md.j2",
    "design_document": "design-document.md.j2",
    "test_plan": "test-plan.md.j2",
}
_PATH = TypeAdapter(RepositoryPath)


@dataclass(frozen=True)
class RenderedDocument:
    document: SourceDocument
    content: bytes
    output_path: str
    template_path: str


@dataclass(frozen=True)
class SemanticComparison:
    equal: bool
    differences: tuple[str, ...]


@dataclass(frozen=True)
class TemplateSet:
    name: str
    version: str
    root: Path
    templates: dict[str, str]


def _sc_compose_candidates() -> tuple[Path, ...]:
    found = shutil.which("sc-compose")
    return tuple(
        item
        for item in (
            Path(found) if found else None,
            Path.home() / ".local/bin/sc-compose",
            Path.home() / ".venvs/sc-compose/bin/sc-compose",
            Path(site.getuserbase()) / "bin/sc-compose",
            Path("/opt/homebrew/bin/sc-compose"),
        )
        if item is not None
    )


def resolve_sc_compose() -> Path:
    requirement = load_sc_compose_requirement(Path(__file__).resolve().parents[1])
    constraint = str(requirement["version"])
    executable = next(
        (
            item
            for item in _sc_compose_candidates()
            if item.is_file() and os.access(item, os.X_OK)
        ),
        None,
    )
    if executable is None:
        raise ValueError(
            "RAPTOR.DEPENDENCY.SC_COMPOSE_MISSING: sc-compose is not installed"
        )
    result = subprocess.run(
        [str(executable), "--version"],
        capture_output=True,
        text=True,
        env=_environment(),
    )
    match = re.fullmatch(r"sc-compose\s+([0-9]+)\.([0-9]+)\.([0-9]+)\s*", result.stdout)
    if result.returncode or match is None:
        raise ValueError(
            "RAPTOR.DEPENDENCY.SC_COMPOSE_VERSION: version output is invalid"
        )
    version = tuple(int(item) for item in match.groups())
    lower_text, upper_text = constraint.removeprefix(">=").split(",<", 1)
    lower = tuple(int(item) for item in lower_text.split("."))
    upper = tuple(int(item) for item in upper_text.split("."))
    if version < lower or version >= upper:
        raise ValueError(
            f"RAPTOR.DEPENDENCY.SC_COMPOSE_VERSION: {constraint} is required"
        )
    return executable.resolve()


def resolve_template_set(repository_root: Path, name: str) -> TemplateSet:
    if name == "raptor":
        root = Path(__file__).resolve().parents[1]
        return TemplateSet(name, TEMPLATE_VERSION, root, dict(_TEMPLATES))
    repository_root = repository_root.resolve()
    root = repository_root / ".raptor/template-sets" / name
    manifest_path = root / "template-set.json"
    if root.is_symlink() or manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("RAPTOR.TEMPLATE.SET: template set is not registered")
    try:
        value = loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError("RAPTOR.TEMPLATE.SET: invalid template manifest") from error
    if not isinstance(value, dict) or set(value) != {
        "name",
        "version",
        "templates",
        "sha256",
    }:
        raise ValueError("RAPTOR.TEMPLATE.SET: invalid template manifest")
    templates, hashes = value["templates"], value["sha256"]
    if (
        value["name"] != name
        or not isinstance(value["version"], str)
        or not re.fullmatch(r"[1-9][0-9]*\.[0-9]+\.[0-9]+", value["version"])
        or not isinstance(templates, dict)
        or set(templates) != set(_TEMPLATES)
        or not isinstance(hashes, dict)
    ):
        raise ValueError("RAPTOR.TEMPLATE.SET: invalid template manifest")
    checked: dict[str, str] = {}
    for family, relative in templates.items():
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError("RAPTOR.TEMPLATE.PATH: template path is unsafe")
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or path.resolve().parent != root.resolve()
        ):
            raise ValueError("RAPTOR.TEMPLATE.PATH: template path is unsafe")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if hashes.get(relative) != digest:
            raise ValueError("RAPTOR.TEMPLATE.HASH: template hash mismatch")
        checked[str(family)] = relative
    return TemplateSet(name, value["version"], root, checked)


def project_render_input(
    document: SourceDocument, *, profile: SourceProfile, template_set: TemplateSet
) -> tuple[str, dict[str, Any]]:
    document = SourceDocument.model_validate(document.model_dump(mode="python"))
    projected = profile.project_render_input(document)
    if not isinstance(projected, dict):
        raise ValueError(
            "RAPTOR.RENDER.PROJECTION: profile projection must be an object"
        )
    families = {str(artifact.artifact_type.value) for artifact in document.artifacts}
    if len(families) != 1:
        raise ValueError("RAPTOR.RENDER.FAMILY: one artifact family is required")
    family = families.pop()
    template = template_set.templates.get(family)
    if template is None:
        raise ValueError(
            "RAPTOR.RENDER.FAMILY: template does not support artifact family"
        )
    materialization = document.provenance.materialization
    payload = {
        "schema_version": document.schema_version,
        "origin": document.provenance.origin.model_dump(mode="json"),
        "parent_content_sha256": materialization.content_sha256,
        "parser_profile": profile.profile_id,
        "parser_profile_version": profile.profile_version,
        "template_set": template_set.name,
        "template_version": template_set.version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    token = base64.urlsafe_b64encode(encoded).decode().rstrip("=")
    projection = dict(projected)
    projection["provenance_block"] = f"<!-- raptor-provenance-v1:{token} -->"
    validate_render_projection(family, projection)
    return template, projection


def validate_render_projection(family: str, projection: object) -> None:
    """Reject incomplete nested data before sc-compose's top-level boundary."""
    if not isinstance(projection, dict) or set(projection) != {
        "provenance_block",
        "artifacts",
    }:
        raise ValueError("RAPTOR.RENDER.PROJECTION: invalid projection shape")
    if not isinstance(projection["provenance_block"], str):
        raise ValueError("RAPTOR.RENDER.PROJECTION: provenance block must be text")
    artifacts = projection["artifacts"]
    required = {"id", "title", "body"}
    if family not in _TEMPLATES or not isinstance(artifacts, list) or not artifacts:
        raise ValueError("RAPTOR.RENDER.PROJECTION: unsupported or empty family")
    for artifact in artifacts:
        if not isinstance(artifact, dict) or not required.issubset(artifact):
            raise ValueError("RAPTOR.RENDER.PROJECTION: missing family field")
        for name in required:
            if not isinstance(artifact[name], str):
                raise ValueError("RAPTOR.RENDER.PROJECTION: invalid family field")


def render_markdown(
    document: SourceDocument,
    *,
    profile: SourceProfile,
    template_set: str,
    output_path: RepositoryPath,
    repository_root: Path,
    executable: Path | None = None,
) -> RenderedDocument:
    root = repository_root.resolve()
    relative = _PATH.validate_python(output_path)
    selected = resolve_template_set(root, template_set)
    template, projection = project_render_input(
        document, profile=profile, template_set=selected
    )
    executable = executable or resolve_sc_compose()
    with tempfile.TemporaryDirectory() as directory:
        variables = Path(directory) / "projection.json"
        variables.write_text(json.dumps(projection, sort_keys=True), encoding="utf-8")
        result = subprocess.run(
            [
                str(executable),
                "render",
                "--root",
                str(selected.root),
                "--file",
                str(Path("templates") / template)
                if selected.name == "raptor"
                else template,
                "--var-file",
                str(variables),
                "--strict",
                "--unknown-var-mode",
                "error",
                "--check-render",
            ],
            capture_output=True,
            env=_environment(),
            cwd=directory,
        )
    if result.returncode:
        raise ValueError("RAPTOR.RENDER.SC_COMPOSE: strict rendering failed")
    content = result.stdout
    if not content.endswith(b"\n"):
        content += b"\n"
    origin = document.provenance.origin
    source = SourceInput(
        repo_root=root,
        repository_id=origin.repository_id,
        document_id=origin.document_id,
        repository_path=PurePosixPath(relative),
        content=content,
    )
    actual = profile.canonicalize(profile.parse(source))
    validate_provenance_transition(document.provenance, actual.provenance)
    return RenderedDocument(actual, content, relative, template)


def compare_semantics(
    expected: SourceDocument,
    actual: SourceDocument,
    *,
    profile: SourceProfile,
    expected_output_path: RepositoryPath,
    template_set: str | None,
    template_version: str | None,
    content: bytes | None = None,
) -> SemanticComparison:
    differences: list[str] = []
    expected_normalized = profile.normalize(expected)
    actual_normalized = profile.normalize(actual)
    _compare_value(
        _comparable_value(expected_normalized),
        _comparable_value(actual_normalized),
        "",
        differences,
    )
    try:
        validate_provenance_transition(expected.provenance, actual.provenance)
    except ValueError as error:
        code = str(error).split(":", 1)[0]
        differences.append(f"/provenance/materialization:{code}")
    materialization = actual.provenance.materialization
    if (
        content is not None
        and materialization.content_sha256 != hashlib.sha256(content).hexdigest()
    ):
        differences.append("/provenance/materialization/content_sha256")
    if materialization.parser_profile != profile.profile_id:
        differences.append("/provenance/materialization/parser_profile")
    if materialization.parser_profile_version != profile.profile_version:
        differences.append("/provenance/materialization/parser_profile_version")
    if materialization.repository_path != expected_output_path:
        differences.append("/provenance/materialization/repository_path")
    if materialization.template_set != template_set:
        differences.append("/provenance/materialization/template_set")
    if materialization.template_version != template_version:
        differences.append("/provenance/materialization/template_version")
    if content is not None:
        lines = content.decode("utf-8").splitlines()
        line_count = len(lines)
        for index, artifact in enumerate(actual.artifacts):
            location = artifact.source_location
            if (
                location is None
                or location.end_line is None
                or location.start_column != 1
                or location.end_column != 1
                or location.end_line < location.start_line
                or location.start_line > line_count
                or location.end_line > line_count + 1
                or artifact.id not in lines[location.start_line - 1]
            ):
                differences.append(f"/artifacts/{index}/source_location")
    return SemanticComparison(not differences, tuple(sorted(set(differences))))


def json_to_markdown(
    repository_root: Path,
    input_path: str,
    output_path: str,
    *,
    profile_id: str = "raptor",
    profile_version: str | None = None,
    template_set: str = "raptor",
    database: str | None = None,
    allow_profile_code: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    from .io import atomic_repository_bytes, read_repository_bytes
    from .operations import repository_path
    from .profiles import resolve_profile
    from .transactions import apply_render_transaction, validate_render_transaction

    executable = resolve_sc_compose()
    root = repository_root.resolve()
    _, source_relative = repository_path(root, input_path, must_exist=True)
    _, output_relative = repository_path(root, output_path)
    document = load_canonical_json(read_repository_bytes(root, source_relative))
    profile = resolve_profile(
        root, profile_id, profile_version, allow_profile_code=allow_profile_code
    )
    rendered = render_markdown(
        document,
        profile=profile,
        template_set=template_set,
        output_path=output_relative,
        repository_root=root,
        executable=executable,
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
        raise ValueError(
            "RAPTOR.ROUND_TRIP.SEMANTIC_LOSS: " + ",".join(comparison.differences)
        )
    transaction: dict[str, object] | None = None
    if database is not None:
        _, database_relative = repository_path(root, database, must_exist=True)
        validate_render_transaction(
            root, document, rendered.document, database_relative
        )
        if apply:
            transaction = apply_render_transaction(
                root,
                document,
                rendered.document,
                rendered.content,
                database_relative,
            )
    elif apply:
        atomic_repository_bytes(root, output_relative, rendered.content)
    return {
        "applied": apply,
        "output": output_relative,
        "template": rendered.template_path,
        "document": rendered.document.model_dump(mode="json", exclude_none=True),
        "differences": list(comparison.differences),
        "transaction": transaction,
    }


def migration_round_trip(
    repository_root: Path,
    markdown_input: str,
    json_path: str,
    database: str,
    exported_json_path: str,
    markdown_output: str,
    *,
    backend: Any,
    profile_id: str = "raptor",
    template_set: str = "raptor",
    apply: bool = False,
) -> dict[str, Any]:
    from .agent_runner import run_agent

    evidence: list[dict[str, Any]] = []
    stages: list[tuple[str, dict[str, JsonValue]]] = [
        (
            "markdown-json-import",
            {
                "input": markdown_input,
                "output": json_path,
                "profile": profile_id,
                "apply": apply,
            },
        )
    ]
    while stages:
        agent, params = stages.pop(0)
        result = run_agent(
            agent=agent,
            params=params,
            backend=backend,
            repository_root=repository_root,
        )
        evidence.append(result)
        if not result.get("success"):
            return result
        if agent == "markdown-json-import":
            data = result.get("data")
            documents = data.get("documents") if isinstance(data, dict) else None
            first = documents[0] if isinstance(documents, list) and documents else None
            if not isinstance(first, dict) or not all(
                isinstance(first.get(name), str)
                for name in ("repository_id", "document_id")
            ):
                raise ValueError(
                    "RAPTOR.ROUND_TRIP.EVIDENCE: Markdown stage omitted identity"
                )
            stages.extend(
                [
                    (
                        "json-sqlite-import",
                        {"input": json_path, "database": database, "apply": apply},
                    ),
                    (
                        "sqlite-json-export",
                        {
                            "database": database,
                            "repository_id": str(first["repository_id"]),
                            "document_id": str(first["document_id"]),
                            "output": exported_json_path,
                            "apply": apply,
                        },
                    ),
                    (
                        "json-markdown-export",
                        {
                            "input": exported_json_path,
                            "output": markdown_output,
                            "profile": profile_id,
                            "template_set": template_set,
                            "database": database,
                            "apply": apply,
                        },
                    ),
                ]
            )
    return {
        "success": True,
        "canceled": False,
        "aborted_by": None,
        "data": {"applied": apply, "stages": evidence},
        "error": None,
        "metadata": {"duration_ms": 0, "tool_calls": 4, "retry_count": 0},
    }


def _comparable_value(document: Any) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "origin": document.origin.model_dump(mode="json"),
        "artifacts": [_thaw(item.data) for item in document.artifacts],
    }


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _compare_value(expected: Any, actual: Any, path: str, output: list[str]) -> None:
    if type(expected) is not type(actual):
        output.append(path)
    elif isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}/{key}"
            if key not in expected or key not in actual:
                output.append(child)
            else:
                _compare_value(expected[key], actual[key], child, output)
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            output.append(path)
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            _compare_value(left, right, f"{path}/{index}", output)
    elif expected != actual:
        output.append(path)


def _environment() -> dict[str, str]:
    return {"PATH": os.defpath, "LANG": "C.UTF-8"}


__all__ = [
    "RenderedDocument",
    "SemanticComparison",
    "TemplateSet",
    "compare_semantics",
    "json_to_markdown",
    "migration_round_trip",
    "project_render_input",
    "render_markdown",
    "resolve_sc_compose",
    "resolve_template_set",
    "validate_render_projection",
]
