"""Track validated source identities independently of record content admission."""

from collections import defaultdict


class SourceInventory:
    def __init__(self):
        self.occurrences = defaultdict(list)

    def record(self, context):
        """Called only after the crate validates this heading's scalar identity."""
        self.occurrences[context.record["token"]].append(context)

    def finalize(self, qualifier):
        """Reject every duplicate source occurrence, then retain aligned row mappings."""
        for token, contexts in self.occurrences.items():
            if len(contexts) < 2:
                continue
            first = contexts[0]
            location = dict(
                file=first.file, line=first.record["line"], column=first.record["column"]
            )
            for context in contexts:
                context.issue(
                    "DUPLICATE_ID",
                    context.record,
                    token,
                    message=(
                        f"Found duplicate {token!r}; expected a unique identifier. "
                        f"First occurrence: {location['file']}:{location['line']}:"
                        f"{location['column']}."
                    ),
                )
        for table in qualifier.rows:
            retained = [
                (row, context)
                for row, context in zip(
                    qualifier.rows[table], qualifier.sources[table], strict=True
                )
                if not context.bad
            ]
            qualifier.rows[table] = [row for row, _ in retained]
            qualifier.sources[table] = [context for _, context in retained]
