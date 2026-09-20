from __future__ import annotations

import os
from collections.abc import Mapping

_ALLOWED = {
    "HOME",
    "LANG",
    "LC_ALL",
    "PATH",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USERPROFILE",
}


def allowed_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    values = os.environ if source is None else source
    return {key: value for key, value in values.items() if key in _ALLOWED}


__all__ = ["allowed_environment"]
