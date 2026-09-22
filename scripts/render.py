#!/usr/bin/env python3
"""Render records from a Raptor JSON index to Markdown using Jinja2 templates."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path); parser.add_argument("--id")
    parser.add_argument("--templates", type=Path, default=Path(__file__).parents[1] / "templates")
    parser.add_argument("--output-dir", type=Path, default=Path("rendered")); args = parser.parse_args()
    try: from jinja2 import Environment, FileSystemLoader
    except ImportError: parser.error("render.py requires Jinja2 (pip install Jinja2)")
    items = json.loads(args.index.read_text(encoding="utf-8")).get("requirements", [])
    if args.id:
        matches = [item for item in items if item["id"] == args.id]
        if not matches: parser.error(f"no record with id {args.id}")
        items = [matches[0]]
    environment = Environment(loader=FileSystemLoader(args.templates), keep_trailing_newline=True, autoescape=False)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        name = {"REQ": "requirement.md.j2", "NFR": "nfr.md.j2", "ADR": "adr.md.j2"}.get(item["type"], "requirement.md.j2")
        (args.output_dir / f"{item['id']}.md").write_text(environment.get_template(name).render(record=item), encoding="utf-8")
    print(f"rendered={len(items)} output={args.output_dir}"); return 0
if __name__ == "__main__": raise SystemExit(main())
