from __future__ import annotations

from pathlib import Path

from .process import invoke_process


class CodexBackend:
    def __init__(self, executable: str = "codex") -> None:
        self.executable = executable

    def invoke(self, *, agent_path: Path, prompt: str, timeout_s: int) -> str:
        return invoke_process(
            [self.executable, "exec", "--config", f"agent_file={agent_path}", prompt],
            timeout_s,
        )


__all__ = ["CodexBackend"]
