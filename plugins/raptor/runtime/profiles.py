from __future__ import annotations

import ast
import hashlib
import importlib.util
import re
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter

from raptor_schema import (
    ArchitectureDecision,
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
    validate_json_object,
)
from raptor_schema.profiles import (
    ArtifactSnapshot,
    ComparableDocument,
    ParsedDocument,
    ParsedSection,
    ProfileDescriptor,
    SourceInput,
    SourceProfile,
)

from .strict_json import loads

_HEADING = re.compile(
    r"^###\s+((?:REQ|NFR|ADR|DES|TST)-[A-Z0-9][A-Z0-9-]*-[0-9]{3,})\s+[—-]\s+(.+?)\s*$",
    re.MULTILINE,
)
_JSON_BLOCK = re.compile(r"```raptor-json\s*\n(.*?)\n```", re.DOTALL)


def _paragraph(value: str) -> str:
    return " ".join(line.strip() for line in value.strip().splitlines() if line.strip())


class RaptorMarkdownProfile:
    profile_id = "raptor"
    profile_version = "1.0.0"

    def parse(self, source: SourceInput) -> ParsedDocument:
        try:
            text = source.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("RAPTOR.PROFILE.PARSE: Markdown must be UTF-8") from error
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
        for match in _JSON_BLOCK.finditer(text):
            sections.append(
                ParsedSection(
                    kind="JSON",
                    heading=None,
                    body=match.group(1),
                    location=SourceLocation(
                        start_line=text.count("\n", 0, match.start()) + 1,
                        start_column=1,
                    ),
                    attributes={},
                )
            )
        if not sections:
            raise ValueError("RAPTOR.PROFILE.PARSE: no Raptor artifacts found")
        return ParsedDocument(source=source, frontmatter={}, sections=tuple(sections))

    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]:
        return []

    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument:
        artifacts: list[object] = []
        repository_id = parsed.source.repository_id
        for section in parsed.sections:
            if section.kind == "JSON":
                value = loads(section.body)
                values = value if isinstance(value, list) else [value]
                artifacts.extend(values)
                continue
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
        return validate_json_object(document.model_dump(mode="json"))

    def normalize(self, document: SourceDocument) -> ComparableDocument:
        return ComparableDocument(
            schema_version=document.schema_version,
            origin=document.provenance.origin,
            artifacts=tuple(
                ArtifactSnapshot.from_artifact(artifact)
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
            raw_descriptor = loads(resolved.read_text())
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
    module_name, separator, class_name = descriptor.entrypoint.partition(":")
    raw_module_path = directory / module_name
    module_path = raw_module_path.resolve()
    if (
        not separator
        or not class_name
        or directory.resolve() not in module_path.parents
    ):
        raise ValueError("RAPTOR.PROFILE.ENTRYPOINT: invalid profile entrypoint")
    if raw_module_path.is_symlink() or not module_path.is_file():
        raise ValueError(
            "RAPTOR.PROFILE.ENTRYPOINT: profile module is not a regular file"
        )
    module_bytes = module_path.read_bytes()
    if hashlib.sha256(module_bytes).hexdigest() != descriptor.module_sha256:
        raise ValueError("RAPTOR.PROFILE.HASH: profile module hash mismatch")
    tree = ast.parse(module_bytes, filename=str(module_path))
    forbidden_roots = {"socket", "urllib", "http", "requests", "aiohttp", "ftplib"}
    if any(
        (
            isinstance(node, ast.Import)
            and any(
                item.name.split(".", 1)[0] in forbidden_roots for item in node.names
            )
        )
        or (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".", 1)[0] in forbidden_roots
        )
        for node in ast.walk(tree)
    ):
        raise ValueError(
            "RAPTOR.PROFILE.NETWORK: profile imports network-capable modules"
        )
    if any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"__import__", "eval", "exec"}
        for node in ast.walk(tree)
    ):
        raise ValueError("RAPTOR.PROFILE.NETWORK: dynamic loading is not permitted")
    spec = importlib.util.spec_from_file_location(
        f"raptor_external_{profile_id}_{descriptor.profile_version}", module_path
    )
    if spec is None or spec.loader is None:
        raise ValueError("RAPTOR.PROFILE.ENTRYPOINT: profile cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ValueError(
            "RAPTOR.PROFILE.ENTRYPOINT: profile module failed to load"
        ) from error
    implementation = getattr(module, class_name, None)
    if not isinstance(implementation, type):
        raise ValueError("RAPTOR.PROFILE.ENTRYPOINT: profile class is missing")
    try:
        profile = implementation()
    except Exception as error:
        raise ValueError(
            "RAPTOR.PROFILE.ENTRYPOINT: profile construction failed"
        ) from error
    required = (
        "parse",
        "validate",
        "canonicalize",
        "project_render_input",
        "normalize",
    )
    if any(not callable(getattr(profile, name, None)) for name in required):
        raise ValueError("RAPTOR.PROFILE.RETURN_TYPE: profile contract is incomplete")
    if (
        getattr(profile, "profile_id", None) != descriptor.profile_id
        or getattr(profile, "profile_version", None) != descriptor.profile_version
    ):
        raise ValueError("RAPTOR.PROFILE.RETURN_TYPE: profile identity differs")
    return cast(SourceProfile, profile)


__all__ = ["RaptorMarkdownProfile", "resolve_profile"]
