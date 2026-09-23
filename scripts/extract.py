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
if __package__:
    from .qualify import Qualifier
else:
    from qualify import Qualifier

HEADING = re.compile(r"^##\s+([A-Z]+-[A-Z]{2,5}-\d{4}):\s*(.*)$")
LABEL = re.compile(r"^\*\*([^*]+):\*\*(?:\s*(.*))?$")
ITEM = re.compile(r"^(?:[-*]|\d+\.)\s+(.+)$")


def add_text(target: dict | None, value: str, line: int, item: bool = False, column: int = 1) -> None:
    if target and value:
        target.setdefault("items" if item else "prose", []).append({"text": value, "line": line, "column": column})


def split(path: Path, text: str) -> dict:
    """Invert the template grammar without knowing any schema field names."""
    tree, record, section, group, label = {"path": str(path), "header": {}, "records": []}, None, None, None, None
    header, fenced, pending_header, pending = True, False, False, {}
    inherited = {}
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("```"):
            fenced = not fenced
            add_text(label or group or section, raw, number)
            continue
        if not fenced and line.startswith("# "):
            record = section = group = label = None
            header = True
            pending_header = bool(tree["records"])
            continue
        if not fenced and (line == "---" or line.startswith("## ")):
            header = False
        if not fenced and (match := HEADING.match(line)):
            record = {"id": match.group(1), "title": match.group(2), "line": number, "fields": {}, "sections": []}
            inherited.update(pending)
            record["fields"].update(inherited)
            pending = {}
            pending_header = False
            tree["records"].append(record)
            section = group = label = None
            continue
        if not fenced and line.startswith("## ") and not HEADING.match(line):
            record = section = group = label = None
            continue
        if not fenced and record and line.startswith("### "):
            section = {"name": raw[4:], "line": number, "prose": [], "labels": [], "groups": []}
            record["sections"].append(section)
            group = label = None
            continue
        if not fenced and section and line.startswith("#### "):
            group = {"name": raw[5:], "line": number, "prose": [], "labels": []}
            section["groups"].append(group)
            label = None
            continue
        match = None if fenced else LABEL.match(raw)
        if match:
            entry = {"name": match.group(1), "line": number, "prose": [], "items": []}
            value = match.group(2) or ""
            if header:
                (pending if pending_header else tree["header"])[entry["name"]] = {"value": value, "line": number, "column": match.start(2) + 1 if match.group(2) else len(line) + 1}
            elif record and not section:
                record["fields"][entry["name"]] = {"value": value, "line": number, "column": match.start(2) + 1 if match.group(2) else len(line) + 1}
            elif section:
                (group or section)["labels"].append(entry)
                label = entry
                add_text(label, value, number, column=match.start(2) + 1 if match.group(2) else len(line) + 1)
            continue
        if line:
            item = ITEM.match(line)
            add_text(label or group or section, item.group(1) if item else raw, number, bool(item), item.start(1) + 1 if item else 1)
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
    qualifier = Qualifier(root)
    for file in files:
        text = file.read_text()
        qualifier.qualify(split(file.relative_to(root), text), text)
    accepted = json.loads(raptor_schema.accept(json.dumps(qualifier.rows)))
    summary = accepted["summary"]
    for issue in qualifier.issues:
        summary["counts"][issue["rule"]] = summary["counts"].get(issue["rule"], 0) + 1
    for error in accepted["errors"]:
        qualifier.map_error(error)
    issues = sorted(qualifier.issues, key=lambda issue: (issue["file"], issue["line"], issue["column"]))
    groups = {}
    for issue in issues:
        key = (issue["rule"], issue["label"] is not None, issue["label"] or "", issue["allowed"] is not None, tuple(issue["allowed"] or []), issue["remedy"])
        group = groups.setdefault(key, dict(rule=issue["rule"], section=None, label=issue["label"], allowed=issue["allowed"], count=0, files={}, remedy=issue["remedy"]))
        group["count"] += 1
        group["files"].setdefault(issue["file"], []).append(issue["line"])
    summary.update(groups=[groups[key] for key in sorted(groups)], aliases=qualifier.counts)
    payload = {"metadata": {"repository": repository, "generated": datetime.now(timezone.utc).isoformat(), "files": len(files), "records": summary["records"]}, **accepted["batch"], "diagnostics": {"issues": issues, "summary": summary}}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"index": str(args.output), "files": len(files), "records": payload["metadata"]["records"], "issues": len(issues)}))
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
