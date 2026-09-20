from __future__ import annotations

import json
import ntpath
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
        _secure_windows_json(repository_root, directories, filename, value)
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
            os.link(
                temporary,
                filename,
                src_dir_fd=descriptor,
                dst_dir_fd=descriptor,
                follow_symlinks=False,
            )
            os.unlink(temporary, dir_fd=descriptor)
            os.fsync(descriptor)
        finally:
            try:
                os.unlink(temporary, dir_fd=descriptor)
            except FileNotFoundError:
                pass
    finally:
        os.close(descriptor)


def _secure_windows_json(
    repository_root: Path,
    directories: tuple[str, ...],
    filename: str,
    value: Mapping[str, Any],
) -> None:
    target = repository_root.joinpath(*directories)
    target.mkdir(parents=True, exist_ok=True)
    destination = target / filename
    descriptor = _windows_open_exclusive(destination)
    try:
        expected = ntpath.normcase(ntpath.normpath(str(destination.absolute())))
        actual = ntpath.normcase(ntpath.normpath(_windows_final_path(descriptor)))
        if actual.startswith("\\\\?\\"):
            actual = actual[4:]
        if actual != expected:
            _discard_windows_file(descriptor)
            raise ValueError("secure path contains a reparse point")
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=False) as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def _windows_open_exclusive(path: Path) -> int:
    import ctypes
    import msvcrt

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        str(path),
        0x40000000,
        0,
        None,
        1,
        0x80,
        None,
    )
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(  # type: ignore[attr-defined]
            ctypes.get_last_error()  # type: ignore[attr-defined]
        )
    return msvcrt.open_osfhandle(  # type: ignore[attr-defined,no-any-return]
        handle, os.O_WRONLY | getattr(os, "O_BINARY", 0)
    )


def _windows_final_path(descriptor: int) -> str:
    import ctypes
    import msvcrt

    handle = msvcrt.get_osfhandle(descriptor)  # type: ignore[attr-defined]
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetFinalPathNameByHandleW(  # type: ignore[attr-defined]
        ctypes.c_void_p(handle), buffer, len(buffer), 0
    )
    if length == 0 or length >= len(buffer):
        raise OSError("cannot resolve secure audit handle")
    return buffer.value


def _discard_windows_file(descriptor: int) -> None:
    import ctypes
    import msvcrt

    delete = ctypes.c_int(1)
    ctypes.windll.kernel32.SetFileInformationByHandle(  # type: ignore[attr-defined]
        ctypes.c_void_p(
            msvcrt.get_osfhandle(descriptor)  # type: ignore[attr-defined]
        ),
        4,
        ctypes.byref(delete),
        ctypes.sizeof(delete),
    )


__all__ = ["atomic_json", "fsync_directory", "fsync_tree", "secure_repository_json"]
