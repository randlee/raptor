from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, cast

from raptor_schema import Artifact, ArtifactType, Diagnostic, DocumentSegment, JsonObject, LifecycleStatus, MaterializationProvenance, OriginProvenance, SourceDocument, SourceLocation, SourceProvenance, Subsection, Relationship, validate_json_object
from raptor_schema.profiles import ArtifactSnapshot, ComparableDocument, FrozenJsonObject, ParsedDocument, ParsedSection, ProfileDescriptor, SourceInput, SourceProfile

from .io import read_repository_bytes

_ITEM = re.compile(r"^##[ \t]+(?P<id>(?P<kind>REQ|NFR|ADR)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}):[ \t]*(?P<title>.+?)[ \t]*$", re.MULTILINE)
_TITLE = re.compile(r"^#[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)
_STATUS = re.compile(r"^\*\*Status:\*\*[ \t]*(?P<status>[^\r\n]+)[ \t]*$", re.MULTILINE)
_SUBSECTION = re.compile(r"^(?P<marks>#{3,6})[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)
_REFERENCE = re.compile(r"(?P<id>(?:REQ|NFR|ADR|TEST)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,})")
_TEST_PLAN_ID = re.compile(r"^\*\*Test Plan ID:\*\*[ \t]*(?P<value>[^\r\n]+)[ \t]*$", re.MULTILINE)
_TEST_PLAN_RANGE = re.compile(r"^(?P<start>TEST-[A-Z0-9][A-Z0-9-]*-[0-9]{4,})[ \t]+(?:through|to)[ \t]+TEST-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}$", re.IGNORECASE)
_TEST_PLAN_SINGLE = re.compile(r"^TEST-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}$", re.IGNORECASE)
_KINDS = {
    "REQ": ArtifactType.REQUIREMENT,
    "NFR": ArtifactType.NON_FUNCTIONAL_REQUIREMENT,
    "ADR": ArtifactType.ARCHITECTURE_DECISION,
}
_ROUTED_DOCUMENT_FAMILIES = {
    ArtifactType.DESIGN_DOCUMENT,
    ArtifactType.TEST_PLAN,
}


def _normal(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"


def _metadata(text: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for name, value in re.findall(r"^\*\*(.+?):\*\*\s*(.*?)\s*$", text, re.MULTILINE):
        values[name.strip()] = value
    return values


def _preamble(text: str) -> str:
    first_section = re.search(r"^#{2,6}[ \t]+", text, re.MULTILINE)
    return text[: first_section.start()] if first_section else text


def _test_plan_identifier(preamble: str, document_id: str) -> tuple[str, str | None]:
    match = _TEST_PLAN_ID.search(preamble)
    if match is None:
        return document_id, None
    value = match.group("value").strip()
    range_match = _TEST_PLAN_RANGE.fullmatch(value)
    if range_match is not None:
        return range_match.group("start").upper(), value
    if _TEST_PLAN_SINGLE.fullmatch(value) is not None:
        return value.upper(), None
    return document_id, None


def _subsections(content: str) -> list[Subsection]:
    return [
        Subsection(title=match.group("title"), level=len(match.group("marks")), markdown=match.group(0), ordinal=index)
        for index, match in enumerate(_SUBSECTION.finditer(content))
    ]


def _relationships(content: str) -> list[Relationship]:
    result: list[Relationship] = []
    for match in _REFERENCE.finditer(content):
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        context = content[line_start:None if line_end == -1 else line_end]
        result.append(Relationship(relation_type="references", target_token=match.group("id"), context=context))
    return result


class RaptorMarkdownProfile:
    """The sole built-in extractor for the v2 reference Markdown grammar."""

    def __init__(self, profile_id: str = "raptor", profile_version: str = "2.0.0") -> None:
        self.profile_id = profile_id
        self.profile_version = profile_version

    def parse(self, source: SourceInput) -> ParsedDocument:
        try:
            text = _normal(source.content.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ValueError("RAPTOR.REFERENCE.INVALID_UTF8") from error
        if source.routed_artifact_type in _ROUTED_DOCUMENT_FAMILIES:
            return ParsedDocument(
                source=source,
                frontmatter=cast(FrozenJsonObject, validate_json_object({"markdown": text})),
                sections=(
                    ParsedSection(
                        kind=source.routed_artifact_type.value,
                        heading=None,
                        body=text,
                        location=SourceLocation(
                            start_line=1,
                            start_column=1,
                            end_line=text.count("\n") + 1,
                            end_column=1,
                        ),
                        attributes={"ordinal": 0},
                    ),
                ),
            )
        malformed = re.search(r"^##\s+(?:REQ|NFR|ADR)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}\s+[^:]", text, re.MULTILINE)
        if malformed:
            line = text.count("\n", 0, malformed.start()) + 1
            raise ValueError(f"RAPTOR.REFERENCE.MALFORMED_HEADING: line {line}")
        matches = list(_ITEM.finditer(text))
        if not matches:
            raise ValueError("RAPTOR.REFERENCE.NO_ITEM")
        seen: set[str] = set()
        sections: list[ParsedSection] = []
        for index, match in enumerate(matches):
            artifact_id = match.group("id")
            if artifact_id in seen:
                raise ValueError("RAPTOR.REFERENCE.DUPLICATE_HEADING")
            seen.add(artifact_id)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end():end]
            sections.append(ParsedSection(kind=match.group("kind"), heading=match.group("title"), body=body, location=SourceLocation(start_line=text.count("\n", 0, match.start()) + 1, start_column=1, end_line=text.count("\n", 0, end) + 1, end_column=1), attributes={"artifact_id": artifact_id, "ordinal": index}))
        return ParsedDocument(source=source, frontmatter=cast(FrozenJsonObject, validate_json_object({"markdown": text})), sections=tuple(sections))

    def validate(self, parsed: ParsedDocument) -> list[Diagnostic]:
        return []

    def canonicalize(self, parsed: ParsedDocument) -> SourceDocument:
        text = str(parsed.frontmatter["markdown"])
        matches = list(_ITEM.finditer(text))
        title_match = _TITLE.search(text)
        segments: list[DocumentSegment] = []
        artifacts: list[Artifact] = []
        if parsed.source.routed_artifact_type in _ROUTED_DOCUMENT_FAMILIES:
            preamble = _preamble(text)
            metadata = _metadata(preamble)
            artifact_id = parsed.source.document_id
            if parsed.source.routed_artifact_type is ArtifactType.TEST_PLAN:
                artifact_id, id_range = _test_plan_identifier(
                    preamble, parsed.source.document_id
                )
                if id_range is not None:
                    metadata["id_range"] = id_range
            status_match = _STATUS.search(preamble)
            whole_status = (
                LifecycleStatus(status_match.group("status").strip())
                if status_match is not None
                and status_match.group("status").strip()
                in {item.value for item in LifecycleStatus}
                else None
            )
            artifacts.append(
                Artifact(
                    artifact_type=parsed.source.routed_artifact_type,
                    id=artifact_id,
                    title=title_match.group("title") if title_match else parsed.source.document_id,
                    status=whole_status,
                    domain=parsed.source.repository_path.parts[0]
                    if len(parsed.source.repository_path.parts) > 1
                    else None,
                    source={"ordinal": 0, "start_line": 1, "end_line": text.count("\n") + 1},
                    content=text,
                    relationships=_relationships(text),
                    subsections=_subsections(text),
                    source_location=parsed.sections[0].location,
                )
            )
            digest = hashlib.sha256(text.encode()).hexdigest()
            path = parsed.source.repository_path.as_posix()
            return SourceDocument(
                provenance=SourceProvenance(
                    origin=OriginProvenance(repository_id=parsed.source.repository_id, document_id=parsed.source.document_id, initial_repository_path=path, original_content_sha256=digest, source_format="markdown", parser_profile=self.profile_id, parser_profile_version=self.profile_version),
                    materialization=MaterializationProvenance(repository_path=path, content_sha256=digest, operation="imported", parser_profile=self.profile_id, parser_profile_version=self.profile_version),
                ),
                title=title_match.group("title") if title_match else None,
                document_metadata=metadata,
                non_item_segments=segments,
                artifacts=artifacts,
            )
        cursor = 0
        sections = parsed.sections
        for index, (match, section) in enumerate(zip(matches, sections, strict=True)):
            if match.start() > cursor:
                segments.append(DocumentSegment(kind="text", content=text[cursor:match.start()]))
            content = section.body
            status_match = _STATUS.search(content)
            status: LifecycleStatus | None = None
            if status_match:
                try:
                    status = LifecycleStatus(status_match.group("status").strip())
                except ValueError as error:
                    raise ValueError("RAPTOR.REFERENCE.UNSUPPORTED_STATUS") from error
            artifacts.append(Artifact(artifact_type=_KINDS[section.kind], id=str(section.attributes["artifact_id"]), title=section.heading or "", status=status, domain=parsed.source.repository_path.parts[0] if len(parsed.source.repository_path.parts) > 1 else None, source={"ordinal": index, "start_line": section.location.start_line, "end_line": section.location.end_line}, content=content, relationships=_relationships(content), subsections=_subsections(content), source_location=section.location))
            segments.append(DocumentSegment(kind="artifact", artifact_index=index))
            cursor = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if cursor < len(text):
            segments.append(DocumentSegment(kind="text", content=text[cursor:]))
        digest = hashlib.sha256(text.encode()).hexdigest()
        path = parsed.source.repository_path.as_posix()
        return SourceDocument(provenance=SourceProvenance(origin=OriginProvenance(repository_id=parsed.source.repository_id, document_id=parsed.source.document_id, initial_repository_path=path, original_content_sha256=digest, source_format="markdown", parser_profile=self.profile_id, parser_profile_version=self.profile_version), materialization=MaterializationProvenance(repository_path=path, content_sha256=digest, operation="imported", parser_profile=self.profile_id, parser_profile_version=self.profile_version)), title=title_match.group("title") if title_match else None, document_metadata=_metadata(text[:matches[0].start()] if matches else text), non_item_segments=segments, artifacts=artifacts)

    def project_render_input(self, document: SourceDocument) -> JsonObject:
        artifacts = [item.model_dump(mode="json", exclude_none=True) for item in document.artifacts]
        segments: list[dict[str, Any]] = []
        for segment in document.non_item_segments:
            rendered = segment.model_dump(mode="json", exclude_none=True)
            if segment.kind == "artifact":
                artifact = artifacts[segment.artifact_index or 0]
                rendered["artifact"] = artifact
                rendered["markdown"] = f"## {artifact['id']}: {artifact['title']}{artifact['content']}"
            segments.append(rendered)
        return validate_json_object({"document": {"title": document.title, "metadata": document.document_metadata, "segments": segments}, "artifacts": artifacts})

    def normalize(self, document: SourceDocument) -> ComparableDocument:
        return ComparableDocument(schema_version=document.schema_version, origin=document.provenance.origin, artifacts=tuple(ArtifactSnapshot.from_artifact(item) for item in document.artifacts))


def bundled_profile() -> RaptorMarkdownProfile:
    return RaptorMarkdownProfile()


def resolve_profile(repository_root: Path, profile_id: str, profile_version: str | None = None, *, allow_profile_code: bool = False) -> SourceProfile:
    del allow_profile_code
    if profile_id != "raptor" or (profile_version is not None and profile_version != "2.0.0"):
        raise ValueError("RAPTOR.PROFILE.NOT_FOUND: only the built-in reference profile is available")
    return RaptorMarkdownProfile()


def profile_descriptor() -> ProfileDescriptor:
    content = read_repository_bytes(Path(__file__).resolve().parents[1], "runtime/profiles.py")
    return ProfileDescriptor(profile_id="raptor", profile_version="2.0.0", api_version="1", entrypoint="runtime.profiles:RaptorMarkdownProfile", module_sha256=hashlib.sha256(content).hexdigest())


__all__ = ["RaptorMarkdownProfile", "bundled_profile", "profile_descriptor", "resolve_profile"]
