#!/usr/bin/env python3
"""Render records from a Raptor JSON index through sc-compose templates."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

TEMPLATES = {
    "REQ": "requirement.md.j2",
    "NFR": "nfr.md.j2",
    "ADR": "adr.md.j2",
    "DESIGN": "design.md.j2",
    "TEST": "test-plan.md.j2",
}


def output_path(record: dict, output_dir: Path) -> Path:
    directory = output_dir / record.get("domain", "default")
    candidate = directory / f"{record['id']}.md"
    if not candidate.exists():
        return candidate
    stem = Path(record.get("source", {}).get("file", record["id"])).stem
    candidate = directory / f"{record['id']}-{stem}.md"
    suffix = 2
    while candidate.exists():
        candidate = directory / f"{record['id']}-{stem}-{suffix}.md"
        suffix += 1
    return candidate


def render(record: dict, templates: Path, output_dir: Path) -> Path:
    template = templates / TEMPLATES.get(record["type"], "requirement.md.j2")
    destination = output_path(record, output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as variables:
        json.dump({"record": record}, variables)
        variable_path = Path(variables.name)
    try:
        subprocess.run(
            ["sc-compose", "render", "--root", str(templates.parent), "--file", str(template),
             "--var-file", str(variable_path), "--output", str(destination)],
            check=True,
        )
    finally:
        variable_path.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", type=Path)
    parser.add_argument("--id")
    parser.add_argument("--templates", type=Path, default=Path(__file__).parents[1] / "templates")
    parser.add_argument("--output-dir", type=Path, default=Path("rendered"))
    args = parser.parse_args()
    records = json.loads(args.index.read_text(encoding="utf-8")).get("requirements", [])
    if args.id:
        records = [record for record in records if record["id"] == args.id]
        if not records:
            parser.error(f"no record with id {args.id}")
    for record in records:
        print(render(record, args.templates, args.output_dir))
    print(f"rendered={len(records)} output={args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
