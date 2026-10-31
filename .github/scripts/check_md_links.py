"""Fail when a tracked Markdown file links to a repository path that does not exist.

Only relative links are checked; URLs, mail links and pure in-page anchors
are ignored. Fenced code blocks and inline code spans are skipped so example
syntax is not mistaken for a link.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def tracked_markdown(root: Path, prefixes: list[str]) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", *(prefixes or ["."])],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8", errors="surrogateescape")
    return [root / p for p in out.split("\0") if p.endswith(".md")]


def broken_links(root: Path, path: Path) -> list[tuple[int, str]]:
    broken: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(INLINE_CODE.sub("", line)):
            if target.startswith("#") or EXTERNAL.match(target):
                continue
            relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not relative:
                continue
            base = root if relative.startswith("/") else path.parent
            if not (base / relative.lstrip("/")).exists():
                broken.append((number, target))
    return broken


def main(argv: list[str]) -> int:
    root = Path(
        subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
    )
    failures = 0
    for path in tracked_markdown(root, argv[1:]):
        for number, target in broken_links(root, path):
            print(f"{path.relative_to(root)}:{number}: broken link -> {target}")
            failures += 1
    print(f"markdown link check: {failures} broken link(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
