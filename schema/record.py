"""The record shape emitted by the corpus extractor."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DocumentMetadata(StrictModel):
    created: str
    last_updated: str
    owner: str
    id_range: str
    range_description: str | None


class Source(StrictModel):
    file: str
    section_line: int


class Content(StrictModel):
    markdown: str
    html: str
    summary: str


class Reference(StrictModel):
    target_id: str
    type: str
    context: str


class ReferencedBy(StrictModel):
    source_id: str
    type: str
    context: str


class Family(StrictModel):
    id_range: str
    members_count: int


class Relationships(StrictModel):
    references: list[Reference]
    referenced_by: list[ReferencedBy]
    family: Family


class Subsection(StrictModel):
    heading: str
    level: int
    content_length: int


class Record(StrictModel):
    id: str
    title: str
    type: Literal["REQ", "NFR", "ADR"]
    status: str | None
    domain: str
    document_metadata: DocumentMetadata
    source: Source
    content: Content
    relationships: Relationships
    subsections: list[Subsection]
