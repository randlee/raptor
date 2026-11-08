"""Section attribution and aggregation of fully constructed diagnostics."""

from collections import Counter


def section_for_path(fields, path):
    name = path.lstrip("/").split("/", 1)[0]
    return next(
        (
            field["label"]
            for field in fields
            if field["level"] == "Section" and field["name"] == name
        ),
        None,
    )


def group_issues(issues):
    groups = {}
    for issue in issues:
        key = (
            issue["rule"],
            issue["section"] is not None,
            issue["section"] or "",
            issue["label"] is not None,
            issue["label"] or "",
            issue["allowed"] is not None,
            tuple(issue["allowed"] or []),
            issue["remedy"],
        )
        group = groups.setdefault(
            key,
            dict(
                rule=issue["rule"],
                section=issue["section"],
                label=issue["label"],
                allowed=issue["allowed"],
                count=0,
                files={},
                remedy=issue["remedy"],
            ),
        )
        group["count"] += 1
        group["files"].setdefault(issue["file"], []).append(issue["line"])
    return [groups[key] for key in sorted(groups)]


def format_text(issue):
    """One diagnostic in rustc style: `file:line:column: error[RULE]`, source line, caret, fix."""
    where = f"{issue['file']}:{issue['line']}:{issue['column']}"
    gutter = " " * len(str(issue["line"]))
    field = issue["section"] or issue["label"]
    note = f"record {issue['record']}" if issue["record"] else "no record"
    if field:
        note += f", field {field}"
    return "\n".join(
        [
            f"{where}: error[{issue['rule']}]: {issue['message']}",
            f"{gutter}--> {where}",
            f"{gutter} |",
            f"{issue['line']} | {issue['source']}",
            f"{gutter} | {' ' * (issue['column'] - 1)}^",
            f"{gutter} = note: {note}",
            f"{gutter} = help: {issue['fix']}",
        ]
    )
