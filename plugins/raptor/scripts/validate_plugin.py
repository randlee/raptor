#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.plugin_validation import validate_plugin  # noqa: E402
from runtime.cli import invoke  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guideline", type=Path, required=True)
    parser.add_argument("--check-frontmatter", action="store_true")
    parser.add_argument("--check-registry", action="store_true")
    parser.add_argument("--check-manifests", action="store_true")
    parser.add_argument("--check-inventory", action="store_true")
    parser.add_argument("--check-vendor", action="store_true")
    arguments = parser.parse_args()
    return invoke(
        lambda: _validate(Path(__file__).resolve().parents[1], arguments.guideline)
    )


def _validate(root: Path, guideline: Path) -> None:
    validate_plugin(root, guideline)


if __name__ == "__main__":
    raise SystemExit(main())
