from __future__ import annotations

import os
import signal
import subprocess
import time
import uuid
from collections.abc import Sequence

from .environment import allowed_environment


def invoke_process(command: Sequence[str], timeout_s: int) -> str:
    invocation_token = uuid.uuid4().hex
    environment = allowed_environment()
    environment["RAPTOR_PROCESS_TOKEN"] = invocation_token
    if os.name == "nt":
        process: subprocess.Popen[str] = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
    else:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
            start_new_session=True,
        )
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired as error:
        _terminate_tree(process, invocation_token)
        raise TimeoutError("agent process exceeded its timeout") from error
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, stdout, stderr)
    return stdout


def _terminate_tree(
    process: subprocess.Popen[str], invocation_token: str | None = None
) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        _terminate_windows(process)
        return
    known = {process.pid}
    for _ in range(4):
        known |= _descendants(known) | _marked_processes(invocation_token)
        for pid in sorted(known, reverse=True):
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        time.sleep(0.05)
    for _ in range(3):
        known |= _descendants(known) | _marked_processes(invocation_token)
        for pid in sorted(known, reverse=True):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.03)
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _terminate_windows(process: subprocess.Popen[str]) -> None:
    for _ in range(3):
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                env=allowed_environment(),
            )
        except OSError:
            process.terminate()
        time.sleep(0.05)
    try:
        process.wait(timeout=0.25)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _descendants(parents: set[int]) -> set[int]:
    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,ppid="],
            check=True,
            capture_output=True,
            text=True,
            env=allowed_environment(),
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    relationships: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        try:
            pid, parent = (int(item) for item in line.split())
        except (TypeError, ValueError):
            continue
        relationships.append((pid, parent))
    discovered: set[int] = set()
    frontier = set(parents)
    while frontier:
        children = {pid for pid, parent in relationships if parent in frontier}
        children -= discovered
        discovered |= children
        frontier = children
    return discovered


def _marked_processes(token: str | None) -> set[int]:
    if token is None:
        return set()
    marker = f"RAPTOR_PROCESS_TOKEN={token}"
    proc = "/proc"
    if os.path.isdir(proc):
        matches: set[int] = set()
        for name in os.listdir(proc):
            if not name.isdigit():
                continue
            try:
                environment = open(f"{proc}/{name}/environ", "rb", buffering=0).read()
            except (OSError, PermissionError):
                continue
            if marker.encode() in environment.split(b"\0"):
                matches.add(int(name))
        return matches
    try:
        result = subprocess.run(
            ["ps", "eww", "-axo", "pid=,command="],
            check=True,
            capture_output=True,
            text=True,
            env=allowed_environment(),
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    matches = set()
    for line in result.stdout.splitlines():
        pid, _, command = line.strip().partition(" ")
        if marker in command:
            try:
                matches.add(int(pid))
            except ValueError:
                pass
    return matches


__all__ = ["invoke_process"]
