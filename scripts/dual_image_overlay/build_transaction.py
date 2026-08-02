"""Transactional filesystem helpers for CyberPPT production stages.

The image/PPT stages create many intermediate files.  This module keeps the
write protocol in one place: JSON/text artifacts are written through a
same-directory temporary file and builds hold a small cross-process lock so a
second run cannot interleave with the first one.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class BuildLockError(RuntimeError):
    """Raised when another process already owns a build lock."""


def _lock_payload(build_id: str) -> str:
    return json.dumps(
        {
            "schema": "cyberppt.build_lock.v1",
            "build_id": build_id,
            "pid": os.getpid(),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        ensure_ascii=False,
    )


@dataclass
class BuildLock:
    """A cross-process lock represented by an exclusive lock file."""

    path: Path
    build_id: str
    acquired: bool = False

    def acquire(self) -> "BuildLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            owner = ""
            try:
                owner = self.path.read_text(encoding="utf-8")
            except OSError:
                pass
            detail = f" ({owner})" if owner else ""
            raise BuildLockError(f"build is already running: {self.path}{detail}") from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(_lock_payload(self.build_id))
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            self.path.unlink(missing_ok=True)
            raise
        self.acquired = True
        return self

    def release(self) -> None:
        if not self.acquired:
            return
        self.path.unlink(missing_ok=True)
        self.acquired = False

    def __enter__(self) -> "BuildLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


@contextmanager
def build_lock(project_path: Path, build_id: str, *, name: str = ".cyberppt-build.lock") -> Iterator[BuildLock]:
    """Serialize a build against other runs targeting the same project."""

    lock = BuildLock(project_path / name, str(build_id))
    with lock:
        yield lock


def _atomic_replace(path: Path, writer) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "wb") as handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def atomic_write_bytes(path: Path, data: bytes) -> Path:
    """Write bytes and replace the target atomically."""

    return _atomic_replace(path, lambda handle: handle.write(data))


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Write text and replace the target atomically."""

    return atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path: Path, payload: Any) -> Path:
    """Serialize JSON and replace the target atomically."""

    return atomic_write_text(
        path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )


def atomic_copy(source: Path, target: Path) -> Path:
    """Copy a completed file through a temporary sibling before replacing it."""

    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    return _atomic_replace(target, lambda handle: _copy_to_handle(source, handle))


def _copy_to_handle(source: Path, handle) -> None:
    with source.open("rb") as source_handle:
        for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
            handle.write(chunk)


def wait_for_lock(path: Path, *, timeout_seconds: float = 0.0, poll_seconds: float = 0.05) -> None:
    """Wait for a lock to disappear, useful for CLI orchestration tests."""

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while path.exists() and time.monotonic() < deadline:
        time.sleep(poll_seconds)
    if path.exists():
        raise BuildLockError(f"build lock did not clear before timeout: {path}")


__all__ = [
    "BuildLock",
    "BuildLockError",
    "atomic_copy",
    "atomic_write_bytes",
    "atomic_write_json",
    "atomic_write_text",
    "build_lock",
    "wait_for_lock",
]
