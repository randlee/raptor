"""Qualify splitter trees using the crate's field metadata and JSON Schemas."""
import json
import re
import tomllib
from collections import Counter
from pathlib import Path

import raptor_schema

REMEDIES = {
    "MISSING_ID": "Add the required field.", "MISSING_FIELD": "Add the required field.",
    "BAD_VALUE": "Use the documented value format.",
    "UNKNOWN_SECTION": "Remove the section or use an allowed section.",
    "UNKNOWN_LABEL": "Remove the label or use an allowed label.",
    "DUPLICATE_ID": "Make the identifier unique.",
    "DANGLING_REFERENCE": "Declare the referenced identifier or remove the reference.",
}


def normal(text):
    return " ".join(text.split()).removesuffix(":").rstrip().casefold()


def resolve(node, root):
    return root["definitions"][node["$ref"].rsplit("/", 1)[-1]] if "$ref" in node else node


def empty(node, root):
    node = resolve(node, root)
    if "null" in node.get("type", []) or any(part.get("type") == "null" for part in node.get("anyOf", [])):
        return None
    if "properties" in node:
        return {name: empty(child, root) for name, child in node["properties"].items()}
    return [] if node.get("type") == "array" else ""


def populated(value):
    if isinstance(value, (dict, list)):
        return any(populated(item) for item in (value.values() if isinstance(value, dict) else value))
    return bool(value)


