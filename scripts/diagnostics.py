"""Diagnostic construction, section attribution, and summary grouping."""

REMEDIES = {
    "MISSING_ID": "Add the required field.", "MISSING_FIELD": "Add the required field.",
    "BAD_VALUE": "Use the documented value format.",
    "UNKNOWN_SECTION": "Remove the section or use an allowed section.",
    "UNKNOWN_LABEL": "Remove the label or use an allowed label.",
    "DUPLICATE_ID": "Make the identifier unique.",
    "DANGLING_REFERENCE": "Declare the referenced identifier or remove the reference.",
}



def issue(self, rule, node, value, label=None, allowed=None, message=None):
    line = node.get("line", 1)
    raw = self.lines[line - 1] if 0 < line <= len(self.lines) else ""
    column = node.get("column", max(0, raw.find(str(value))) + 1)
    self.issues.append(dict(file=self.file, line=line, column=column, rule=rule, id=self.record.get("id"),
        section=self.section, label=label, value=value, allowed=allowed, message=message or f"Found {value!r}; expected {allowed or label or rule.lower()}.",
        remedy=REMEDIES[rule]))
    self.bad |= rule in ("BAD_VALUE", "MISSING_FIELD", "MISSING_ID")


def section_for_path(fields, path):
    name = path.lstrip("/").split("/", 1)[0]
    return next((field["label"] for field in fields if field["level"] == "Section" and field["name"] == name), None)


def group_issues(issues):
    groups = {}
    for issue in issues:
        key = (issue["rule"], issue["section"] is not None, issue["section"] or "", issue["label"] is not None,
               issue["label"] or "", issue["allowed"] is not None, tuple(issue["allowed"] or []), issue["remedy"])
        group = groups.setdefault(key, dict(rule=issue["rule"], section=issue["section"], label=issue["label"],
            allowed=issue["allowed"], count=0, files={}, remedy=issue["remedy"]))
        group["count"] += 1
        group["files"].setdefault(issue["file"], []).append(issue["line"])
    return [groups[key] for key in sorted(groups)]
