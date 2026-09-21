from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter

from raptor_schema import (
    ArchitectureDecision,
    DesignDocument,
    Diagnostic,
    JsonObject,
    MaterializationProvenance,
    NonFunctionalRequirement,
    OriginProvenance,
    ProfileId,
    ProfileVersion,
    Requirement,
    SourceDocument,
    SourceLocation,
    SourceProvenance,
    TestPlan,
    validate_json_object,
)
from raptor_schema.profiles import (
    ArtifactSnapshot,
    ComparableDocument,
    FrozenJsonObject,
    ParsedDocument,
    ParsedSection,
    ProfileDescriptor,
    SourceInput,
    SourceProfile,
)

from .strict_json import loads
from .io import read_repository_bytes

_HEADING = re.compile(
    r"^###\s+((?:REQ|NFR|ADR|DES|TST)-[A-Z0-9][A-Z0-9-]*-[0-9]{3,})\s+[—-]\s+(.+?)\s*$",
    re.MULTILINE,
)
_PROVENANCE_BLOCK = re.compile(
    r"<!--\s*raptor-provenance-v1:([A-Za-z0-9_-]+)\s*-->", re.MULTILINE
)
_CANONICAL_ARTIFACT_LINE = re.compile(
    r"^Canonical Artifact: ([^\r\n]*)\r?$", re.MULTILINE
)


def _paragraph(value: str) -> str:
    return " ".join(line.strip() for line in value.strip().splitlines() if line.strip())


def _native_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        fields[name.strip().lower()] = value.strip()
    return fields


def _required_field(fields: dict[str, str], name: str) -> str:
    value = fields.get(name, "")
    if not value:
        raise ValueError(f"RAPTOR.PROFILE.CANONICALIZE: missing {name}")
    return value


def _parts(fields: dict[str, str], name: str, count: int) -> list[str]:
    values = [item.strip() for item in _required_field(fields, name).split("|")]
    if len(values) != count or any(not item for item in values):
        raise ValueError(f"RAPTOR.PROFILE.CANONICALIZE: invalid {name}")
    return values


def _artifact_keys(value: str) -> list[dict[str, str]]:
    if not value:
        return []
    keys: list[dict[str, str]] = []
    for item in value.split(","):
        repository_id, separator, artifact_id = item.strip().rpartition("/")
        if not separator:
            raise ValueError("RAPTOR.PROFILE.CANONICALIZE: invalid artifact key")
        keys.append({"repository_id": repository_id, "artifact_id": artifact_id})
    return keys


def _render_summary(artifact: Mapping[str, object]) -> str:
    family = artifact.get("artifact_type")
    field = {
        "requirement": "statement",
        "non_functional_requirement": "statement",
        "architecture_decision": "decision",
        "design_document": "overview",
        "test_plan": "objective",
    }.get(str(family))
    if field is None or not isinstance(artifact.get(field), str):
        raise ValueError("RAPTOR.RENDER.PROJECTION: unsupported artifact family")
    return f"{field.replace('_', ' ').title()}: {artifact[field]}"


