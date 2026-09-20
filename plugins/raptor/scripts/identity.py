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
from runtime.identity import register_identity  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", type=Path, required=True)
    register.add_argument("--repository-id", required=True)
    register.add_argument("--document-id", required=True)
    register.add_argument("--path", required=True)
    mode = register.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    return invoke(
        lambda: register_identity(
            arguments.repo_root,
            repository_id=arguments.repository_id,
            document_id=arguments.document_id,
            repository_path=arguments.path,
            apply=arguments.apply,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
