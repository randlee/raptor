#!/usr/bin/env python3
"""Load or dump a schema-defined SQLite index."""

import argparse
import json
from pathlib import Path

if __package__:
    from .sqlite_records import dump, load
else:
    from sqlite_records import dump, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("--dump", action="store_true")
    args = parser.parse_args()
    if args.dump:
        print(json.dumps(dump(args.paths[0])))
    else:
        load(json.loads(args.paths[0].read_text()), args.paths[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
