from __future__ import annotations

import json
import os
import secrets
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_tree(root: Path) -> None:
    if os.name == "nt":
        return
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    fsync_directory(root)


def atomic_json(
    path: Path, value: Mapping[str, Any], *, indent: int | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            separators = (",", ":") if indent is None else None
            json.dump(
                value, stream, sort_keys=True, separators=separators, indent=indent
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def secure_repository_json(
    repository_root: Path,
    directories: tuple[str, ...],
    filename: str,
    value: Mapping[str, Any],
) -> None:
    if os.name == "nt":
        target = repository_root
        for name in directories:
            target = target / name
            if target.is_symlink():
                raise ValueError("secure path contains a symlink")
            target.mkdir(exist_ok=True)
            if repository_root not in target.resolve().parents:
                raise ValueError("secure path escapes repository root")
        if (target / filename).is_symlink():
            raise ValueError("secure destination is a symlink")
        atomic_json(target / filename, value)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(repository_root, flags)
    try:
        for name in directories:
            try:
                os.mkdir(name, mode=0o700, dir_fd=descriptor)
            except FileExistsError:
                pass
            try:
                child = os.open(name, flags, dir_fd=descriptor)
            except OSError as error:
                raise ValueError(
                    "secure path contains a symlink or non-directory"
                ) from error
            os.close(descriptor)
            descriptor = child
        try:
            os.stat(filename, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(
                os.stat(filename, dir_fd=descriptor, follow_symlinks=False).st_mode
            ):
                raise ValueError("secure destination is a symlink")
        temporary = f".{filename}.{secrets.token_hex(8)}"
        try:
            file_descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=descriptor,
            )
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(
                temporary, filename, src_dir_fd=descriptor, dst_dir_fd=descriptor
            )
            os.fsync(descriptor)
        finally:
            try:
                os.unlink(temporary, dir_fd=descriptor)
            except FileNotFoundError:
                pass
    finally:
        os.close(descriptor)


__all__ = ["atomic_json", "fsync_directory", "fsync_tree", "secure_repository_json"]
