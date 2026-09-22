from __future__ import annotations

import pytest
from pydantic import ValidationError

from raptor_schema import IngressDiagnostic, IngressReport, IngressReportEntry


def imported(path: str) -> IngressReportEntry:
    return IngressReportEntry(
        repository_path=path,
        outcome="imported",
        document_id="DOC-RAP-001",
        route="requirements",
        profile={"profile_id": "raptor", "profile_version": "1.0.0"},
        canonical_digest="a" * 64,
        sqlite_outcome="validated",
        field_count=3,
        relationship_count=0,
        origin_digest="b" * 64,
        materialization_digest="c" * 64,
    )


def report(*entries: IngressReportEntry) -> IngressReport:
    return IngressReport(
        report_version="1.0.0",
        repository_id="urn:raptor:repo:raptor",
        config_path=".raptor/raptor.toml",
        database_path=".raptor/state/ingress.sqlite",
        entries=entries,
    )


def test_imported_and_diagnosed_entries_are_explicit_terminal_outcomes() -> None:
    diagnostic = IngressReportEntry(
        repository_path="specifications/unsupported.md",
        outcome="diagnosed",
        sqlite_outcome="not_attempted",
        diagnostic=IngressDiagnostic(
            code="RAPTOR.INGRESS.ERROR", message="input was diagnosed"
        ),
    )

    result = report(imported("specifications/requirements.md"), diagnostic)

    assert [entry.outcome for entry in result.entries] == ["imported", "diagnosed"]


def test_report_rejects_unsorted_or_incomplete_terminal_entries() -> None:
    with pytest.raises(ValidationError, match="unique sorted"):
        report(imported("specifications/z.md"), imported("specifications/a.md"))
    with pytest.raises(ValidationError, match="requires canonical ingress details"):
        IngressReportEntry(
            repository_path="specifications/requirements.md",
            outcome="imported",
            sqlite_outcome="validated",
        )
    with pytest.raises(ValidationError, match="requires a diagnostic"):
        IngressReportEntry(
            repository_path="specifications/requirements.md",
            outcome="diagnosed",
            sqlite_outcome="not_attempted",
        )
