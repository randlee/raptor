from __future__ import annotations

from pathlib import Path

import pytest

from runtime import routes
from runtime.rendering import migration_round_trip


@pytest.mark.parametrize("family", ["requirement", "nfr", "adr", "design", "test-plan"])
@pytest.mark.parametrize("apply", [False, True])
def test_round_trip_composes_registered_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, apply: bool, family: str
) -> None:
    calls: list[dict[str, object]] = []

    def composed(*_args: object, **kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {"success": True, "data": {"composed": True}}

    monkeypatch.setattr(routes, "route", composed)
    result = migration_round_trip(
        tmp_path,
        f"docs/{family}.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
        backend=object(),
        apply=apply,
    )
    assert result["success"] is True
    assert len(calls) == 1
    params = calls[0]["params"]
    assert isinstance(params, dict) and params["apply"] is apply
    assert params["markdown_input"] == f"docs/{family}.md"


def test_round_trip_failure_short_circuits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = 0

    def failed(*_args: object, **_kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"success": False, "error": {"code": "RAPTOR.STEP.FAILED"}}

    monkeypatch.setattr(routes, "route", failed)
    result = migration_round_trip(
        tmp_path,
        "docs/input.md",
        "canonical.json",
        "raptor.sqlite",
        "export.json",
        "docs/output.md",
        backend=object(),
    )
    assert result["success"] is False and calls == 1
