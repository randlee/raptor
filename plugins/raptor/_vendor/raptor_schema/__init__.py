from pathlib import Path

from .canonical import dump_canonical_json, load_canonical_json
from .models import *  # noqa: F403
from .profiles import ArtifactSnapshot, ComparableDocument, FrozenJsonObject, FrozenJsonValue, ParsedDocument, ParsedSection, ProfileDescriptor, SourceInput, SourceProfile, validate_json_object
from .storage import ArtifactStore, SQLiteArtifactStore, StorageError, TraceabilityRelationship, TraceabilityRelationships, document_key


def generate_json_schemas(output_dir: Path, *, check: bool = False) -> None:
    from .generate import generate_json_schemas as _generate

    _generate(output_dir, check=check)


__all__ = [
    "ArtifactStore", "SQLiteArtifactStore", "StorageError", "TraceabilityRelationship", "TraceabilityRelationships", "document_key", "dump_canonical_json", "load_canonical_json", "generate_json_schemas",
    "ArtifactSnapshot", "ComparableDocument", "FrozenJsonObject", "FrozenJsonValue", "ParsedDocument", "ParsedSection", "ProfileDescriptor", "SourceInput", "SourceProfile", "validate_json_object",
    *[name for name in __import__("raptor_schema.models", fromlist=["__all__"]).__all__],
]
