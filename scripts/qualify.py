"""Qualify splitter trees using the crate's field metadata and JSON Schemas."""

import json
import re

import raptor_schema

if __package__:
    from .aliases import load_aliases
    from .diagnostics import section_for_path
    from .markdown_content import normal, populated
    from .record_context import RecordContext
    from .schema_json import empty, nonnull, resolve, roles, schemas
    from .shape_content import parse_content
    from .source_inventory import SourceInventory
else:
    from aliases import load_aliases
    from diagnostics import section_for_path
    from markdown_content import normal, populated
    from record_context import RecordContext
    from schema_json import empty, nonnull, resolve, roles, schemas
    from shape_content import parse_content
    from source_inventory import SourceInventory


def record_end(lines, record):
    """Last content line of a record, ignoring blank lines and `---` separators."""
    end = record["line"]
    for number in range(record["line"] + 1, len(lines) + 1):
        text = lines[number - 1]
        if text.startswith(("# ", "## ")):
            break
        if text.strip() and not re.fullmatch(r"-{3,}", text.strip()):
            end = number
    return end


class Qualifier:
    def __init__(self, root):
        self.schemas = schemas()
        self.fields = {
            table: json.loads(raptor_schema.field_table(table)) for table in self.schemas
        }
        self.protocol = next(iter(self.schemas.values()))["x-raptor-protocol"]
        self.heading_roles = self.protocol["heading_roles"]
        heading_fields = {}
        for table, fields in self.fields.items():
            headings = [
                field for field in fields if field["role"] == self.heading_roles["identifier"]
            ]
            if len(headings) != 1:
                raise ValueError("Each schema table must declare one heading identifier")
            [heading] = headings
            heading_fields[table] = heading
        scalar_kinds = {
            self.schemas[table]["properties"][field["name"]]["$ref"].rsplit("/", 1)[-1]
            for table, field in heading_fields.items()
        }
        if len(scalar_kinds) != 1:
            raise ValueError("Schema heading identifiers must share one scalar definition")
        self.identifier_kind = scalar_kinds.pop()
        self.table_prefixes = {
            table: schema["x-raptor-tables"][table]["id_prefixes"]
            for table, schema in self.schemas.items()
        }
        self.rows = {table: [] for table in self.schemas}
        self.sources = {table: [] for table in self.schemas}
        self.issues, self.counts = [], {}
        self.source_inventory = SourceInventory()
        self.aliases = load_aliases(root, self.schemas, self.fields)
        self.rules = next(iter(self.schemas.values()))["x-raptor-rules"]
        self.error_rules = {
            category: rule
            for rule, metadata in self.rules.items()
            for category in metadata["categories"]
        }

    def qualify(self, tree, text):
        lines = text.splitlines()
        if not tree["records"]:
            context = RecordContext(self, tree["path"], lines, {})
            context.issue("MISSING_ID", {"line": 1, "column": 1}, "", allowed=["a record heading"])
        for record in tree["records"]:
            context = RecordContext(self, tree["path"], lines, record)
            identifier = record["token"]
            try:
                raptor_schema.validate_scalar(self.identifier_kind, identifier)
            except raptor_schema.SchemaError as error:
                context.issue(
                    "BAD_VALUE",
                    record,
                    identifier,
                    allowed=error.allowed_values,
                    message=f"{error.category}: {error.message}",
                )
            else:
                self.source_inventory.record(context)
            matches = [
                table
                for table, prefixes in self.table_prefixes.items()
                if any(identifier.startswith(prefix) for prefix in prefixes)
            ]
            if len(matches) != 1:
                if context.bad:
                    continue
                raise ValueError("Validated heading has no unique schema table routing")
            context.table = matches[0]
            context.schema = self.schemas[context.table]
            result = self.qualify_record(context, tree["header"] | record["fields"])
            if not context.bad:
                self.rows[context.table].append(result)
                self.sources[context.table].append(context)
        return self.rows

    def qualify_record(self, context, supplied_fields):
        fields = self.fields[context.table]
        result = empty(context.schema, context.schema)
        headers = {
            field["label"]: field for field in fields if field["level"] in ("Header", "Item")
        }
        supplied = {}
        for name, node in supplied_fields.items():
            canonical = context.match("labels", name, headers, node, "UNKNOWN_LABEL")
            if canonical:
                supplied[canonical] = dict(node, token=canonical)
        top = {
            field["name"]: field
            for field in fields
            if field["level"] in ("Header", "Item")
            and field["name"] in context.schema["properties"]
        }
        heading_values = {
            self.heading_roles["identifier"]: context.record["token"],
            self.heading_roles["caption"]: context.record["caption"],
        }
        for field in top.values():
            key = field["name"]
            if field["role"] in self.heading_roles.values():
                node = dict(context.record, value=heading_values[field["role"]])
                if field["role"] == self.heading_roles["caption"]:
                    node["column"] = context.record["caption_column"]
            else:
                node = supplied.get(field["label"])
            if node is not None and node["value"].strip():
                context.locations[f"/{key}"] = (node, node["value"], field["label"])
                prop = context.schema["properties"][key]
                result[key] = (
                    node["value"]
                    if field["role"] == self.heading_roles["identifier"]
                    else context.scalar(node["value"], prop, node)
                )
            elif field["required"]:
                self.missing_header(context, field, supplied.get(field["label"]))
        self.qualify_sections(context, result, fields)
        return result

    def qualify_sections(self, context, result, fields):
        sections = {field["label"]: field for field in fields if field["level"] == "Section"}
        present = {}
        for node in context.record["sections"]:
            canonical = context.match("sections", node["token"], sections, node, "UNKNOWN_SECTION")
            if canonical is None:
                continue
            field = sections[canonical]
            path = f"/{field['name']}"
            context.locations[path] = (node, node["token"], canonical)
            context.section = canonical
            prop = context.schema["properties"][field["name"]]
            result[field["name"]] = parse_content(context, node, field, prop, path)
            context.section = None
            present[canonical] = node
        for label, field in sections.items():
            if field["required"] and (label not in present or not populated(result[field["name"]])):
                self.missing_section(context, label, fields, present, sections)

    def missing_header(self, context, field, node):
        """Report a required header field as empty (at its label) or missing (where it belongs)."""
        label, record, lines = field["label"], context.record, context.lines
        prop = context.schema["properties"][field["name"]]
        shape = resolve(nonnull(prop), context.schema)
        kind = nonnull(prop).get("$ref", "").rsplit("/", 1)[-1]
        if "enum" in shape:
            expected, value = f"one of {', '.join(shape['enum'])}", shape["enum"][0]
            alternatives = f" (or another of: {', '.join(shape['enum'][1:])})"
        else:
            try:
                raptor_schema.validate_scalar(kind, "")
                expected = "a value"
            except raptor_schema.SchemaError as error:
                expected = error.message.split("expected ", 1)[-1].rstrip(".")
            value = None
        edit = None
        if node is not None:
            line = node["line"]
            state, where = "empty", f"on line {line}"
            if value:
                edit = dict(op="replace", line=line, lines=[f"{lines[line - 1].rstrip()} {value}"])
            location = node
        else:
            after = max([n["line"] for n in record["fields"].values()] + [record["line"]])
            line = after + 1
            state, where = "missing", f"after line {after}"
            if value:
                edit = dict(op="insert", line=line, lines=[f"**{label}:** {value}"])
            location = {"line": line, "column": 1}
        fix = f"write `**{label}:** <value>` {where}, where <value> is {expected}"
        if value:
            fix = f"write `**{label}:** {value}` {where}{alternatives}"
        context.issue(
            "MISSING_FIELD",
            location,
            "",
            label,
            message=f"header field {label!r} of {record['token']} is {state}; expected {expected}.",
            fix=fix,
            edit=edit,
        )

    def missing_section(self, context, label, fields, present, sections):
        """Report a required section as empty (at its heading) or missing (where it belongs)."""
        lines, node = context.lines, present.get(label)
        children = [f for f in fields if f["level"] == "Label" and f["section"] == label]
        field = sections[label]
        section = resolve(context.schema["properties"][field["name"]], context.schema)

        def entry(prop):
            prop = resolve(nonnull(prop), context.schema)
            if prop.get("type") != "array":
                return f"Describe the {label.lower()}."
            if "selection" in roles(prop["items"], context.schema):
                return "- [ ] Describe the criterion."
            return "- Describe."

        def child_entry(member):
            return entry(section["properties"][member["name"]])

        first = next(iter(children), None)
        body = [f"**{first['label']}:**", "", child_entry(first)] if first else [entry(section)]
        context.section = label
        if node is not None:
            if node["labels"]:
                head = node["labels"][0]
                token = normal(head["token"])
                child = next((c for c in children if normal(c["label"]) == token), first)
                line, lines_ = head["line"], ["", child_entry(child)]
                put = f"under `**{head['token']}:**` at line {line}"
            else:
                line, lines_ = node["line"], ["", *body]
                put = f"under `### {label}` at line {line}"
            noun = "at least one sentence" if body == [entry(section)] else "at least one list item"
            context.issue(
                "MISSING_FIELD",
                node,
                "",
                label,
                message=f"section {label!r} of {context.record['token']} is empty; expected {noun}.",
                fix=f"write {noun} {put}",
                edit=dict(op="insert", line=line + 1, lines=lines_),
            )
            context.section = None
            return
        order = list(sections)
        later = [present[name] for name in order[order.index(label) + 1 :] if name in present]
        heading = f"### {label}"
        if later:
            line = later[0]["line"]
            edit = dict(op="insert", line=line, lines=[heading, "", *body, ""])
        else:
            line = record_end(lines, context.record) + 1
            edit = dict(op="insert", line=line, lines=["", heading, "", *body])
        context.issue(
            "MISSING_FIELD",
            {"line": line, "column": 1},
            "",
            label,
            message=(
                f"section {label!r} of {context.record['token']} is missing; "
                f"expected a `{heading}` section with its content."
            ),
            fix=f"add `{heading}` before line {line} followed by its content",
            edit=edit,
        )
        context.section = None

    def map_error(self, error):
        context = self.sources[error["table"]][error["record_position"]]
        path = error["field_path"]
        context.section = section_for_path(self.fields[error["table"]], path)
        if error["item_index"] is not None and not any(p.isdigit() for p in path.split("/")):
            path += f"/{error['item_index']}"
        while path not in context.locations and path:
            path = path.rsplit("/", 1)[0]
        fallback = (context.record, error["offending_value"], None)
        node, value, label = context.locations.get(path, fallback)
        rule = self.error_rules[error["category"]]
        context.issue(
            rule,
            node,
            value,
            label,
            message=(
                f"Found {value!r}; expected valid schema input. "
                f"{error['category']}: {error['message']}"
            ),
            fix=f"{error['recovery']} Offending value: {value!r} at line {node['line']}.",
        )
