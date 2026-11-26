#!/usr/bin/env python3
"""Generate one sc-compose authoring template per record kind from the schema.

Each template renders one new record as a standalone Markdown file. Variable
names are the record's field names; statement lists are split by modal. The
templates are written to `templates/<kind>-new.md.j2` and must not be edited
by hand: the schema boundary test compares them with this output.
"""

import argparse
import json
import re
from pathlib import Path

if __package__:
    from .schema_json import resolve, roles, schemas
else:
    from schema_json import resolve, roles, schemas

MACROS = """{%- macro items(label, values) -%}
{% if values %}
**{{ label }}:**

{% for value in values %}
- {{ value | replace("\\n", "\\n  ") }}
{% endfor %}

{% endif %}
{%- endmacro -%}
{%- macro checklist(label, values) -%}
{% if values %}
**{{ label }}:**

{% for value in values %}
- [ ] {{ value | replace("\\n", "\\n  ") }}
{% endfor %}

{% endif %}
{%- endmacro -%}
{%- macro text(label, value) -%}
{% if value %}
**{{ label }}:**

{{ value }}

{% endif %}
{%- endmacro -%}
{%- macro prose(value) -%}
{% if value %}
{{ value }}

{% endif %}
{%- endmacro -%}
{%- macro definitions_paragraph(value) -%}
{% if value %}
Definitions: {{ value }}

{% endif %}
{%- endmacro -%}
"""
STATEMENT_GUIDANCE = (
    "One obligation per MUST or MUST NOT item; the reason belongs in the rationale "
    "section; define project terms and acronyms in `definitions`; each acceptance "
    "criterion names a check that decides it."
)
GROUP_GUIDANCE = (
    "Name the problem and the forces behind the decision; give every rejected "
    "option its reason; list costs as well as benefits."
)
DEFINITIONS = "definitions"
HARD_BREAK = "{{ '  ' }}"


def snake(word):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", word).lower()


class Layout:
    """The variables and Markdown layout of one table's authoring template."""

    def __init__(self, schema, table):
        self.schema, self.table = schema, table
        self.fields = schema["x-raptor-fields"]
        self.info = schema["x-raptor-tables"][table]
        self.required, self.defaults, self.guidance = [], {}, []

    def declare(self, variable, default=None, required=False):
        known = set(self.required) | set(self.defaults)
        if variable in known:
            return variable
        if required:
            self.required.append(variable)
        else:
            self.defaults[variable] = default
        return variable

    def children(self, section):
        return [
            member
            for member in self.fields
            if member["level"] == "Label" and member["section"] == section
        ]

    def label_call(self, metadata, shape, owner=""):
        prop = shape["properties"][metadata["name"]]
        node = resolve(prop, self.schema)
        if node.get("type") != "array":
            name = owner + metadata["name"]
            return f'{{{{ text("{metadata["label"]}", {name}) }}}}', name, ""
        item_roles = roles(node["items"], self.schema)
        name = metadata["name"]
        if "modality" in item_roles:
            name = snake(metadata["modal"])
        macro = "checklist" if "selection" in item_roles else "items"
        return f'{{{{ {macro}("{metadata["label"]}", {owner + name}) }}}}', owner + name, []

    def section(self, field):
        key = field["name"]
        shape = resolve(self.schema["properties"][key], self.schema)
        semantic = roles(self.schema["properties"][key], self.schema)
        children = self.children(field["label"])
        calls, names = [], []
        if "collection" in semantic:
            groups = shape["properties"][semantic["collection"]]["items"]
            group_shape = resolve(groups, self.schema)
            caption = roles(groups, self.schema)["caption"]
            prefix = self.info["group_heading_prefix"]
            inner = [self.label_call(member, group_shape, "group.")[0] for member in children]
            calls.append(
                f"{{% for group in {key} %}}\n#### {prefix} {{{{ loop.index }}}}: "
                f"{{{{ group.{caption} }}}}\n\n{''.join(inner)}{{% endfor %}}\n"
            )
            names.append(self.declare(key, []))
            self.guidance.append(GROUP_GUIDANCE)
            self.guidance.append(
                f"Each `{key}` item is an object with "
                + ", ".join(f"`{name}`" for name in group_shape["properties"])
                + "."
            )
        else:
            if any(member["modal"] for member in children):
                calls.append(f"{{{{ definitions_paragraph({DEFINITIONS}) }}}}")
                names.append(self.declare(DEFINITIONS, ""))
                self.guidance.append(STATEMENT_GUIDANCE)
            calls.append(f"{{{{ prose({key}) }}}}")
            names.append(self.declare(key, ""))
            for metadata in children:
                call, name, default = self.label_call(metadata, shape)
                calls.append(call)
                names.append(self.declare(name, default))
        body = f"### {field['label']}\n\n{''.join(calls)}"
        if field["required"]:
            return body
        return f"{{% if {' or '.join(names)} %}}\n{body}{{% endif %}}\n"

    def header(self):
        heading_roles = self.schema["x-raptor-protocol"]["heading_roles"]
        identifier, caption = (
            next(member["name"] for member in self.fields if member["role"] == heading_roles[role])
            for role in ("identifier", "caption")
        )
        self.declare(identifier, required=True)
        self.declare(caption, required=True)
        lines = [f"# {self.info['heading_label']}: {{{{ {caption} }}}}", ""]
        items = []
        for metadata in self.fields:
            # A field the record does not store (a derived header) is not authored.
            if metadata["name"] not in self.schema["properties"]:
                continue
            if metadata["role"] in heading_roles.values():
                continue
            if metadata["level"] not in ("Header", "Item"):
                continue
            name = self.declare(metadata["name"], "", metadata["required"])
            line = f"**{metadata['label']}:** {{{{ {name} }}}}{HARD_BREAK}"
            if not metadata["required"]:
                line = f"{{% if {name} %}}\n{line}\n{{% endif %}}"
            (lines if metadata["level"] == "Header" else items).append(line)
        record_heading = f"## {{{{ {identifier} }}}}: {{{{ {caption} }}}}"
        return "\n".join([*lines, "", "---", "", record_heading, "", *items, "", ""])

    def render(self, kind):
        header = self.header()
        sections = "".join(
            self.section(field) for field in self.fields if field["level"] == "Section"
        )
        frontmatter = [
            "---",
            f"name: {kind}-new",
            "version: 1.0.0",
            f"description: Author one new {kind.upper()} record as a standalone Markdown file.",
            f"required_variables: [{', '.join(self.required)}]",
            "defaults:",
            *(f"  {name}: {json.dumps(value)}" for name, value in self.defaults.items()),
            "---",
        ]
        guidance = " ".join(dict.fromkeys(self.guidance))
        comment = f"{{#- Generated by scripts/authoring_templates.py. {guidance} -#}}\n"
        return "\n".join(frontmatter) + "\n" + comment + MACROS + header + sections


def generate(definitions=None):
    """Return {file name: template text} for every record kind."""
    definitions = definitions or schemas()
    result = {}
    for table, schema in definitions.items():
        for kind in schema["x-raptor-kinds"]:
            kind = kind.lower()
            result[f"{kind}-new.md.j2"] = Layout(schema, table).render(kind)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parents[1] / "templates")
    args = parser.parse_args()
    for name, text in generate().items():
        (args.output_dir / name).write_text(text, encoding="utf-8")
        print(args.output_dir / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
