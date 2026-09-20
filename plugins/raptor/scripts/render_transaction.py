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
from raptor_schema import DocumentKey  # noqa: E402
from runtime.cli import invoke  # noqa: E402
from runtime.transactions import recover_render_transaction  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--document-id", required=True)
    arguments = parser.parse_args()
    return invoke(
        lambda: recover_render_transaction(
            arguments.repo_root,
            DocumentKey(
                repository_id=arguments.repository_id,
                document_id=arguments.document_id,
            ),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
