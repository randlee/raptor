#!/usr/bin/env python3
"""Render a Raptor index through its schema-driven templates."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import raptor_schema
import sc_compose as sc


def render(record: dict, table: str, templates: Path, output: Path) -> None:
    fields = json.loads(raptor_schema.field_table(table))
    template = "decision.md.j2" if table == "decisions" else "requirement.md.j2"
    request = sc.ComposeRequest(root=templates.parent, mode=sc.ComposeMode.file(f"{templates.name}/{template}"), vars_input={"record": record, "fields": fields})
    target = output / table / f"{record['id']}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(sc.compose_file(request).rendered_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("rendered"))
    parser.add_argument("--templates", type=Path, default=Path(__file__).parents[1] / "templates")
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    for table in ("requirements", "decisions"):
        for record in index.get(table, []):
            render(record, table, args.templates, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
