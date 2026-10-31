"""Compose one schema-derived Markdown document and write its record file."""

import sc_compose as sc

if __package__:
    from .render_context import document_context
    from .schema_json import schemas
else:
    from render_context import document_context
    from schema_json import schemas


def render(record, table, templates, output, definitions=None):
    definitions = definitions or schemas()
    identifier, document = document_context(record, table, definitions)
    template = definitions[table]["x-raptor-tables"][table]["template"]
    request = sc.ComposeRequest(
        root=templates.parent,
        mode=sc.ComposeMode.file(f"{templates.name}/{template}.md.j2"),
        vars_input={"document": document},
    )
    target = output / table / f"{identifier}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(sc.compose_file(request).rendered_text.rstrip() + "\n", encoding="utf-8")
