from __future__ import annotations

import json
import ntpath
import os
import secrets
import stat
import tempfile
from contextlib import contextmanager
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterator, cast


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


def remove_repository_file(repository_root: Path, relative: str) -> None:
    """Remove one regular repository file through its retained parent handle."""
    parts = repository_parts(relative)
    if _is_windows():
        parent = _windows_open_checked(
            repository_root, write=True, directory=True, create=False
        )
        try:
            for part in parts[:-1]:
                child = _windows_open_relative(
                    parent, part, write=True, directory=True, create=False
                )
                os.close(parent)
                parent = child
            try:
                descriptor = _windows_open_relative(
                    parent, parts[-1], write=True, directory=False, create=False
                )
            except FileNotFoundError:
                return
            try:
                _discard_windows_file(descriptor)
            finally:
                os.close(descriptor)
        finally:
            os.close(parent)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    parent = os.open(repository_root, flags)
    try:
        for part in parts[:-1]:
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        try:
            info = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("RAPTOR.PATH.OUTSIDE_ROOT: removal target is unsafe")
        os.unlink(parts[-1], dir_fd=parent)
        os.fsync(parent)
    finally:
        os.close(parent)


@contextmanager
def repository_lock(repository_root: Path, relative: str) -> Iterator[None]:
    """Hold a process-scoped lock; a crash releases it without stale lock state."""
    parts = repository_parts(relative)
    if _is_windows():
        import msvcrt

        parent = _windows_open_checked(
            repository_root, write=True, directory=True, create=False
        )
        try:
            for part in parts[:-1]:
                try:
                    child = _windows_open_relative(
                        parent, part, write=True, directory=True, create=True
                    )
                except OSError:
                    child = _windows_open_relative(
                        parent, part, write=True, directory=True, create=False
                    )
                os.close(parent)
                parent = child
            try:
                descriptor = _windows_open_relative(
                    parent, parts[-1], write=True, directory=False, create=True
                )
            except OSError:
                descriptor = _windows_open_relative(
                    parent, parts[-1], write=True, directory=False, create=False
                )
            try:
                if os.fstat(descriptor).st_size == 0:
                    os.write(descriptor, b"0")
                os.lseek(descriptor, 0, os.SEEK_SET)
                try:
                    locking = cast(Any, getattr(msvcrt, "locking"))
                    locking(descriptor, getattr(msvcrt, "LK_NBLCK"), 1)
                except OSError as error:
                    raise BlockingIOError from error
                yield
            finally:
                os.close(descriptor)
        finally:
            os.close(parent)
        return
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    parent = os.open(repository_root, flags)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=parent)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(
            parts[-1],
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
            dir_fd=parent,
        )
        try:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        finally:
            os.close(descriptor)
    finally:
        os.close(parent)


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
    """Read through retained, no-reparse handles rooted at the repository."""
    descriptor = _windows_open_checked(
        repository_root, write=False, directory=True, create=False
    )
    try:
        for part in parts[:-1]:
            child = _windows_open_relative(
                descriptor, part, write=False, directory=True, create=False
            )
            os.close(descriptor)
            descriptor = child
        file_descriptor = _windows_open_relative(
            descriptor, parts[-1], write=False, directory=False, create=False
        )
        with os.fdopen(file_descriptor, "rb") as stream:
            return stream.read()
    except OSError as error:
        raise ValueError(
            "RAPTOR.PATH.OUTSIDE_ROOT: file is missing or unsafe"
        ) from error
    finally:
        os.close(descriptor)


def _windows_repository_publish(
    repository_root: Path, parts: tuple[str, ...], value: bytes
) -> None:
    """Publish using verified handles and a parent-handle-relative rename."""
    parent_descriptor = _windows_open_checked(
        repository_root, write=True, directory=True, create=False
    )
    try:
        for part in parts[:-1]:
            child_descriptor = _windows_open_relative(
                parent_descriptor,
                part,
                write=True,
                directory=True,
                create=True,
            )
            os.close(parent_descriptor)
            parent_descriptor = child_descriptor
        temporary_name = f".{parts[-1]}.{secrets.token_hex(8)}"
        descriptor = _windows_open_relative(
            parent_descriptor,
            temporary_name,
            write=True,
            directory=False,
            create=True,
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
    access = (0xC0000000 | (0x00000040 if directory else 0)) if write else 0x80000000
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


def _windows_open_relative(
    parent_descriptor: int,
    name: str,
    *,
    write: bool,
    directory: bool,
    create: bool,
) -> int:
    """Open/create one child with NtCreateFile RootDirectory semantics."""
    import ctypes
    import msvcrt

    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ushort),
            ("maximum_length", ctypes.c_ushort),
            ("buffer", ctypes.c_wchar_p),
        ]

    class ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("root_directory", ctypes.c_void_p),
            ("object_name", ctypes.POINTER(UnicodeString)),
            ("attributes", ctypes.c_ulong),
            ("security_descriptor", ctypes.c_void_p),
            ("security_quality_of_service", ctypes.c_void_p),
        ]

    class IoStatusBlock(ctypes.Structure):
        _fields_ = [("status", ctypes.c_void_p), ("information", ctypes.c_size_t)]

    buffer = ctypes.create_unicode_buffer(name)
    encoded_length = len(name.encode("utf-16-le"))
    unicode_name = UnicodeString(
        encoded_length, encoded_length + 2, ctypes.cast(buffer, ctypes.c_wchar_p)
    )
    get_osfhandle = cast(Any, getattr(msvcrt, "get_osfhandle"))
    attributes = ObjectAttributes(
        ctypes.sizeof(ObjectAttributes),
        get_osfhandle(parent_descriptor),
        ctypes.pointer(unicode_name),
        0x40,
        None,
        None,
    )
    status_block = IoStatusBlock()
    handle = ctypes.c_void_p()
    access = 0x00100000 | 0x00000080 | 0x00000001
    if write:
        access |= 0x00000002 | 0x00000100
        if directory:
            access |= 0x00000004 | 0x00000040
    if write and not directory:
        access |= 0x00010000  # DELETE is required by FileRenameInfo.
    options = 0x00200000 | 0x00000020 | (0x1 if directory else 0x40)
    disposition = 3 if create and directory else 2 if create else 1
    nt_create_file = cast(
        Any,
        ctypes.windll.ntdll.NtCreateFile,  # type: ignore[attr-defined]
    )
    nt_create_file.argtypes = [
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_uint32,
        ctypes.POINTER(ObjectAttributes),
        ctypes.POINTER(IoStatusBlock),
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
    ]
    nt_create_file.restype = ctypes.c_long
    status = nt_create_file(
        ctypes.byref(handle),
        access,
        ctypes.byref(attributes),
        ctypes.byref(status_block),
        None,
        0x80,
        0x7,
        disposition,
        options,
        None,
        0,
    )
    if status < 0:
        unsigned = status & 0xFFFFFFFF
        if unsigned in (0xC0000034, 0xC000003A):
            raise FileNotFoundError(name)
        raise OSError(f"NtCreateFile failed with NTSTATUS 0x{unsigned:08x}")
    descriptor = msvcrt.open_osfhandle(  # type: ignore[attr-defined]
        handle.value,
        (os.O_RDWR if write else os.O_RDONLY) | getattr(os, "O_BINARY", 0),
    )
    if _windows_is_reparse(descriptor):
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


__all__ = [
    "atomic_json",
    "atomic_repository_bytes",
    "fsync_directory",
    "fsync_tree",
    "read_repository_bytes",
    "remove_repository_file",
    "repository_lock",
    "repository_parts",
    "secure_repository_json",
]
