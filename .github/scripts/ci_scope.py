"""Classify whether changed repository paths require the runtime CI jobs.

Mirrors atm-core's ``.github/scripts/ci_scope.py``. A path is runtime when it
can change what cargo or pytest builds, loads, or executes. Everything else
(``docs/**``, ``*.md`` outside the trees below, ``.claude/**``, ``plugins/**``
agent prose, ATM/beads metadata) is documentation-only. Runtime prefixes are
checked first, so Markdown the tests load (``tests/fixtures/*.md``) and the
``templates/*.md.j2`` render inputs stay runtime.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterable

RUNTIME_PATHS = (
    # Rust workspace.
    "crates/",
    # Python pipeline, its tests and fixtures.
    "scripts/",
    "tests/",
    # Loaded by scripts/extract.py, scripts/load_sqlite.py and tests/test_record.py.
    "schema/",
    # Default sc-compose template root for scripts/render.py.
    "templates/",
    # Repository config read by scripts/extract.py when run from the repo root.
    ".raptor/",
    # CI itself.
    ".github/workflows/",
    ".github/scripts/",
)
RUNTIME_FILES = {
    "Cargo.toml",
    "Cargo.lock",
    "build.rs",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "conftest.py",
    "pytest.ini",
    "tox.ini",
}


def is_runtime(path: str) -> bool:
    """Return whether one changed path can affect the cargo or pytest jobs."""
    name = path.rsplit("/", 1)[-1]
    return (
        path in RUNTIME_FILES
        or path.startswith(RUNTIME_PATHS)
        or path.startswith("rust-toolchain")
        or path.endswith(".py")
        or (name.startswith("requirements") and name.endswith((".txt", ".in")))
    )


def requires_runtime(changed_paths: Iterable[str]) -> bool:
    """Return whether any changed path requires the runtime jobs."""
    return any(is_runtime(path) for path in changed_paths if path)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: ci_scope.py <range-start> <head>", file=sys.stderr)
        return 2
    changed = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", argv[1], argv[2]],
        check=True,
        capture_output=True,
    ).stdout
    paths = changed.decode("utf-8", errors="surrogateescape").split("\0")
    print(f"runtime={str(requires_runtime(paths)).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
