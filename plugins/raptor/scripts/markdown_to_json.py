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
from runtime.operations import markdown_to_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="raptor")
    parser.add_argument("--profile-version")
    parser.add_argument("--allow-profile-code", action="store_true")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--database")
    parser.add_argument(
        "--reference-mode",
        choices=("structural", "document", "batch", "store"),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
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
