#!/usr/bin/env python3
"""Render a Raptor index through its schema-driven template."""

import argparse
import json
from pathlib import Path

if __package__:
    from .markdown_renderer import render
    from .schema_json import schemas
else:
    from markdown_renderer import render
    from schema_json import schemas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("rendered"))
    parser.add_argument("--templates", type=Path, default=Path(__file__).parents[1] / "templates")
    args = parser.parse_args()
    index, definitions = json.loads(args.index.read_text()), schemas()
    for table in definitions:
        for record in index.get(table, []):
            render(record, table, args.templates, args.output_dir, definitions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
