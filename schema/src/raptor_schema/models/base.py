from __future__ import annotations

import math
from typing import Annotated, TypeAlias

from pydantic import AfterValidator, BaseModel, ConfigDict, JsonValue, StringConstraints, WithJsonSchema

_SCHEMA_VERSION_BODY = (
    r"(?:[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
_CANONICAL_SCHEMA_VERSION_BODY = _SCHEMA_VERSION_BODY
_PROFILE_ID_BODY = r"[a-z][a-z0-9_-]*"
_REPOSITORY_ID_BODY = r"urn:raptor:repo:[a-z0-9][a-z0-9._-]{2,127}"


def _python_pattern(body: str) -> str:
    return rf"^{body}\Z"


def _pydantic_pattern(body: str) -> str:
    return rf"^{body}\z"


def _json_schema_pattern(body: str) -> str:
    return rf"^{body}(?![\s\S])"


SCHEMA_VERSION_RE = _python_pattern(_SCHEMA_VERSION_BODY)
SCHEMA_VERSION_JSON_RE = _json_schema_pattern(_SCHEMA_VERSION_BODY)
CANONICAL_SCHEMA_VERSION_RE = _python_pattern(_CANONICAL_SCHEMA_VERSION_BODY)
CANONICAL_SCHEMA_VERSION_JSON_RE = _json_schema_pattern(
    _CANONICAL_SCHEMA_VERSION_BODY
)
REPOSITORY_ID_RE = _python_pattern(_REPOSITORY_ID_BODY)
DOCUMENT_ID_RE = r"^DOC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$"
ARTIFACT_ID_RE = r"^(?:(?:REQ|NFR|ADR)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}|TEST-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}|DOC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,})$"
SHA256_RE = r"^[0-9a-f]{64}$"
EXTENSION_KEY_RE = r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_-]*)+$"
PROFILE_ID_RE = _python_pattern(_PROFILE_ID_BODY)
DIAGNOSTIC_CODE_RE = r"^[A-Z][A-Z0-9]*(\.[A-Z][A-Z0-9_]*)+$"
TEST_CASE_ID_RE = r"^TC-[A-Z0-9][A-Z0-9-]*-[0-9]{3,}$"


def _trim(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


def _repository_path(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("must be a non-empty repository-relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("path may not contain empty, '.' or '..' segments")
    return value


SchemaVersion = Annotated[
    str,
    StringConstraints(pattern=_pydantic_pattern(_CANONICAL_SCHEMA_VERSION_BODY)),
    WithJsonSchema({"type": "string", "pattern": CANONICAL_SCHEMA_VERSION_JSON_RE}),
]
ProfileVersion = Annotated[
    str,
    StringConstraints(pattern=_pydantic_pattern(_SCHEMA_VERSION_BODY)),
    WithJsonSchema({"type": "string", "pattern": SCHEMA_VERSION_JSON_RE}),
]
RepositoryId = Annotated[
    str,
    StringConstraints(pattern=_pydantic_pattern(_REPOSITORY_ID_BODY)),
    WithJsonSchema(
        {"type": "string", "pattern": _json_schema_pattern(_REPOSITORY_ID_BODY)}
    ),
]
DocumentId = Annotated[str, StringConstraints(pattern=DOCUMENT_ID_RE)]
ArtifactId = Annotated[str, StringConstraints(pattern=ARTIFACT_ID_RE)]
Sha256 = Annotated[str, StringConstraints(pattern=SHA256_RE)]
ExtensionKey = Annotated[str, StringConstraints(pattern=EXTENSION_KEY_RE)]
ProfileId = Annotated[
    str,
    StringConstraints(pattern=_pydantic_pattern(_PROFILE_ID_BODY)),
    WithJsonSchema(
        {"type": "string", "pattern": _json_schema_pattern(_PROFILE_ID_BODY)}
    ),
]
DiagnosticCode = Annotated[str, StringConstraints(pattern=DIAGNOSTIC_CODE_RE)]
TestCaseId = Annotated[str, StringConstraints(pattern=TEST_CASE_ID_RE)]
RepositoryPath = Annotated[
    str,
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "pattern": r"^(?!/)(?!\.{1,2}(?:/|$))(?!.*(?:/\.{1,2})(?:/|$))(?!.*//)(?!.*\/$)(?!.*\\).+$",
        }
    ),
    AfterValidator(_repository_path),
]
Title = Annotated[
    str,
    StringConstraints(min_length=1, max_length=200, pattern=r"\S"),
    AfterValidator(_trim),
]
NonEmptyText = Annotated[
    str, StringConstraints(min_length=1, pattern=r"\S"), AfterValidator(_trim)
]
JsonObject: TypeAlias = dict[str, JsonValue]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


def reject_non_finite(value: JsonValue) -> JsonValue:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("float values must be finite")
    if isinstance(value, list):
        return [reject_non_finite(item) for item in value]
    if isinstance(value, dict):
        return {key: reject_non_finite(item) for key, item in value.items()}
    return value


__all__ = [
    "ARTIFACT_ID_RE",
    "DIAGNOSTIC_CODE_RE",
    "DOCUMENT_ID_RE",
    "EXTENSION_KEY_RE",
    "PROFILE_ID_RE",
    "REPOSITORY_ID_RE",
    "SCHEMA_VERSION_RE",
    "SHA256_RE",
    "TEST_CASE_ID_RE",
    "ArtifactId",
    "ContractModel",
    "DiagnosticCode",
    "DocumentId",
    "ExtensionKey",
    "JsonObject",
    "NonEmptyText",
    "ProfileId",
    "ProfileVersion",
    "RepositoryId",
    "RepositoryPath",
    "SchemaVersion",
    "Sha256",
    "TestCaseId",
    "Title",
    "reject_non_finite",
]
