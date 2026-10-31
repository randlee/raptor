#!/usr/bin/env python3
"""Build a Raptor index from the configured Markdown inventory."""

import json

if __package__:
    from .import_corpus import inventory, run_import
    from .markdown_splitter import split
else:
    from import_corpus import inventory, run_import
    from markdown_splitter import split


def main():
    report, result = run_import()
    print(json.dumps(report))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
