from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from .models import (
    Artifact,
    IdentityManifest,
    RepositoryRoutingConfig,
    RepositoryScanConfig,
    SourceDocument,
)


def _schemas() -> dict[str, dict[str, object]]:
    return {
        "artifact.schema.json": TypeAdapter(Artifact).json_schema(),
        "identity-manifest.schema.json": IdentityManifest.model_json_schema(),
        "repository-scan-config.schema.json": RepositoryScanConfig.model_json_schema(),
        "repository-routing-config.schema.json": RepositoryRoutingConfig.model_json_schema(),
        "source-document.schema.json": SourceDocument.model_json_schema(),
    }


def _render(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def generate_json_schemas(output_dir: Path, *, check: bool = False) -> None:
    mismatches: list[str] = []
    if not check:
        output_dir.mkdir(parents=True, exist_ok=True)
    for name, schema in _schemas().items():
        target = output_dir / name
        content = _render(schema)
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                mismatches.append(str(target))
        else:
            target.write_text(content, encoding="utf-8")
    if check:
        expected = set(_schemas())
        actual = {path.name for path in output_dir.glob("*.schema.json")}
        mismatches.extend(str(output_dir / name) for name in sorted(actual - expected))
    if mismatches:
        raise SystemExit("generated schema drift: " + ", ".join(mismatches))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate_json_schemas(args.output, check=args.check)


if __name__ == "__main__":
    main()
