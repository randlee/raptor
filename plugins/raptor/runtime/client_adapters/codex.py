from __future__ import annotations

import subprocess
from pathlib import Path


class CodexBackend:
    def __init__(self, executable: str = "codex") -> None:
        self.executable = executable

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        result = subprocess.run(
            [self.executable, "exec", "--config", f"agent_file={agent_path}", prompt],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return result.stdout


__all__ = ["CodexBackend"]
