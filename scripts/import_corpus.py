"""Inventory and import pipeline for configured Markdown repositories."""

import argparse
import json
import tomllib
from collections import Counter
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

import raptor_schema

if __package__:
    from .diagnostics import group_issues
    from .markdown_splitter import split
    from .qualify import Qualifier
else:
    from diagnostics import group_issues
    from markdown_splitter import split
    from qualify import Qualifier


def inventory(root, sources):
    files = set()
    for source in sources.get("sources", []):
        base = root / source["root"]
        include = source.get("include", ["**/*.md"])
        exclude = source.get("exclude", [])
        for file in base.rglob("*.md") if base.exists() else []:
            relative = file.relative_to(base).as_posix()

            def matches(patterns):
                return any(
                    fnmatch(relative, pattern)
                    or (pattern.startswith("**/") and fnmatch(relative, pattern[3:]))
                    for pattern in patterns
                )

            if matches(include) and not matches(exclude):
                files.add(file)
    return sorted(files)


def build_index(root):
    config = root / ".raptor"
    repository = tomllib.loads((config / "raptor.toml").read_text())["repository_id"]
    files = inventory(root, tomllib.loads((config / "sources.toml").read_text()))
    qualifier = Qualifier(root)
    for file in files:
        text = file.read_text()
        qualifier.qualify(split(file.relative_to(root), text), text)
    accepted = json.loads(raptor_schema.accept(json.dumps(qualifier.rows)))
    for error in accepted["errors"]:
        qualifier.map_error(error)
    issues = sorted(qualifier.issues, key=lambda item: (item["file"], item["line"], item["column"]))
    summary = dict(
        accepted["summary"],
        counts=dict(Counter(item["rule"] for item in issues)),
        groups=group_issues(issues),
        aliases=qualifier.counts,
    )
    metadata = dict(
        repository=repository,
        generated=datetime.now(timezone.utc).isoformat(),
        files=len(files),
        records=summary["records"],
    )
    return dict(
        metadata=metadata, **accepted["batch"], diagnostics=dict(issues=issues, summary=summary)
    )


def run_import():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("requirements-index.json"))
    args = parser.parse_args()
    payload = build_index(args.project_root.resolve())
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    issue_count = len(payload["diagnostics"]["issues"])
    report = dict(
        index=str(args.output),
        files=payload["metadata"]["files"],
        records=payload["metadata"]["records"],
        issues=issue_count,
    )
    return report, int(bool(issue_count))
