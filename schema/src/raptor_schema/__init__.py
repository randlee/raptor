from pathlib import Path

from .canonical import (
    ArtifactResolver,
    ReferenceValidationError,
    ReferenceValidationMode,
    dump_canonical_json,
    load_canonical_json,
    validate_document,
    validate_documents,
)
from .models import *
from .profiles import (
    ComparableDocument,
    ParsedDocument,
    ParsedSection,
    ProfileDescriptor,
    ProfileError,
    ResolvedProfile,
    SourceInput,
    SourceProfile,
    canonicalize_with_profile,
    load_profile,
    parse_with_profile,
    resolve_profile_descriptor,
    validate_with_profile,
)


def generate_json_schemas(output_dir: Path, *, check: bool = False) -> None:
    """Generate versioned schemas without importing the CLI module eagerly."""
    from .generate import generate_json_schemas as _generate

    return _generate(output_dir, check=check)

__all__ = [name for name in globals() if not name.startswith("_")]
