#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.vendor import check, refresh  # noqa: E402
from runtime.cli import invoke  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    return invoke(lambda: _run(root, arguments.check))


def _run(root: Path, check_only: bool) -> dict[str, Any] | None:
    if check_only:
        check(root)
        return None
    return refresh(root)


if __name__ == "__main__":
    raise SystemExit(main())