class Qualifier:
    def __init__(self, root):
        self.schemas = json.loads(raptor_schema.json_schema())
        self.fields = {table: json.loads(raptor_schema.field_table(table)) for table in self.schemas}
        self.kinds = {kind.upper(): table for table, schema in self.schemas.items() for kind in schema["x-raptor-kinds"]}
        self.rows, self.sources = ({table: [] for table in self.schemas} for _ in range(2))
        self.issues, self.counts, self.aliases = [], {}, {}
        fields = [field for fields in self.fields.values() for field in fields]
        choices = {"labels": {f["label"] for f in fields if f["level"] != "Section"},
                   "sections": {f["label"] for f in fields if f["level"] == "Section"},
                   "values": {v for s in self.schemas.values() for d in s["definitions"].values() for v in d.get("enum", [])}}
        path = Path(root) / ".raptor/aliases.toml"
        text = path.read_text() if path.exists() else ""
        try:
            aliases = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"{path}: {error}") from error
        alias_lines, group = {}, ""
        for number, raw in enumerate(text.splitlines(), 1):
            if heading := re.match(r"\s*\[([\w]+)\]", raw):
                group = heading[1]
            if assignment := re.match(r'''\s*(?:"([^"]+)"|'([^']+)'|([\w-]+))\s*=''', raw):
                alias_lines[group, next(value for value in assignment.groups() if value is not None)] = number
        for group, mapping in aliases.items():
            if group not in choices or not isinstance(mapping, dict):
                raise ValueError(f"{path}:1: expected only labels, sections and values tables")
            for key, target in mapping.items():
                line = alias_lines.get((group, key), 1)
                if not isinstance(target, str) or target not in choices[group]:
                    raise ValueError(f"{path}:{line}: unknown alias target {target!r}; expected {sorted(choices[group])}")
                self.aliases.setdefault(group, {})[normal(key)] = (key, target)

    def issue(self, rule, node, value, label=None, allowed=None, message=None):
        line = node.get("line", 1)
        raw = self.lines[line - 1] if 0 < line <= len(self.lines) else ""
        column = node.get("column", max(0, raw.find(str(value))) + 1)
        self.issues.append(dict(file=self.file, line=line, column=column, rule=rule, id=self.record.get("id"),
            label=label, value=value, allowed=allowed, message=message or f"Found {value!r}; expected {allowed or label or rule.lower()}.",
            remedy=REMEDIES[rule]))
        self.bad |= rule in ("BAD_VALUE", "MISSING_FIELD", "MISSING_ID")

    def match(self, group, value, choices, node, rule):
        token = normal(value)
        if token in self.aliases.get(group, {}):
            source, target = self.aliases[group][token]
            counts = self.counts.setdefault(group, Counter())
            counts[f"{source} -> {target}"] += 1
            token = normal(target)
        found = next((choice for choice in choices if normal(choice) == token), None)
        if found is None and group == "labels":
            for alias, (source, target) in self.aliases.get("values", {}).items():
                for fields in self.fields.values():
                    for field in fields:
                        if field["modal"] == target and field["label"] in choices:
                            if token == f"{alias} {normal(field['label']).split()[-1]}":
                                self.counts.setdefault("values", Counter())[f"{source} -> {target}"] += 1
                                return field["label"]
        if found is None:
            source = dict(node, column=self.lines[node["line"] - 1].find(value) + 1) if group != "values" else node
            self.issue(rule, source, value, value if group != "values" else node.get("name"), list(choices))
        return found

    def scalar(self, value, specification, node):
        text = value.strip()
        if "anyOf" in specification:
            specification = next(part for part in specification["anyOf"] if part.get("type") != "null")
        shape = resolve(specification, self.schema)
        if "enum" in shape:
            return self.match("values", value, shape["enum"], node, "BAD_VALUE")
        if "$ref" in specification and shape.get("type") == "string":
            try:
                raptor_schema.validate_scalar(specification["$ref"].rsplit("/", 1)[-1], text)
            except raptor_schema.SchemaError as error:
                self.issue("BAD_VALUE", node, value, node.get("name"), message=f"{error.category}: {error.message}")
        return text

    def items(self, node, field, specification, path, offset):
        out = []
        entries = sorted(node.get("prose", []) + node.get("items", []), key=lambda item: item["line"])
        for entry in entries:
            entry = dict(entry, name=field["label"])
            raw = entry["text"]
            text = raw.strip()
            shape = field["shape"]
            item_path = f"{path}/{offset + len(out)}"
            self.locations[item_path] = (entry, raw, field["label"])
            if shape == "StatementList":
                item = dict(modal=field["modal"], text=text)
            elif shape == "Checklist":
                box = re.match(r"^\[([ xX])\]\s+(.*)$", text)
                if text.startswith("[") and not box:
                    self.issue("BAD_VALUE", entry, raw, field["label"], message=f"Found {raw!r}; expected [ ] text or [x] text.")
                item = dict(text=box[2] if box else text, checked=box[1].casefold() == "x" if box else None)
            elif shape in ("IdList", "LinkList"):
                link = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)(?:\s+(.*))?", text)
                if link:
                    token, href, note = link.groups()
                else:
                    token, _, note = text.partition(" ")
                    href = ""
                if (text.startswith("[") and not link) or (shape == "LinkList" and not link):
                    self.issue("BAD_VALUE", entry, raw, field["label"], message=f"Found {raw!r}; expected [text](href) with an optional note.")
                note = note.lstrip("—- ").strip() if note else None
                item = dict(text=token, href=href, note=note) if shape == "LinkList" else dict(id=token, note=note)
                if shape == "IdList":
                    props = resolve(specification["items"], self.schema)["properties"]
                    source = dict(entry, column=entry["column"] + raw.find(token))
                    self.locations[item_path] = (source, token, field["label"])
                    item["id"] = self.scalar(token, props["id"], source)
            else:
                item = text
            out.append(item)
        return out

    def content(self, node, field, specification, path):
        shape = resolve(specification, self.schema)
        text = "\n".join(item["text"] for item in node.get("prose", []))
        if shape.get("type") == "string":
            for child in node.get("labels", []) + node.get("groups", []):
                self.issue("UNKNOWN_LABEL" if "items" in child else "UNKNOWN_SECTION", child, child["name"], allowed=[])
            return text
        result = empty(specification, self.schema)
        result["text"] = text
        labels = {f["label"]: f for f in self.fields[self.table] if f["section"] == field["label"]}
        if "groups" in shape["properties"]:
            for index, group in enumerate(node.get("groups", [])):
                target = self.content(group, field, shape["properties"]["groups"]["items"], f"{path}/groups/{index}")
                target.pop("text", None)
                target["name"] = group["name"].split(":", 1)[-1].strip()
                result["groups"].append(target)
        else:
            for group in node.get("groups", []):
                self.issue("UNKNOWN_SECTION", group, group["name"], field["label"], [])
        for label in node.get("labels", []):
            canonical = self.match("labels", label["name"], labels, label, "UNKNOWN_LABEL")
            if canonical is None:
                continue
            member = labels[canonical]
            key = member["name"]
            prop = shape["properties"][key]
            target_path = f"{path}/{key}"
            self.locations[target_path] = (label, label["name"], canonical)
            if resolve(prop, self.schema).get("type") == "array":
                result[key].extend(self.items(label, member, resolve(prop, self.schema), target_path, len(result[key])))
            else:
                result[key] = "\n".join(item["text"] for item in label.get("prose", []) + label.get("items", []))
        return result

    def qualify(self, tree, text):
        self.file, self.lines = tree["path"], text.splitlines()
        self.record, self.bad = {}, False
        if not tree["records"]:
            self.issue("MISSING_ID", {}, "", allowed=["a record heading"])
        for record in tree["records"]:
            self.record, self.bad, self.locations = record, False, {}
            self.table = self.kinds.get(record["id"].partition("-")[0])
            if self.table is None:
                self.issue("BAD_VALUE", record, record["id"], allowed=list(self.kinds))
                continue
            self.schema = self.schemas[self.table]
            fields = self.fields[self.table]
            result = empty(self.schema, self.schema)
            headers = {field["label"]: field for field in fields if field["level"] in ("Header", "Item")}
            supplied = {}
            for name, node in (tree["header"] | record["fields"]).items():
                canonical = self.match("labels", name, headers, node, "UNKNOWN_LABEL")
                if canonical:
                    supplied[canonical] = dict(node, name=canonical)
            top = {f["name"]: f for f in fields if f["level"] in ("Header", "Item") and f["shape"] != "Derived"}
            for field in top.values():
                key = field["name"]
                node = dict(record, value=record[key]) if field["role"].startswith("heading_") else supplied.get(field["label"])
                if node is not None and node["value"].strip():
                    self.locations[f"/{key}"] = (node, node["value"], field["label"])
                    result[key] = self.scalar(node["value"], self.schema["properties"][key], node)
                elif field["required"]:
                    self.issue("MISSING_FIELD", record, "", field["label"])
            sections = {field["label"]: field for field in fields if field["level"] == "Section"}
            present = set()
            for node in record["sections"]:
                canonical = self.match("sections", node["name"], sections, node, "UNKNOWN_SECTION")
                if canonical is not None:
                    field = sections[canonical]
                    path = f"/{field['name']}"
                    self.locations[path] = (node, node["name"], canonical)
                    result[field["name"]] = self.content(node, field, self.schema["properties"][field["name"]], path)
                    present.add(canonical)
            for label, field in sections.items():
                if field["required"] and (label not in present or not populated(result[field["name"]])):
                    self.issue("MISSING_FIELD", record, "", label)
            if not self.bad:
                self.rows[self.table].append(result)
                self.sources[self.table].append((self.file, self.lines, record, self.locations))
        return self.rows

    def map_error(self, error):
        self.file, self.lines, self.record, locations = self.sources[error["table"]][error["record_position"]]
        path = error["field_path"]
        if error["item_index"] is not None and not any(part.isdigit() for part in path.split("/")):
            path += f"/{error['item_index']}"
        while path not in locations and path:
            path = path.rsplit("/", 1)[0]
        node, value, label = locations.get(path, (self.record, error["offending_value"], None))
        rule = {"DuplicateId": "DUPLICATE_ID", "DanglingReference": "DANGLING_REFERENCE"}.get(error["category"], "BAD_VALUE")
        expected = {"DUPLICATE_ID": "a unique identifier", "DANGLING_REFERENCE": "an identifier declared in this inventory"}.get(rule)
        message = f"Found {value!r}; expected {expected}." if expected else f"{error['category']}: {error['message']}"
        self.issue(rule, node, value, label, message=message)
