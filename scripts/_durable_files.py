#!/usr/bin/env python3
"""Narrow POSIX primitives for durable, race-detecting single-file replacement."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
import stat
import tempfile
from pathlib import Path
from typing import Callable, Iterator


class DurableFileError(OSError):
    """A filesystem entry or durable step violated the supported contract."""


FaultHook = Callable[[str], None]
_UNSET = object()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def classify_entry(path: Path) -> str:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return "missing"
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "special"


def require_safe_parent(path: Path) -> os.stat_result:
    parent = path.parent
    try:
        info = parent.lstat()
    except OSError as exc:
        raise DurableFileError(f"cannot inspect parent {parent}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise DurableFileError(f"parent is a symlink: {parent}")
    if not stat.S_ISDIR(info.st_mode):
        raise DurableFileError(f"parent is not a directory: {parent}")
    return info


def require_single_link_regular(path: Path, *, allow_missing: bool = False) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        if allow_missing:
            return None
        raise DurableFileError(f"required file is missing: {path}")
    if stat.S_ISLNK(info.st_mode):
        raise DurableFileError(f"refusing symlink authority file: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise DurableFileError(f"refusing non-regular authority file ({classify_entry(path)}): {path}")
    if info.st_nlink != 1:
        raise DurableFileError(f"refusing authority file with link count {info.st_nlink}: {path}")
    return info


def _open_flags(base: int) -> int:
    return base | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)


def read_regular_bytes(path: Path, *, allow_missing: bool = False) -> tuple[bytes | None, os.stat_result | None]:
    require_safe_parent(path)
    before = require_single_link_regular(path, allow_missing=allow_missing)
    if before is None:
        return None, None
    try:
        fd = os.open(path, _open_flags(os.O_RDONLY))
    except OSError as exc:
        raise DurableFileError(f"cannot securely open {path}: {exc}") from exc
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise DurableFileError(f"opened entry is not a single-link regular file: {path}")
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise DurableFileError(f"entry changed while opening: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks), opened
    finally:
        os.close(fd)


def fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, _open_flags(os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)))
    except OSError as exc:
        raise DurableFileError(f"cannot open directory for fsync {path}: {exc}") from exc
    try:
        os.fsync(fd)
    except OSError as exc:
        raise DurableFileError(f"cannot fsync directory {path}: {exc}") from exc
    finally:
        os.close(fd)


@contextlib.contextmanager
def stable_lock(lock_path: Path) -> Iterator[int]:
    """Exclusively lock a sidecar inode that is never replaced by its caller."""
    require_safe_parent(lock_path)
    existed = classify_entry(lock_path) != "missing"
    if existed:
        require_single_link_regular(lock_path)
    flags = _open_flags(os.O_RDWR | os.O_CREAT)
    try:
        fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise DurableFileError(f"cannot open stable lock {lock_path}: {exc}") from exc
    try:
        os.fchmod(fd, 0o600)
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise DurableFileError(f"stable lock is not a single-link regular file: {lock_path}")
        current = require_single_link_regular(lock_path)
        assert current is not None
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise DurableFileError(f"stable lock changed while opening: {lock_path}")
        if not existed:
            os.fsync(fd)
            fsync_directory(lock_path.parent)
        fcntl.flock(fd, fcntl.LOCK_EX)
        current = require_single_link_regular(lock_path)
        assert current is not None
        if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
            raise DurableFileError(f"stable lock inode changed while waiting: {lock_path}")
        yield fd
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _write_once(fd: int, content: memoryview) -> int:
    return os.write(fd, content)


def _call_fault(fault: FaultHook | None, stage: str) -> None:
    if fault is not None:
        fault(stage)


def _recheck_expected(path: Path, expected_sha256: object) -> None:
    current, _ = read_regular_bytes(path, allow_missing=True)
    if expected_sha256 is _UNSET:
        return
    if expected_sha256 is None:
        if current is not None:
            raise DurableFileError(f"target appeared after planning: {path}")
        return
    if current is None or sha256_bytes(current) != expected_sha256:
        raise DurableFileError(f"target changed after planning: {path}")


def atomic_replace_bytes(
    path: Path,
    content: bytes,
    *,
    mode: int = 0o600,
    expected_sha256: str | None | object = _UNSET,
    fault: FaultHook | None = None,
) -> str:
    """Durably install complete bytes through a same-directory temporary file.

    ``expected_sha256=None`` requires an absent target. A hexadecimal value
    requires those current bytes. Omitting the argument snapshots and rechecks
    the current target automatically.
    """
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    parent_info = require_safe_parent(path)
    initial, _ = read_regular_bytes(path, allow_missing=True)
    if expected_sha256 is _UNSET:
        expected_sha256 = sha256_bytes(initial) if initial is not None else None
    else:
        _recheck_expected(path, expected_sha256)
    fd = -1
    temporary_path: Path | None = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary_path = Path(temporary)
        temp_info = os.fstat(fd)
        if temp_info.st_dev != parent_info.st_dev:
            raise DurableFileError("temporary file is on a different device")
        os.fchmod(fd, mode)
        _call_fault(fault, "before_write")
        remaining = memoryview(content)
        while remaining:
            written = _write_once(fd, remaining)
            if written <= 0:
                raise DurableFileError("zero-progress write")
            remaining = remaining[written:]
        _call_fault(fault, "after_write")
        os.fsync(fd)
        _call_fault(fault, "after_file_fsync")
        os.close(fd)
        fd = -1
        require_safe_parent(path)
        _recheck_expected(path, expected_sha256)
        _call_fault(fault, "before_replace")
        os.replace(temporary_path, path)
        temporary_path = None
        _call_fault(fault, "after_replace")
        fsync_directory(path.parent)
        _call_fault(fault, "after_dir_fsync")
        _call_fault(fault, "before_reopen")
        installed, installed_info = read_regular_bytes(path)
        _call_fault(fault, "after_reopen")
        if installed != content or sha256_bytes(installed or b"") != sha256_bytes(content):
            raise DurableFileError(f"installed-byte verification failed: {path}")
        if installed_info is None or installed_info.st_dev != parent_info.st_dev:
            raise DurableFileError(f"installed file is on an unexpected device: {path}")
        _call_fault(fault, "after_verify")
        return sha256_bytes(content)
    except OSError as exc:
        if isinstance(exc, DurableFileError):
            raise
        raise DurableFileError(f"durable replacement failed for {path}: {exc}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary_path is not None:
            try:
                info = temporary_path.lstat()
            except FileNotFoundError:
                pass
            else:
                if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                    try:
                        temporary_path.unlink()
                    except FileNotFoundError:
                        pass


def durable_unlink(path: Path, *, expected_sha256: str) -> None:
    """Remove one exact single-link regular file and durably record the unlink."""
    require_safe_parent(path)
    current, _ = read_regular_bytes(path)
    if current is None or sha256_bytes(current) != expected_sha256:
        raise DurableFileError(f"target changed before durable unlink: {path}")
    try:
        path.unlink()
        fsync_directory(path.parent)
    except OSError as exc:
        raise DurableFileError(f"durable unlink failed for {path}: {exc}") from exc
