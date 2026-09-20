#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.plugin_validation import validate_plugin  # noqa: E402
from runtime.cli import invoke  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--guideline",
        type=Path,
        default=Path(__file__).resolve().parents[3]
        / "docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md",
    )
    parser.add_argument("--check-frontmatter", action="store_true")
    parser.add_argument("--check-registry", action="store_true")
    parser.add_argument("--check-manifests", action="store_true")
    parser.add_argument("--check-inventory", action="store_true")
    parser.add_argument("--check-vendor", action="store_true")
    parser.add_argument("--check-templates", action="store_true")
    parser.add_argument("--check-cli")
    parser.add_argument("--expected-range")
    arguments = parser.parse_args()
    return invoke(
        lambda: validate_plugin(
            Path(__file__).resolve().parents[1],
            arguments.guideline,
            check_cli=arguments.check_cli,
            expected_range=arguments.expected_range,
            check_templates=arguments.check_templates,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
