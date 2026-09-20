#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))
from runtime.bootstrap import bootstrap  # noqa: E402

bootstrap(PLUGIN_ROOT)
from runtime.cli import invoke  # noqa: E402
from runtime.operations import validate_json, validate_markdown, validate_sqlite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("markdown", "json", "sqlite"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input")
    parser.add_argument("--database")
    parser.add_argument("--profile", default="raptor")
    parser.add_argument("--profile-version")
    parser.add_argument("--allow-profile-code", action="store_true")
    parser.add_argument(
        "--reference-mode",
        choices=("structural", "document", "batch", "store"),
    )
    parser.add_argument("--format", choices=("json",), default="json")
    arguments = parser.parse_args()
    if arguments.kind == "markdown":
        return invoke(
            lambda: validate_markdown(
                arguments.repo_root,
                _required(arguments.input, "--input"),
                profile_id=arguments.profile,
                profile_version=arguments.profile_version,
                reference_mode=arguments.reference_mode or "document",
                database=arguments.database,
                allow_profile_code=arguments.allow_profile_code,
            )
        )
    if arguments.kind == "json":
        return invoke(
            lambda: validate_json(
                arguments.repo_root,
                _required(arguments.input, "--input"),
                reference_mode=arguments.reference_mode or "structural",
                database=arguments.database,
            )
        )
    return invoke(
        lambda: validate_sqlite(
            arguments.repo_root, _required(arguments.database, "--database")
        )
    )


def _required(value: str | None, option: str) -> str:
    if value is None:
        raise ValueError(f"RAPTOR.CLI.INPUT: {option} is required")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
