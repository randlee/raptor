from __future__ import annotations

import json
import ntpath
import os
import secrets
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast


def repository_parts(value: str) -> tuple[str, ...]:
    path = Path(value)
    if (
        not value
        or value == "-"
        or "\\" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(
            "RAPTOR.PATH.OUTSIDE_ROOT: path must be normalized and relative"
        )
    return path.parts


def read_repository_bytes(repository_root: Path, relative: str) -> bytes:
    """Read one repository file without following any path-component symlink."""
    parts = repository_parts(relative)
    if _is_windows():
        return _windows_repository_read(repository_root, parts)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(repository_root, directory_flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=descriptor
        )
        if not stat.S_ISREG(os.fstat(file_descriptor).st_mode):
            os.close(file_descriptor)
            raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: source must be a regular file")
        with os.fdopen(file_descriptor, "rb") as stream:
            return stream.read()
    except OSError as error:
        raise ValueError(
            "RAPTOR.PATH.OUTSIDE_ROOT: file is missing or unsafe"
        ) from error
    finally:
        os.close(descriptor)


def atomic_repository_bytes(repository_root: Path, relative: str, value: bytes) -> None:
    """Atomically publish one file below an existing, no-follow directory tree."""
    parts = repository_parts(relative)
    if _is_windows():
        _windows_repository_publish(repository_root, parts, value)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(repository_root, flags)
    temporary = f".{parts[-1]}.{secrets.token_hex(8)}"
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        file_descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=descriptor,
        )
        with os.fdopen(file_descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, parts[-1], src_dir_fd=descriptor, dst_dir_fd=descriptor)
        os.fsync(descriptor)
    finally:
        try:
            os.unlink(temporary, dir_fd=descriptor)
        except FileNotFoundError:
            pass
        os.close(descriptor)


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


def _is_windows() -> bool:
    return os.name == "nt"


def _windows_repository_read(repository_root: Path, parts: tuple[str, ...]) -> bytes:
    """Read through a verified final Windows handle, never through Path.read_bytes."""
    descriptor = _windows_open_checked(
        repository_root.joinpath(*parts), write=False, directory=False, create=False
    )
    try:
        with os.fdopen(descriptor, "rb") as stream:
            return stream.read()
    except OSError as error:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise ValueError(
            "RAPTOR.PATH.OUTSIDE_ROOT: file is missing or unsafe"
        ) from error


def _windows_repository_publish(
    repository_root: Path, parts: tuple[str, ...], value: bytes
) -> None:
    """Publish using verified handles and a parent-handle-relative rename."""
    parent = repository_root
    parent_descriptor = _windows_open_checked(
        parent, write=False, directory=True, create=False
    )
    try:
        for part in parts[:-1]:
            child = parent / part
            try:
                child_descriptor = _windows_open_checked(
                    child, write=False, directory=True, create=False
                )
            except FileNotFoundError:
                _windows_create_directory(child)
                child_descriptor = _windows_open_checked(
                    child, write=False, directory=True, create=False
                )
            os.close(parent_descriptor)
            parent_descriptor = child_descriptor
            parent = child
        temporary_name = f".{parts[-1]}.{secrets.token_hex(8)}"
        temporary_path = parent / temporary_name
        descriptor = _windows_open_checked(
            temporary_path, write=True, directory=False, create=True
        )
        published = False
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            _windows_rename_relative(descriptor, parent_descriptor, parts[-1])
            published = True
        finally:
            if not published:
                _discard_windows_file(descriptor)
            os.close(descriptor)
    finally:
        os.close(parent_descriptor)


def _windows_open_checked(
    path: Path, *, write: bool, directory: bool, create: bool
) -> int:
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
    access = 0x40000000 if write else 0x80000000
    share = 0 if write else 0x00000001 | 0x00000002 | 0x00000004
    disposition = 1 if create else 3
    flags = 0x00200000 | (0x02000000 if directory else 0x00000080)
    handle = create_file(str(path), access, share, None, disposition, flags, None)
    if handle == ctypes.c_void_p(-1).value:
        error = ctypes.get_last_error()  # type: ignore[attr-defined]
        if error in (2, 3):
            raise FileNotFoundError(str(path))
        raise ctypes.WinError(error)  # type: ignore[attr-defined]
    descriptor = msvcrt.open_osfhandle(  # type: ignore[attr-defined]
        handle,
        (os.O_WRONLY if write else os.O_RDONLY) | getattr(os, "O_BINARY", 0),
    )
    expected = _windows_normal_path(str(path.absolute()))
    if (
        _windows_is_reparse(descriptor)
        or _windows_normal_path(_windows_final_path(descriptor)) != expected
    ):
        os.close(descriptor)
        raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: reparse points are not allowed")
    return cast(int, descriptor)


def _windows_normal_path(value: str) -> str:
    normalized = ntpath.normcase(ntpath.normpath(value))
    return normalized[4:] if normalized.startswith("\\\\?\\") else normalized


def _windows_is_reparse(descriptor: int) -> bool:
    import ctypes
    import msvcrt

    class AttributeTagInfo(ctypes.Structure):
        _fields_ = [("attributes", ctypes.c_uint32), ("tag", ctypes.c_uint32)]

    info = AttributeTagInfo()
    get_osfhandle = cast(Any, getattr(msvcrt, "get_osfhandle"))
    result = ctypes.windll.kernel32.GetFileInformationByHandleEx(  # type: ignore[attr-defined]
        ctypes.c_void_p(get_osfhandle(descriptor)),
        9,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not result:
        raise ctypes.WinError()  # type: ignore[attr-defined]
    return bool(info.attributes & 0x00000400)


def _windows_create_directory(path: Path) -> None:
    import ctypes

    if not ctypes.windll.kernel32.CreateDirectoryW(str(path), None):  # type: ignore[attr-defined]
        error = ctypes.get_last_error()  # type: ignore[attr-defined]
        if error != 183:
            raise ctypes.WinError(error)  # type: ignore[attr-defined]


def _windows_rename_relative(
    descriptor: int, parent_descriptor: int, destination_name: str
) -> None:
    import ctypes
    import msvcrt

    encoded = destination_name.encode("utf-16-le")

    class RenameInfo(ctypes.Structure):
        _fields_ = [
            ("replace", ctypes.c_ubyte),
            ("root", ctypes.c_void_p),
            ("length", ctypes.c_uint32),
            ("name", ctypes.c_byte * len(encoded)),
        ]

    info = RenameInfo()
    get_osfhandle = cast(Any, getattr(msvcrt, "get_osfhandle"))
    info.replace = 1
    info.root = get_osfhandle(parent_descriptor)
    info.length = len(encoded)
    ctypes.memmove(
        ctypes.addressof(info) + RenameInfo.name.offset, encoded, len(encoded)
    )
    if not ctypes.windll.kernel32.SetFileInformationByHandle(  # type: ignore[attr-defined]
        ctypes.c_void_p(get_osfhandle(descriptor)),
        3,
        ctypes.byref(info),
        ctypes.sizeof(info),
    ):
        raise ctypes.WinError()  # type: ignore[attr-defined]


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
