#!/usr/bin/env python3
"""Build a Raptor index from the configured Markdown inventory."""
from __future__ import annotations

import argparse
import json
import re
import tomllib
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

import raptor_schema

HEADING = re.compile(r"^##\s+([A-Z]+-[A-Z]{2,5}-\d{4}):\s*(.*)$")
LABEL = re.compile(r"^\*\*([^*]+):\*\*(?:\s*(.*))?$")
ITEM = re.compile(r"^(?:[-*]|\d+\.)\s+(.+)$")


def add_text(target: dict | None, value: str, line: int, item: bool = False) -> None:
    if target and value:
        target.setdefault("items" if item else "prose", []).append({"text": value, "line": line})


def split(path: Path, text: str) -> dict:
    """Invert the template grammar without knowing any schema field names."""
    tree, record, section, group, label = {"path": str(path), "header": {}, "records": []}, None, None, None, None
    header, fenced = True, False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("```"):
            fenced = not fenced
            add_text(label if label else group if group else section, raw, number)
            continue
        if not fenced and line.startswith("# "):
            continue
        if not fenced and (line == "---" or line.startswith("## ")):
            header = False
        if not fenced and (match := HEADING.match(line)):
            record = {"id": match.group(1), "title": match.group(2), "line": number, "fields": {}, "sections": []}
            tree["records"].append(record)
            section = group = label = None
            continue
        if not fenced and line.startswith("## "):
            record = section = group = label = None
            continue
        if not fenced and record and line.startswith("### "):
            section = {"name": line[4:].strip(), "line": number, "prose": [], "labels": [], "groups": []}
            record["sections"].append(section)
            group = label = None
            continue
        if not fenced and section and line.startswith("#### "):
            group = {"name": line[5:].strip(), "line": number, "prose": [], "labels": []}
            section["groups"].append(group)
            label = None
            continue
        match = None if fenced else LABEL.match(line)
        if match:
            entry = {"name": match.group(1), "line": number, "prose": [], "items": []}
            value = (match.group(2) or "").rstrip()
            if header:
                tree["header"][entry["name"]] = {"value": value, "line": number}
            elif record and not section:
                record["fields"][entry["name"]] = {"value": value, "line": number}
            elif section:
                (group if group else section)["labels"].append(entry)
                label = entry
                add_text(label, value, number)
            continue
        if line:
            item = ITEM.match(line)
            add_text(label if label else group if group else section, item.group(1) if item else raw, number, bool(item))
    return tree


def inventory(root: Path, sources: dict) -> list[Path]:
    files: set[Path] = set()
    for source in sources.get("sources", []):
        base = root / source["root"]
        include, exclude = source.get("include", ["**/*.md"]), source.get("exclude", [])
        for file in base.rglob("*.md") if base.exists() else []:
            relative = file.relative_to(base).as_posix()
            match = lambda patterns: any(fnmatch(relative, pattern) or (pattern.startswith("**/") and fnmatch(relative, pattern[3:])) for pattern in patterns)
            if match(include) and not match(exclude):
                files.add(file)
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    config = root / ".raptor"
    repository = tomllib.loads((config / "raptor.toml").read_text())["repository_id"]
    files = inventory(root, tomllib.loads((config / "sources.toml").read_text()))
    requirements, decisions, issues = [], [], []
    for file in files:
        bound = json.loads(raptor_schema.bind_file(json.dumps(split(file.relative_to(root), file.read_text()))))
        requirements.extend(bound["requirements"])
        decisions.extend(bound["decisions"])
        issues.extend(bound["diagnostics"])
    issues.extend(json.loads(raptor_schema.check_inventory(json.dumps(requirements), json.dumps(decisions))))
    issues.sort(key=lambda issue: (issue["file"], issue["line"]))
    payload = {"metadata": {"repository": repository, "generated": datetime.now(timezone.utc).isoformat(), "files": len(files), "records": len(requirements) + len(decisions)}, "requirements": requirements, "decisions": decisions, "diagnostics": {"issues": issues, "summary": json.loads(raptor_schema.summarize(json.dumps(issues)))}}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"index": str(args.output), "files": len(files), "records": payload["metadata"]["records"], "issues": len(issues)}))
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
