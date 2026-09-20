from __future__ import annotations

import subprocess
from pathlib import Path


class ClaudeBackend:
    def __init__(self, executable: str = "claude") -> None:
        self.executable = executable

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        result = subprocess.run(
            [
                self.executable,
                "--print",
                "--append-system-prompt-file",
                str(agent_path),
                prompt,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return result.stdout


__all__ = ["ClaudeBackend"]
