"""Test-only CLI adapter for the installed sc_compose 1.6.1 bindings."""

from __future__ import annotations

import json
import sys

import sc_compose


def _argument(name: str) -> str:
    return sys.argv[sys.argv.index(name) + 1]


def main() -> int:
    if sys.argv[1:] == ["--version"]:
        print("sc-compose 1.6.1")
        return 0
    if len(sys.argv) < 2 or sys.argv[1] not in {"render", "validate"}:
        return 2
    variables = None
    if "--var-file" in sys.argv:
        with open(_argument("--var-file"), encoding="utf-8") as source:
            variables = json.load(source)
    request = sc_compose.ComposeRequest(
        root=_argument("--root"),
        mode=sc_compose.ComposeMode.file(_argument("--file")),
        vars_input=variables,
        policy=sc_compose.ComposePolicy(
            strict_undeclared_variables="--strict" in sys.argv,
            unknown_variable_policy=(
                "error"
                if "--unknown-var-mode" in sys.argv
                and _argument("--unknown-var-mode") == "error"
                else "ignore"
            ),
        ),
    )
    try:
        if sys.argv[1] == "validate":
            return 0 if sc_compose.validate(request).ok else 2
        sys.stdout.write(sc_compose.compose(request).rendered_text)
    except sc_compose.ScComposeError:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