class RaptorMarkdownProfile:
    def __init__(
        self, profile_id: str = "raptor", profile_version: str = "1.0.0"
    ) -> None:
        self.profile_id = profile_id
        self.profile_version = profile_version

    def parse(self, source: SourceInput) -> ParsedDocument:
        try:
            text = source.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("RAPTOR.PROFILE.PARSE: Markdown must be UTF-8") from error
        blocks = _PROVENANCE_BLOCK.findall(text)
        if len(blocks) > 1:
            raise ValueError("RAPTOR.PROVENANCE.BLOCK: multiple provenance blocks")
        frontmatter: JsonObject = {}
        if blocks:
            try:
                padded = blocks[0] + "=" * (-len(blocks[0]) % 4)
                value = loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
                frontmatter = validate_json_object({"raptor_provenance": value})
            except Exception as error:
                raise ValueError(
                    "RAPTOR.PROVENANCE.BLOCK: invalid provenance block"
                ) from error
        sections: list[ParsedSection] = []
        for match in _HEADING.finditer(text):
            next_match = _HEADING.search(text, match.end())
            end = next_match.start() if next_match else len(text)
            body = text[match.end() : end].strip()
            sections.append(
                ParsedSection(
                    kind=match.group(1).split("-", 1)[0],
                    heading=match.group(2).strip(),
                    body=body,
                    location=SourceLocation(
                        start_line=text.count("\n", 0, match.start()) + 1,
                        start_column=1,
                        end_line=text.count("\n", 0, end) + 1,
                        end_column=1,
                    ),
                    attributes={"artifact_id": match.group(1)},
                )
            )
        if not sections and re.search(r"^#\s+ADR-", text, re.MULTILINE):
            heading = re.search(
                r"^#\s+(ADR-[A-Z0-9][A-Z0-9-]*-[0-9]{3,})\s+[—-]\s+(.+)$",
                text,
                re.MULTILINE,
            )
            if heading:
                sections.append(
                    ParsedSection(
                        kind="ADR",
                        heading=heading.group(2).strip(),
                        body=text,
                        location=SourceLocation(start_line=1, start_column=1),
                        attributes={"artifact_id": heading.group(1)},
                    )
                )
        if not sections:
            raise ValueError("RAPTOR.PROFILE.PARSE: no Raptor artifacts found")
        return ParsedDocument(
            source=source,
            frontmatter=cast(FrozenJsonObject, frontmatter),
            sections=tuple(sections),
        )

    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]:
        return []

    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument:
        rendered = parsed.frontmatter.get("raptor_provenance")
        if rendered is not None:
            if not isinstance(rendered, Mapping):
                raise ValueError("RAPTOR.PROVENANCE.BLOCK: invalid provenance payload")
            required = {
                "schema_version",
                "origin",
                "parent_content_sha256",
                "parser_profile",
                "parser_profile_version",
                "template_set",
                "template_version",
            }
            if set(rendered) != required:
                raise ValueError("RAPTOR.PROVENANCE.BLOCK: invalid provenance payload")
            origin = OriginProvenance.model_validate(rendered["origin"])
            if (
                origin.repository_id != parsed.source.repository_id
                or origin.document_id != parsed.source.document_id
            ):
                raise ValueError(
                    "RAPTOR.PROVENANCE.ORIGIN_MUTATION: rendered origin is immutable"
                )
            rendered_artifacts: list[object] = []
            for section in parsed.sections:
                canonical_matches = list(
                    _CANONICAL_ARTIFACT_LINE.finditer(section.body)
                )
                if not canonical_matches:
                    raise ValueError(
                        "RAPTOR.RENDER.VISIBLE_MISMATCH: canonical artifact is missing"
                    )
                canonical_match = canonical_matches[-1]
                item = loads(canonical_match.group(1))
                if not isinstance(item, dict):
                    raise ValueError(
                        "RAPTOR.RENDER.VISIBLE_MISMATCH: canonical artifact is invalid"
                    )
                artifact = dict(item)
                expected_summary = _render_summary(artifact)
                visible_summary = section.body[: canonical_match.start()]
                if visible_summary.endswith("\r\n"):
                    visible_summary = visible_summary[:-2]
                elif visible_summary.endswith("\n"):
                    visible_summary = visible_summary[:-1]
                if (
                    artifact.get("id") != section.attributes["artifact_id"]
                    or artifact.get("title") != section.heading
                    or canonical_match.end() != len(section.body)
                    or visible_summary != expected_summary
                ):
                    raise ValueError(
                        "RAPTOR.RENDER.VISIBLE_MISMATCH: visible artifact disagrees"
                    )
                artifact["source_location"] = section.location.model_dump(mode="json")
                rendered_artifacts.append(artifact)
            digest = hashlib.sha256(parsed.source.content).hexdigest()
            return SourceDocument.model_validate(
                {
                    "schema_version": rendered["schema_version"],
                    "provenance": {
                        "origin": origin,
                        "materialization": {
                            "repository_path": parsed.source.repository_path.as_posix(),
                            "content_sha256": digest,
                            "operation": "rendered",
                            "parent_content_sha256": rendered["parent_content_sha256"],
                            "parser_profile": rendered["parser_profile"],
                            "parser_profile_version": rendered[
                                "parser_profile_version"
                            ],
                            "template_set": rendered["template_set"],
                            "template_version": rendered["template_version"],
                        },
                    },
                    "artifacts": rendered_artifacts,
                }
            )
        artifacts: list[object] = []
        repository_id = parsed.source.repository_id
        for section in parsed.sections:
            artifact_id = str(section.attributes["artifact_id"])
            location = section.location.model_dump(mode="json")
            if section.kind in {"REQ", "NFR"}:
                statement, marker, acceptance = section.body.partition("Acceptance:")
                if not marker or not _paragraph(acceptance):
                    raise ValueError(
                        "RAPTOR.PROFILE.CANONICALIZE: requirement omits Acceptance"
                    )
                common = {
                    "id": artifact_id,
                    "title": section.heading,
                    "status": "accepted",
                    "statement": _paragraph(statement),
                    "acceptance_criteria": [_paragraph(acceptance)],
                    "source_location": location,
                }
                if section.kind == "REQ":
                    artifacts.append(
                        Requirement.model_validate(
                            {"artifact_type": "requirement", **common}
                        )
                    )
                else:
                    attribute = re.sub(
                        r"[^a-z0-9_]+", "_", (section.heading or "quality").lower()
                    ).strip("_")
                    artifacts.append(
                        NonFunctionalRequirement.model_validate(
                            {
                                "artifact_type": "non_functional_requirement",
                                "quality_attribute": attribute,
                                "measurement": {
                                    "name": "acceptance satisfied",
                                    "comparator": "eq",
                                    "target": True,
                                },
                                **common,
                            },
                        )
                    )
            elif section.kind == "ADR":
                adr_values = {
                    name.lower(): _paragraph(body)
                    for name, body in re.findall(
                        r"^##\s+([^\n]+)\n(.*?)(?=^##\s+|\Z)",
                        section.body,
                        re.MULTILINE | re.DOTALL,
                    )
                }
                artifacts.append(
                    ArchitectureDecision.model_validate(
                        {
                            "artifact_type": "architecture_decision",
                            "id": artifact_id,
                            "title": section.heading,
                            "status": "accepted",
                            "context": adr_values.get(
                                "context", "Context recorded in source."
                            ),
                            "decision": adr_values.get(
                                "decision", "Decision recorded in source."
                            ),
                            "alternatives": [adr_values["alternatives"]]
                            if adr_values.get("alternatives")
                            else [],
                            "consequences": [
                                adr_values.get(
                                    "consequences", "No consequences recorded."
                                )
                            ],
                            "source_location": location,
                        },
                    )
                )
            elif section.kind == "DES":
                fields = _native_fields(section.body)
                component = _parts(fields, "component", 2)
                interface = _parts(fields, "interface", 3)
                artifacts.append(
                    DesignDocument.model_validate(
                        {
                            "artifact_type": "design_document",
                            "id": artifact_id,
                            "title": section.heading,
                            "status": "proposed",
                            "overview": _required_field(fields, "overview"),
                            "components": [
                                {
                                    "name": component[0],
                                    "responsibility": component[1],
                                    "dependencies": _artifact_keys(
                                        fields.get("dependencies", "")
                                    ),
                                }
                            ],
                            "interfaces": [
                                {
                                    "name": interface[0],
                                    "description": interface[1],
                                    "participants": [
                                        item.strip() for item in interface[2].split(",")
                                    ],
                                }
                            ],
                            "source_location": location,
                        }
                    )
                )
            elif section.kind == "TST":
                fields = _native_fields(section.body)
                case = _parts(fields, "test case", 4)
                verifies = _artifact_keys(_required_field(fields, "verifies"))
                artifacts.append(
                    TestPlan.model_validate(
                        {
                            "artifact_type": "test_plan",
                            "id": artifact_id,
                            "title": section.heading,
                            "status": "proposed",
                            "objective": _required_field(fields, "objective"),
                            "scope": _required_field(fields, "scope"),
                            "test_cases": [
                                {
                                    "id": case[0],
                                    "title": case[1],
                                    "steps": [
                                        item.strip() for item in case[2].split(";")
                                    ],
                                    "expected_result": case[3],
                                    "verifies": verifies,
                                }
                            ],
                            "entry_criteria": [
                                item.strip()
                                for item in fields.get("entry criteria", "").split(";")
                                if item.strip()
                            ],
                            "exit_criteria": [_required_field(fields, "exit criteria")],
                            "source_location": location,
                        }
                    )
                )
        digest = hashlib.sha256(parsed.source.content).hexdigest()
        path = parsed.source.repository_path.as_posix()
        origin = OriginProvenance(
            repository_id=repository_id,
            document_id=parsed.source.document_id,
            initial_repository_path=path,
            original_content_sha256=digest,
            source_format="markdown",
            parser_profile=self.profile_id,
            parser_profile_version=self.profile_version,
        )
        materialization = MaterializationProvenance(
            repository_path=path,
            content_sha256=digest,
            operation="imported",
            parser_profile=self.profile_id,
            parser_profile_version=self.profile_version,
        )
        return SourceDocument.model_validate(
            {
                "schema_version": "1.0.0",
                "provenance": SourceProvenance(
                    origin=origin, materialization=materialization
                ),
                "artifacts": artifacts,
            }
        )

    def project_render_input(self, document: SourceDocument) -> JsonObject:
        artifacts: list[dict[str, object]] = []
        for artifact in document.artifacts:
            canonical = artifact.model_dump(mode="json", exclude_none=True)
            canonical.pop("source_location", None)
            artifacts.append(
                {
                    "id": artifact.id,
                    "title": artifact.title,
                    "body": _render_summary(canonical)
                    + "\nCanonical Artifact: "
                    + json.dumps(canonical, sort_keys=True, separators=(",", ":")),
                }
            )
        return validate_json_object({"artifacts": artifacts})

    def normalize(self, document: SourceDocument) -> ComparableDocument:
        return ComparableDocument(
            schema_version=document.schema_version,
            origin=document.provenance.origin,
            artifacts=tuple(
                ArtifactSnapshot(
                    data=cast(
                        FrozenJsonObject,
                        validate_json_object(
                            artifact.model_dump(
                                mode="json",
                                exclude={"source_location"},
                                exclude_none=True,
                            )
                        ),
                    ),
                )
                for artifact in document.artifacts
            ),
        )


