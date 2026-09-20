from __future__ import annotations

import json
from pathlib import Path

import pytest

from raptor_schema import SourceDocument

CORPUS = Path(__file__).parent / "corpus"


@pytest.fixture
def document_dict() -> dict[str, object]:
    return json.loads((CORPUS / "all-families.json").read_text(encoding="utf-8"))


@pytest.fixture
def document(document_dict: dict[str, object]) -> SourceDocument:
    return SourceDocument.model_validate(document_dict)
