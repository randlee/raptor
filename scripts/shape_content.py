"""Qualify list, section and group content from schema semantic roles."""

import json
import re

import raptor_schema

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
        item_path = f"{path}/{offset + len(output)}"
        context.locations[item_path] = (entry, raw, metadata["label"])
        if "modality" in semantic:
            check_modality(context, entry, metadata, raw)
            item = {semantic["modality"]: metadata["modal"], semantic["content"]: text}
        elif "selection" in semantic:
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
        elif "identifier" in semantic or "destination" in semantic:
            item = parse_reference(context, entry, metadata, specification, semantic, item_path)
        else:
            item = text
        output.append(item)
    return output


def check_modality(context, entry, metadata, raw):
    """Report a statement whose own keyword disagrees with its label's modal.

    The label still decides the stored modal; this only makes the source defect
    findable. Inline code spans are blanked first so quoted keywords do not count.
    """
    prose = re.sub(r"`[^`]*`", lambda span: " " * len(span[0]), raw)
    found = raptor_schema.modal_mismatch(metadata["modal"], prose)
    if found is None:
        return
    mismatch = json.loads(found)
    start = mismatch["offset"]
    keyword = raw[start : start + mismatch["length"]]
    before = raw[:start]
    line = entry["line"] + before.count("\n")
    if "\n" in before:
        column = context.lines[line - 1].find(keyword.split()[0]) + 1 or entry["column"]
    else:
        column = entry["column"] + start
    source = context.lines[line - 1]
    expected = mismatch["expected"]
    swap = (
        None
        if "\n" in keyword or source[column - 1 :][: len(keyword)] != keyword
        else dict(
            op="replace",
            line=line,
            lines=[source[: column - 1] + expected + source[column - 1 + len(keyword) :]],
        )
    )
    context.issue(
        "MODAL_MISMATCH",
        dict(entry, line=line, column=column),
        mismatch["found"],
        metadata["label"],
        allowed=[mismatch["expected"]],
        message=(
            f"Found {mismatch['found']!r} in a statement under {metadata['label']!r}; "
            f"expected {mismatch['expected']!r} or no keyword. The label's modal is kept."
        ),
        fix=(
            f"replace `{keyword}` at line {line}, column {column} with `{expected}`, "
            "or reword the statement without a modal keyword"
        ),
        edit=swap,
    )


def parse_reference(context, entry, metadata, specification, semantic, path):
    raw = entry["value"]
    text = raw.strip()
    link = re.fullmatch(r"\[([^\]]+)\]\(([^\s)]+)\)(?:\s+(.*))?", text, re.DOTALL)
    if link:
        token, href, note = link.groups()
    else:
        token, _, note = text.partition(" ")
        href = ""
    if (text.startswith("[") and not link) or ("destination" in semantic and not link):
        context.issue(
            "BAD_VALUE",
            entry,
            raw,
            metadata["label"],
            message=f"Found {raw!r}; expected [text](href) with an optional note.",
        )
    note = note.lstrip("—- ").strip() if note else None
    if "destination" in semantic:
        return {
            semantic["content"]: token,
            semantic["destination"]: href,
            semantic["annotation"]: note,
        }
    properties = resolve(specification["items"], context.schema)["properties"]
    offset = raw.find(token)
    if offset < 0:
        raise ValueError(f"Reference token {token!r} is absent from its source item")
    source = dict(entry, column=entry["column"] + offset)
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
