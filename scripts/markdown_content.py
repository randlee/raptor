"""Schema-independent reconstruction of text and list items from splitter nodes."""


def normal(text):
    return " ".join(text.split()).removesuffix(":").rstrip().casefold()


def populated(value):
    if isinstance(value, (dict, list)):
        return any(
            populated(item) for item in (value.values() if isinstance(value, dict) else value)
        )
    return bool(value)


def source_text(node):
    """Keep scalar Markdown content in source order, including list markers and gaps."""
    entries = sorted(node.get("prose", []) + node.get("items", []), key=lambda item: item["line"])
    parts, previous = [], None
    for entry in entries:
        if previous is not None:
            parts.append("\n" * (entry["line"] - previous))
        parts.append(entry.get("raw", entry["value"]))
        previous = entry["line"]
    return "".join(parts)


def list_entries(node):
    """Join adjacent or indented continuations; return detached prose separately."""
    entries, detached = [], []
    previous_line = None
    for entry in sorted(
        node.get("prose", []) + node.get("items", []), key=lambda item: item["line"]
    ):
        if entry in node.get("items", []) or entry["line"] == node["line"]:
            entries.append(dict(entry))
        elif (
            entries
            and previous_line is not None
            and (entry["line"] == previous_line + 1 or entry["value"][:1].isspace())
        ):
            gap = "\n" * (entry["line"] - previous_line)
            # Templates indent continuation lines by the two-character list marker width.
            continuation = entry["value"][2:] if entry["value"].startswith("  ") else entry["value"]
            entries[-1]["value"] += gap + continuation
        else:
            detached.append(entry)
            previous_line = None
            continue
        previous_line = entry["line"]
    return entries, detached