def resolve_profile(
    repository_root: Path,
    profile_id: str,
    version: str | None = None,
    *,
    allow_profile_code: bool = False,
) -> SourceProfile:
    try:
        profile_id = TypeAdapter(ProfileId).validate_python(profile_id)
    except ValueError as error:
        raise ValueError("RAPTOR.PROFILE.ID: invalid profile identifier") from error
    if version is not None and not re.fullmatch(r"[1-9][0-9]*\.x", version):
        try:
            version = TypeAdapter(ProfileVersion).validate_python(version)
        except ValueError as error:
            raise ValueError(
                "RAPTOR.PROFILE.VERSION: invalid version constraint"
            ) from error
    if profile_id == "raptor":
        if version not in {None, "1.x", "1.0.0"}:
            raise ValueError("RAPTOR.PROFILE.VERSION: no compatible built-in profile")
        return RaptorMarkdownProfile()
    if not allow_profile_code:
        raise ValueError("RAPTOR.PROFILE.UNTRUSTED: external profile code is opt-in")
    root = repository_root.resolve()
    profiles_root = root / ".raptor/profiles"
    try:
        profiles_root.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(
            "RAPTOR.PROFILE.ENTRYPOINT: profile root escapes repository"
        ) from error
    if profiles_root.is_symlink():
        raise ValueError("RAPTOR.PROFILE.ENTRYPOINT: profile root may not be a symlink")
    candidates = sorted((profiles_root / profile_id).glob("*/profile.json"))
    if not candidates:
        raise ValueError("RAPTOR.PROFILE.VERSION: profile is not registered")
    compatible: list[tuple[ProfileDescriptor, Path]] = []
    for descriptor_path in candidates:
        if (
            descriptor_path.is_symlink()
            or descriptor_path.parent.is_symlink()
            or descriptor_path.parent.parent.is_symlink()
        ):
            raise ValueError(
                "RAPTOR.PROFILE.ENTRYPOINT: descriptor may not be a symlink"
            )
        resolved = descriptor_path.resolve()
        try:
            resolved.relative_to(profiles_root.resolve())
        except ValueError as error:
            raise ValueError(
                "RAPTOR.PROFILE.ENTRYPOINT: descriptor escapes root"
            ) from error
        try:
            raw_descriptor = loads(
                read_repository_bytes(
                    root, descriptor_path.relative_to(root).as_posix()
                ).decode("utf-8")
            )
            if not isinstance(raw_descriptor, dict):
                raise ValueError("descriptor must be an object")
            descriptor = ProfileDescriptor(**raw_descriptor)
        except Exception as error:
            message = str(error)
            code = (
                "RAPTOR.PROFILE.API"
                if "api_version" in message
                else "RAPTOR.PROFILE.DESCRIPTOR"
            )
            raise ValueError(f"{code}: invalid profile descriptor") from error
        if descriptor.profile_id != profile_id:
            continue
        if (
            version is None
            or descriptor.profile_version == version
            or (
                version.endswith(".x")
                and descriptor.profile_version.split(".", 1)[0] == version[:-2]
            )
        ):
            compatible.append((descriptor, resolved.parent))
    if not compatible:
        raise ValueError("RAPTOR.PROFILE.VERSION: no compatible profile version")
    compatible.sort(
        key=lambda item: tuple(int(part) for part in item[0].profile_version.split("."))
    )
    if (
        len(compatible) > 1
        and compatible[-1][0].profile_version == compatible[-2][0].profile_version
    ):
        raise ValueError(
            "RAPTOR.PROFILE.AMBIGUOUS: duplicate compatible profile version"
        )
    descriptor, directory = compatible[-1]
    if descriptor.api_version != "1":
        raise ValueError("RAPTOR.PROFILE.API: unsupported profile API")
    module_name, separator, implementation_name = descriptor.entrypoint.partition(":")
    raw_module_path = directory / module_name
    module_path = raw_module_path.resolve()
    if (
        not separator
        or implementation_name != "raptor-markdown"
        or Path(module_name).suffix != ".json"
        or directory.resolve() not in module_path.parents
    ):
        raise ValueError("RAPTOR.PROFILE.ENTRYPOINT: invalid profile entrypoint")
    if raw_module_path.is_symlink() or not module_path.is_file():
        raise ValueError(
            "RAPTOR.PROFILE.ENTRYPOINT: profile module is not a regular file"
        )
    module_bytes = read_repository_bytes(
        root, raw_module_path.relative_to(root).as_posix()
    )
    if hashlib.sha256(module_bytes).hexdigest() != descriptor.module_sha256:
        raise ValueError("RAPTOR.PROFILE.HASH: profile module hash mismatch")
    try:
        declaration = loads(module_bytes.decode("utf-8"))
    except Exception as error:
        raise ValueError(
            "RAPTOR.PROFILE.NETWORK: external profiles must be declarative"
        ) from error
    expected = {
        "kind": "raptor-markdown-profile",
        "profile_id": descriptor.profile_id,
        "profile_version": descriptor.profile_version,
    }
    if declaration != expected:
        raise ValueError(
            "RAPTOR.PROFILE.NETWORK: external profiles must be declarative"
        )
    return cast(
        SourceProfile,
        RaptorMarkdownProfile(descriptor.profile_id, descriptor.profile_version),
    )


__all__ = ["RaptorMarkdownProfile", "resolve_profile"]
