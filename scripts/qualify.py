"""Qualify splitter trees using the crate's field metadata and JSON Schemas."""

import json

import raptor_schema

if __package__:
    from .aliases import load_aliases
    from .diagnostics import section_for_path
    from .markdown_content import populated
    from .record_context import RecordContext
    from .schema_json import empty, schemas
    from .shape_content import parse_content
else:
    from aliases import load_aliases
    from diagnostics import section_for_path
    from markdown_content import populated
    from record_context import RecordContext
    from schema_json import empty, schemas
    from shape_content import parse_content


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
            context.issue("MISSING_ID", {}, "", allowed=["a record heading"])
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
            if field["level"] in ("Header", "Item") and field["shape"] != "Derived"
        }
        heading_values = {
            self.heading_roles["identifier"]: context.record["token"],
            self.heading_roles["caption"]: context.record["caption"],
        }
        for field in top.values():
            key = field["name"]
            if field["role"] in self.heading_roles.values():
                node = dict(context.record, value=heading_values[field["role"]])
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
                context.issue("MISSING_FIELD", context.record, "", field["label"])
        self.qualify_sections(context, result, fields)
        return result

    def qualify_sections(self, context, result, fields):
        sections = {field["label"]: field for field in fields if field["level"] == "Section"}
        present = set()
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
            present.add(canonical)
        for label, field in sections.items():
            if field["required"] and (label not in present or not populated(result[field["name"]])):
                context.section = label
                context.issue("MISSING_FIELD", context.record, "", label)
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
        )
