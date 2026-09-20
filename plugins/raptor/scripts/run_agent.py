#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.agent_runner import run_agent  # noqa: E402
from runtime.cli import emit, failure  # noqa: E402
from runtime.client_adapters.claude import ClaudeBackend  # noqa: E402
from runtime.client_adapters.codex import CodexBackend  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("agent")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--client", choices=("claude", "codex"), required=True)
    parser.add_argument("--version")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--correlation-id")
    arguments = parser.parse_args()
    try:
        backend = ClaudeBackend() if arguments.client == "claude" else CodexBackend()
        result = run_agent(
            agent=arguments.agent,
            params=json.loads(arguments.params),
            version_constraint=arguments.version,
            timeout_s=arguments.timeout,
            correlation_id=arguments.correlation_id,
            backend=backend,
        )
    except Exception as error:
        result = failure(error)
    return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
