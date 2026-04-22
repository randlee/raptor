#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
import tomllib


KNOWN_SOURCES = {"startup", "resume", "clear", "compact"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=sorted(KNOWN_SOURCES))
    parser.add_argument("--atm-team", required=True)
    parser.add_argument("--atm-identity", required=True)
    return parser.parse_args(argv[1:])


def load_payload() -> dict[str, object]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"session_start_context.py: invalid JSON input: {exc}", file=sys.stderr)
        return {}
    if isinstance(parsed, dict):
        return parsed
    print("session_start_context.py: expected JSON object payload", file=sys.stderr)
    return {}


def require_nonempty(name: str, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"missing required value: {name}")
    return stripped


def resolve_project_root() -> Path:
    project_dir = require_nonempty("CLAUDE_PROJECT_DIR", os.environ.get("CLAUDE_PROJECT_DIR", ""))
    return Path(project_dir).expanduser().resolve()


def choose_mode(payload: dict[str, object], expected_mode: str | None) -> str:
    payload_source = str(payload.get("source", "")).strip()
    if payload_source in KNOWN_SOURCES:
        if expected_mode and expected_mode != payload_source:
            print(
                "session_start_context.py: matcher mode "
                f"{expected_mode!r} does not match payload source {payload_source!r}; "
                "using payload source",
                file=sys.stderr,
            )
        return payload_source
    if expected_mode in KNOWN_SOURCES:
        return expected_mode
    return "startup"


def load_atm_config(project_root: Path) -> dict[str, object]:
    atm_path = project_root / ".atm.toml"
    if not atm_path.exists():
        raise ValueError(f"missing ATM config: {atm_path}")
    with atm_path.open("rb") as handle:
        parsed = tomllib.load(handle)
    if not isinstance(parsed, dict):
        raise ValueError(f"invalid ATM config root: {atm_path}")
    return parsed


def load_fragment_file(project_root: Path, raw_path: str, field_name: str) -> str:
    relative_path = raw_path.strip()
    if not relative_path:
        raise ValueError(f"startup prompt {field_name!r} file path must not be empty")

    candidate = (project_root / relative_path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(
            f"startup prompt {field_name!r} file path escapes project root: {relative_path}"
        ) from exc

    if not candidate.is_file():
        raise ValueError(
            f"startup prompt {field_name!r} file does not exist: {relative_path}"
        )

    text = candidate.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"startup prompt {field_name!r} file is empty: {relative_path}")
    return text


def normalize_string_fragment(
    value: str,
    *,
    field_name: str,
    project_root: Path,
) -> list[str]:
    text = value.strip()
    if not text:
        raise ValueError(f"startup prompt {field_name!r} must not be empty")
    if text.startswith("@file:"):
        return [load_fragment_file(project_root, text[len("@file:") :], field_name)]
    return [text]


def normalize_fragments(value: object, field_name: str, project_root: Path) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return normalize_string_fragment(value, field_name=field_name, project_root=project_root)
    if isinstance(value, list):
        fragments = []
        for index, item in enumerate(value):
            if not isinstance(item, str):
                raise ValueError(f"startup prompt {field_name!r}[{index}] must be a string")
            fragments.extend(
                normalize_string_fragment(
                    item,
                    field_name=f"{field_name}[{index}]",
                    project_root=project_root,
                )
            )
        return fragments
    raise ValueError(f"startup prompt {field_name!r} must be a string or list of strings")


def collect_mode_fragments(
    table: dict[str, object],
    mode: str,
    table_name: str,
    project_root: Path,
) -> list[str]:
    exact_fragments = []
    grouped_fragments = []
    for key, value in table.items():
        if not isinstance(key, str):
            continue
        normalized_modes = [part.strip() for part in key.split(",") if part.strip()]
        if not normalized_modes:
            continue
        if mode not in normalized_modes:
            continue
        if len(normalized_modes) == 1 and normalized_modes[0] == mode:
            exact_fragments.extend(
                normalize_fragments(value, f"{table_name}.{key}", project_root)
            )
            continue
        grouped_fragments.extend(
            normalize_fragments(value, f"{table_name}.{key}", project_root)
        )

    return exact_fragments or grouped_fragments


def build_context(project_root: Path, identity: str, mode: str) -> str:
    config = load_atm_config(project_root)
    prompt_root = config.get("startup")
    if not isinstance(prompt_root, dict):
        raise ValueError("missing [startup] table in .atm.toml")

    identity_prompts = prompt_root.get(identity)
    if not isinstance(identity_prompts, dict):
        raise ValueError(f"missing [startup.{identity}] table in .atm.toml")

    fragments = []
    fragments.extend(normalize_fragments(prompt_root.get("all"), "startup.all", project_root))
    fragments.extend(
        normalize_fragments(
            identity_prompts.get("all"),
            f"startup.{identity}.all",
            project_root,
        )
    )
    fragments.extend(
        collect_mode_fragments(identity_prompts, mode, f"startup.{identity}", project_root)
    )
    if not fragments:
        raise ValueError(
            f"no startup prompts configured for ATM_IDENTITY={identity!r} and mode={mode!r}"
        )
    return "\n".join(fragments)


def emit_context(context: str) -> int:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))
    return 0


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        payload = load_payload()
        require_nonempty("ATM_TEAM", args.atm_team)
        identity = require_nonempty("ATM_IDENTITY", args.atm_identity)
        project_root = resolve_project_root()
        mode = choose_mode(payload, args.mode)
        context = build_context(project_root, identity, mode)
    except ValueError as exc:
        print(f"session_start_context.py: {exc}", file=sys.stderr)
        return 1
    return emit_context(context)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
