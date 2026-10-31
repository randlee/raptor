"""Build a Markdown layout context solely from exported schema metadata."""

if __package__:
    from .schema_json import resolve, roles
else:
    from schema_json import resolve, roles


def list_value(value, metadata, specification, schema):
    semantic = roles(specification["items"], schema)
    if not isinstance(value, dict):
        return value
    if "modality" in semantic and value[semantic["modality"]] != metadata["modal"]:
        return None
    content = value.get(semantic.get("content", ""), "")
    if "identifier" in semantic:
        content = value[semantic["identifier"]]
    if "destination" in semantic:
        content = f"[{content}]({value[semantic['destination']]})"
    if "selection" in semantic:
        selected = value[semantic["selection"]]
        content = ("[x] " if selected is True else "[ ] " if selected is False else "") + content
    annotation = value.get(semantic.get("annotation", ""))
    return content + (f" — {annotation}" if annotation else "")


def section_nodes(value, field, specification, schema, fields, table_info):
    if isinstance(value, str):
        return [{"kind": "prose", "body": value}]
    shape = resolve(specification, schema)
    semantic = roles(specification, schema)
    nodes = [{"kind": "prose", "body": value.get(semantic.get("content", ""), "")}]
    if "collection" in semantic:
        collection = semantic["collection"]
        prop = shape["properties"][collection]["items"]
        child_roles = roles(prop, schema)
        for number, group in enumerate(value[collection], 1):
            caption = group[child_roles["caption"]]
            prefix = table_info["group_heading_prefix"]
            nodes.append({"kind": "group", "body": f"{prefix} {number}: {caption}"})
            nodes.extend(section_nodes(group, field, prop, schema, fields, table_info))
        return nodes
    for metadata in fields:
        if metadata["level"] != "Label" or metadata["section"] != field["label"]:
            continue
        key = metadata["name"]
        if key not in shape["properties"]:
            continue
        prop = shape["properties"][key]
        nodes.append({"kind": "label", "body": metadata["label"]})
        if resolve(prop, schema).get("type") == "array":
            for item in value[key]:
                body = list_value(item, metadata, resolve(prop, schema), schema)
                if body is not None:
                    nodes.append({"kind": "item", "body": body})
        else:
            nodes.append({"kind": "prose", "body": value[key]})
    return nodes


def document_context(record, table, definitions):
    schema = definitions[table]
    fields = schema["x-raptor-fields"]
    info = schema["x-raptor-tables"][table]
    headings = {
        field["role"]: record[field["name"]]
        for field in fields
        if field["role"].startswith("heading_")
    }
    headers, items, sections = [], [], []
    for field in fields:
        key = field["name"]
        if field["level"] == "Header":
            if field["shape"] == "Derived":
                identifier = headings["heading_id"]
                value = identifier + info["range_separator"] + identifier
            else:
                value = record[key]
            if field["required"] or value:
                headers.append({"caption": field["label"], "body": value})
        elif field["level"] == "Item" and not field["role"].startswith("heading_"):
            items.append({"caption": field["label"], "body": record[key]})
        elif field["level"] == "Section":
            nodes = section_nodes(
                record[key], field, schema["properties"][key], schema, fields, info
            )
            sections.append({"caption": field["label"], "nodes": nodes})
    document = dict(
        heading_label=info["heading_label"],
        headers=headers,
        item_fields=items,
        sections=sections,
        **headings,
    )
    return headings["heading_id"], document
