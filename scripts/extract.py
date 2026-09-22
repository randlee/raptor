#!/usr/bin/env python3
"""Extract REQ, NFR, and ADR Markdown sections into a portable JSON index."""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ITEM = re.compile(
    r"^##[ \t]+(?P<id>(?:REQ|NFR|ADR)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}):[ \t]*(?P<title>.+?)[ \t]*$",
    re.MULTILINE,
)
H1 = re.compile(r"^#[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)
FIELD = re.compile(r"^\*\*(?P<name>[^:]+):\*\*[ \t]*(?P<value>.+?)[ \t]*$", re.MULTILINE)
SUBSECTION = re.compile(r"^(?P<marks>#{3,5})[ \t]+(?P<title>.+?)[ \t]*$", re.MULTILINE)
REFERENCE = re.compile(r"(?:REQ|NFR|ADR)-[A-Z0-9][A-Z0-9-]*-[0-9]{4,}")
STATUS = {"draft": "Draft", "proposed": "Proposed", "active": "Active", "approved": "Approved", "accepted": "Approved", "deprecated": "Deprecated", "superseded": "Superseded"}


def diagnostic(path: Path, message: str) -> None:
    print(f"{path}: {message}", file=sys.stderr)


def metadata(text: str, path: Path) -> dict[str, Any]:
    values: dict[str, Any] = {"created": None, "last_updated": None, "owner": "Unknown", "id_range": None, "range_description": None, "status": "Draft"}
    for match in FIELD.finditer("\n".join(text.splitlines()[:50])):
        name, value = match["name"].strip().lower(), match["value"].strip()
        if name == "status":
            values["status"] = STATUS.get(value.lower(), value)
        elif name == "id range": values["id_range"] = value
        elif name == "created": values["created"] = value
        elif name in {"updated", "last updated"}: values["last_updated"] = value
        elif name == "owner": values["owner"] = value
    title = H1.search(text)
    values["range_description"] = title["title"].strip() if title else None
    fallback = datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
    values["created"] = values["created"] or fallback
    values["last_updated"] = values["last_updated"] or fallback
    return values


def relative_domain(path: Path, root: Path, override: str | None) -> str:
    if override:
        return override
    parts = path.relative_to(root).parts
    return parts[0] if len(parts) > 1 else "default"


def markdown_html(markdown: str) -> str:
    """A deliberately small stdlib representation; Markdown remains authoritative."""
    return "<pre>" + html.escape(markdown) + "</pre>"


def parse_file(path: Path, root: Path, domain: str | None) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    doc = metadata(text, path)
    matches = list(ITEM.finditer(text))
    records: list[dict[str, Any]] = []
    for ordinal, match in enumerate(matches):
        body = text[match.end(): matches[ordinal + 1].start() if ordinal + 1 < len(matches) else len(text)].strip()
        item_status = next((STATUS.get(m["value"].strip().lower(), m["value"].strip()) for m in FIELD.finditer(body) if m["name"].strip().lower() == "status"), doc["status"])
        references = [{"target_id": found.group(0), "type": "mentions", "context": line.strip()} for line in body.splitlines() for found in REFERENCE.finditer(line)]
        item_id = match["id"]
        records.append({
            "id": item_id, "title": match["title"].strip(), "type": item_id.split("-", 1)[0], "status": item_status,
            "domain": relative_domain(path, root, domain),
            "document_metadata": {key: doc[key] for key in ("created", "last_updated", "owner", "id_range", "range_description")},
            "source": {"file": path.relative_to(root).as_posix(), "section_line": text.count("\n", 0, match.start()) + 1},
            "content": {"markdown": body, "html": markdown_html(body), "summary": body[:200] + ("..." if len(body) > 200 else "")},
            "relationships": {"references": references, "referenced_by": [], "family": {"id_range": doc["id_range"], "members_count": 0}},
            "subsections": [{"heading": sub["title"].strip(), "level": len(sub["marks"]), "content_length": 0} for sub in SUBSECTION.finditer(body)],
        })
    return records


def build_relationships(records: list[dict[str, Any]]) -> None:
    by_id = {record["id"]: record for record in records}
    for record in records:
        for reference in record["relationships"]["references"]:
            if target := by_id.get(reference["target_id"]):
                target["relationships"]["referenced_by"].append({"source_id": record["id"], "type": "mentioned_by", "context": reference["context"]})
    counts = Counter(record["document_metadata"]["id_range"] for record in records if record["document_metadata"]["id_range"])
    for record in records:
        item_range = record["document_metadata"]["id_range"]
        record["relationships"]["family"]["members_count"] = counts[item_range]


def extract(roots: list[Path], domain: str | None, file_list: Path | None) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    problems = 0
    for root in roots:
        paths = (root / line for line in dict.fromkeys(line.strip() for line in file_list.read_text(encoding="utf-8").splitlines() if line.strip())) if file_list else root.rglob("*.md")
        for path in sorted(candidate for candidate in paths if candidate.suffix == ".md" and ".git" not in candidate.parts):
            try:
                parsed = parse_file(path, root, domain)
            except UnicodeDecodeError:
                diagnostic(path, "invalid UTF-8")
                problems += 1
                continue
            for record in parsed:
                records.append(record)
    build_relationships(records)
    return records, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="repository or documentation roots to scan")
    parser.add_argument("--output", type=Path, default=Path("requirements-index.json"))
    parser.add_argument("--domain", help="domain value to use for every extracted item")
    parser.add_argument("--file-list", type=Path, help="newline-delimited Markdown paths relative to the one root")
    args = parser.parse_args()
    roots = [root.resolve() for root in args.roots]
    missing = [root for root in roots if not root.is_dir()]
    if missing:
        parser.error("not a directory: " + ", ".join(map(str, missing)))
    if args.file_list and len(roots) != 1:
        parser.error("--file-list requires exactly one root")
    records, problems = extract(roots, args.domain, args.file_list)
    payload = {"metadata": {"version": "1.0.0", "total_requirements": len(records)}, "requirements": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"records={len(records)} diagnostics={problems} output={args.output}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
