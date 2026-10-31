"""Explicit source and schema context for one record qualification operation."""

from dataclasses import dataclass, field
from collections import Counter

import raptor_schema

if __package__:
    from .markdown_content import normal
    from .schema_json import nonnull, resolve
else:
    from markdown_content import normal
    from schema_json import nonnull, resolve


@dataclass
class RecordContext:
    owner: object
    file: str
    lines: list
    record: dict
    table: str | None = None
    schema: dict = field(default_factory=dict)
    locations: dict = field(default_factory=dict)
    section: str | None = None
    bad: bool = False

    def issue(self, rule, node, value, label=None, allowed=None, message=None):
        line = max(1, node.get("line", 1))
        raw = self.lines[line - 1] if line <= len(self.lines) else ""
        found = raw.find(str(value))
        column = max(1, node.get("column", found + 1 if found >= 0 else 1))
        policy = self.owner.rules[rule]
        self.owner.issues.append(
            dict(
                file=self.file,
                line=line,
                column=column,
                rule=rule,
                id=self.record.get("heading_id"),
                section=self.section,
                label=label,
                value=value,
                allowed=allowed,
                message=message or f"Found {value!r}; expected {allowed or label or rule.lower()}.",
                remedy=policy["remedy"],
            )
        )
        self.bad |= policy["rejects_record"]

    def match(self, group, value, choices, node, rule, message=None):
        token = normal(value)
        if token in self.owner.aliases.get(group, {}):
            source, target = self.owner.aliases[group][token]
            self.owner.counts.setdefault(group, Counter())[f"{source} -> {target}"] += 1
            token = normal(target)
        found = next((choice for choice in choices if normal(choice) == token), None)
        if found is None and group == "labels":
            for alias, (source, target) in self.owner.aliases.get("values", {}).items():
                for fields in self.owner.fields.values():
                    for metadata in fields:
                        suffix = metadata.get("modal_label_suffix")
                        if metadata["modal"] == target and metadata["label"] in choices and suffix:
                            if token == normal(alias + suffix):
                                counts = self.owner.counts.setdefault("values", Counter())
                                counts[f"{source} -> {target}"] += 1
                                return metadata["label"]
        if found is None:
            source = dict(node)
            if group != "values":
                raw = self.lines[node["line"] - 1]
                source["column"] = max(1, raw.find(value) + 1)
            label = value if group != "values" else node.get("token")
            self.issue(rule, source, value, label, list(choices), message)
        return found

    def scalar(self, value, specification, node):
        text = value.strip()
        specification = nonnull(specification)
        shape = resolve(specification, self.schema)
        if "enum" in shape:
            return self.match("values", value, shape["enum"], node, "BAD_VALUE")
        if "$ref" in specification and shape.get("type") == "string":
            try:
                raptor_schema.validate_scalar(specification["$ref"].rsplit("/", 1)[-1], text)
            except raptor_schema.SchemaError as error:
                self.issue(
                    "BAD_VALUE",
                    node,
                    value,
                    node.get("token"),
                    message=f"{error.category}: {error.message}",
                )
        return text
