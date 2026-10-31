"""Validate source aliases against canonical choices exported by Rust."""

import re
import tomllib
from pathlib import Path

if __package__:
    from .markdown_content import normal
else:
    from markdown_content import normal


def load_aliases(root, schemas, fields):
    all_fields = [field for table in fields.values() for field in table]
    choices = {
        "labels": {f["label"] for f in all_fields if f["level"] != "Section"},
        "sections": {f["label"] for f in all_fields if f["level"] == "Section"},
        "values": {
            value
            for schema in schemas.values()
            for node in schema["definitions"].values()
            for value in node.get("enum", [])
        },
    }
    path = Path(root) / ".raptor/aliases.toml"
    text = path.read_text() if path.exists() else ""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}: {error}") from error
    locations, group = {}, ""
    for number, raw in enumerate(text.splitlines(), 1):
        if heading := re.match(r"\s*\[([\w]+)\]", raw):
            group = heading[1]
        if assignment := re.match(r"""\s*(?:"([^"]+)"|'([^']+)'|([\w-]+))\s*=""", raw):
            key = next(value for value in assignment.groups() if value is not None)
            locations[group, key] = number
    aliases = {}
    for group, mapping in data.items():
        if group not in choices or not isinstance(mapping, dict):
            raise ValueError(f"{path}:1: expected only labels, sections and values tables")
        for key, target in mapping.items():
            line = locations.get((group, key), 1)
            if not isinstance(target, str) or target not in choices[group]:
                expected = sorted(choices[group])
                raise ValueError(
                    f"{path}:{line}: unknown alias target {target!r}; expected {expected}"
                )
            aliases.setdefault(group, {})[normal(key)] = (key, target)
    return aliases
