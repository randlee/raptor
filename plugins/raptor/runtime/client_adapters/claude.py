from __future__ import annotations

from pathlib import Path

from .process import invoke_process


class ClaudeBackend:
    def __init__(self, executable: str = "claude") -> None:
        self.executable = executable

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        return invoke_process(
            [
                self.executable,
                "--print",
                "--append-system-prompt-file",
                str(agent_path),
                prompt,
            ],
            timeout_s,
        )


__all__ = ["ClaudeBackend"]
