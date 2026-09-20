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
from runtime.operations import export_sqlite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--output", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    return invoke(
        lambda: export_sqlite(
            arguments.repo_root,
            arguments.database,
            arguments.repository_id,
            arguments.document_id,
            arguments.output,
            apply=arguments.apply,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
