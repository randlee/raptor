"""Split Markdown structure without validating schema vocabulary or IDs."""

import re
from pathlib import Path

HEADING = re.compile(r"^##\s+(\S+):\s*(.*)$")
LABEL = re.compile(r"^\*\*([^*]+):\*\*(?:\s*(.*))?$")
ITEM = re.compile(r"^(?:[-*]|\d+\.)\s+(.+)$")


def add_text(
    target: dict | None,
    value: str,
    line: int,
    item: bool = False,
    column: int = 1,
    source: str | None = None,
) -> None:
    if target and value:
        target.setdefault("items" if item else "prose", []).append(
            {
                "value": value,
                "raw": value if source is None else source,
                "line": line,
                "column": column,
            }
        )


def split(path: Path, text: str) -> dict:
    """Invert the template grammar without knowing any schema field names."""
    tree, record, section, group, label = (
        {"path": str(path), "header": {}, "records": []},
        None,
        None,
        None,
        None,
    )
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
        if not fenced and (re.fullmatch(r"-{3,}", line) or line.startswith("## ")):
            header = False
        if not fenced and re.fullmatch(r"-{3,}", line):
            continue
        if not fenced and (match := HEADING.match(line)):
            record = {
                "heading_id": match.group(1),
                "heading_title": match.group(2),
                "line": number,
                "fields": {},
                "sections": [],
            }
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
            section = {
                "token": raw[4:],
                "line": number,
                "prose": [],
                "labels": [],
                "group_nodes": [],
            }
            record["sections"].append(section)
            group = label = None
            continue
        if not fenced and section and line.startswith("#### "):
            group = {"token": raw[5:], "line": number, "prose": [], "labels": []}
            section["group_nodes"].append(group)
            label = None
            continue
        match = None if fenced else LABEL.match(raw)
        if match:
            entry = {"token": match.group(1), "line": number, "prose": [], "items": []}
            value = match.group(2) or ""
            if header:
                (pending if pending_header else tree["header"])[entry["token"]] = {
                    "value": value,
                    "line": number,
                    "column": match.start(2) + 1 if match.group(2) else len(line) + 1,
                }
            elif record and not section:
                record["fields"][entry["token"]] = {
                    "value": value,
                    "line": number,
                    "column": match.start(2) + 1 if match.group(2) else len(line) + 1,
                }
            elif section:
                (group or section)["labels"].append(entry)
                label = entry
                add_text(
                    label,
                    value,
                    number,
                    column=match.start(2) + 1 if match.group(2) else len(line) + 1,
                )
            continue
        if line:
            item = None if fenced else ITEM.match(line)
            add_text(
                label or group or section,
                item.group(1) if item else raw,
                number,
                bool(item),
                item.start(1) + 1 if item else 1,
                source=raw,
            )
    return tree
