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
from runtime.operations import configured_markdown_to_sqlite, markdown_to_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="raptor")
    parser.add_argument("--profile-version")
    parser.add_argument("--allow-profile-code", action="store_true")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--database")
    parser.add_argument("--config")
    parser.add_argument("--report")
    parser.add_argument(
        "--reference-mode",
        choices=("structural", "document", "batch", "store"),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    if arguments.config is not None:
        if arguments.input is not None or arguments.output is not None:
            parser.error("--config mode does not accept --input or --output")
        if arguments.database is None or arguments.report is None:
            parser.error("--config mode requires --database and --report")
        if arguments.reference_mode is not None:
            parser.error("--config mode selects batch reference mode")
        return invoke(
            lambda: configured_markdown_to_sqlite(
                arguments.repo_root,
                arguments.config,
                arguments.database,
                arguments.report,
                allow_profile_code=arguments.allow_profile_code,
                apply=arguments.apply,
            )
        )
    if arguments.input is None or arguments.output is None:
        parser.error("--input and --output are required without --config")
    if arguments.report is not None:
        parser.error("--report requires --config")
    return invoke(
        lambda: markdown_to_json(
            arguments.repo_root,
            arguments.input,
            arguments.output,
            profile_id=arguments.profile,
            profile_version=arguments.profile_version,
            reference_mode=arguments.reference_mode,
            database=arguments.database,
            allow_profile_code=arguments.allow_profile_code,
            apply=arguments.apply,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
