"""Qualify list, section and group content from schema semantic roles."""

import re

if __package__:
    from .markdown_content import list_entries, source_text
    from .schema_json import empty, resolve, roles
else:
    from markdown_content import list_entries, source_text
    from schema_json import empty, resolve, roles


def parse_items(context, node, metadata, specification, path, offset):
    output = []
    entries, detached = list_entries(node)
    for entry in detached:
        context.issue(
            "BAD_VALUE",
            entry,
            entry["value"],
            metadata["label"],
            message="Expected a list item or its continuation.",
        )
    semantic = roles(specification["items"], context.schema)
    for entry in entries:
        entry = dict(entry, token=metadata["label"])
        raw = entry["value"]
        text = raw.strip()
        shape = metadata["shape"]
        item_path = f"{path}/{offset + len(output)}"
        context.locations[item_path] = (entry, raw, metadata["label"])
        if shape == "StatementList":
            item = {semantic["modality"]: metadata["modal"], semantic["content"]: text}
        elif shape == "Checklist":
            box = re.match(r"^\[([ xX])\]\s+(.*)$", text, re.DOTALL)
            if text.startswith("[") and not box:
                context.issue(
                    "BAD_VALUE",
                    entry,
                    raw,
                    metadata["label"],
                    message=f"Found {raw!r}; expected [ ] text or [x] text.",
                )
            item = {
                semantic["content"]: box[2] if box else text,
                semantic["selection"]: box[1].casefold() == "x" if box else None,
            }
        elif shape in ("IdList", "LinkList"):
            item = parse_reference(context, entry, metadata, specification, semantic, item_path)
        else:
            item = text
        output.append(item)
    return output


def parse_reference(context, entry, metadata, specification, semantic, path):
    raw = entry["value"]
    text = raw.strip()
    link = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)(?:\s+(.*))?", text, re.DOTALL)
    if link:
        token, href, note = link.groups()
    else:
        token, _, note = text.partition(" ")
        href = ""
    shape = metadata["shape"]
    if (text.startswith("[") and not link) or (shape == "LinkList" and not link):
        context.issue(
            "BAD_VALUE",
            entry,
            raw,
            metadata["label"],
            message=f"Found {raw!r}; expected [text](href) with an optional note.",
        )
    note = note.lstrip("—- ").strip() if note else None
    if shape == "LinkList":
        return {
            semantic["content"]: token,
            semantic["destination"]: href,
            semantic["annotation"]: note,
        }
    properties = resolve(specification["items"], context.schema)["properties"]
    source = dict(entry, column=entry["column"] + max(0, raw.find(token)))
    context.locations[path] = (source, token, metadata["label"])
    key = semantic["identifier"]
    return {key: context.scalar(token, properties[key], source), semantic["annotation"]: note}


def parse_content(context, node, metadata, specification, path):
    shape = resolve(specification, context.schema)
    text = source_text(node)
    if shape.get("type") == "string":
        for child in node.get("labels", []) + node.get("group_nodes", []):
            rule = "UNKNOWN_LABEL" if "items" in child else "UNKNOWN_SECTION"
            context.issue(rule, child, child["token"], allowed=[])
        return text
    result = empty(specification, context.schema)
    semantic = roles(specification, context.schema)
    if "content" in semantic:
        result[semantic["content"]] = text
    labels = {
        field["label"]: field
        for field in context.owner.fields[context.table]
        if field["section"] == metadata["label"] and field["name"] in shape["properties"]
    }
    if "collection" in semantic:
        collection = semantic["collection"]
        prop = shape["properties"][collection]["items"]
        child_roles = roles(prop, context.schema)
        for index, group in enumerate(node.get("group_nodes", [])):
            target = parse_content(context, group, metadata, prop, f"{path}/{collection}/{index}")
            if "content" in child_roles:
                target.pop(child_roles["content"], None)
            target[child_roles["caption"]] = group["token"].split(":", 1)[-1].strip()
            result[collection].append(target)
    else:
        for group in node.get("group_nodes", []):
            context.issue("UNKNOWN_SECTION", group, group["token"], metadata["label"], [])
    for label in node.get("labels", []):
        message = (
            f"Found {label['token']!r} under {metadata['label']!r}; "
            "expected a label defined at this level."
        )
        canonical = context.match("labels", label["token"], labels, label, "UNKNOWN_LABEL", message)
        if canonical is None:
            continue
        member = labels[canonical]
        key = member["name"]
        prop = shape["properties"][key]
        target_path = f"{path}/{key}"
        context.locations[target_path] = (label, label["token"], canonical)
        if resolve(prop, context.schema).get("type") == "array":
            values = parse_items(
                context, label, member, resolve(prop, context.schema), target_path, len(result[key])
            )
            result[key].extend(values)
        else:
            result[key] = source_text(label)
    return result
