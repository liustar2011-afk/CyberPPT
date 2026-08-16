"""Shared LibreOffice executable discovery and bounded failure diagnostics."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


MAX_FAILURE_OUTPUT_CHARS = 8192


def officecli_path() -> Path | None:
    """Return the PATH-resolved Office CLI executable, when installed."""
    command = shutil.which("officecli")
    return Path(command) if command else None


def obscura_path() -> Path | None:
    """Return the configured Obscura headless-browser executable, when installed."""
    configured = Path("/Applications/obscura")
    return configured if configured.is_file() and configured.stat().st_mode & 0o111 else None


def office_candidates() -> list[Path]:
    """Return PATH Office executables followed by Codex's isolated fallback."""
    candidates = [
        Path(command)
        for command in (shutil.which("soffice"), shutil.which("libreoffice"))
        if command
    ]
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "bin"
        / "override"
        / "soffice"
    )
    if bundled.is_file():
        candidates.append(bundled)
    return list(dict.fromkeys(candidates))


def _bounded_output(value: object) -> object:
    if isinstance(value, str) and len(value) > MAX_FAILURE_OUTPUT_CHARS:
        omitted = len(value) - MAX_FAILURE_OUTPUT_CHARS
        return f"[truncated {omitted} chars] {value[-MAX_FAILURE_OUTPUT_CHARS:]}"
    return value


def office_failure_evidence(candidate: Path, error: BaseException) -> str:
    """Describe a failed Office launch without retaining unbounded output."""
    if isinstance(error, subprocess.CalledProcessError):
        return (
            f"{candidate} exited {error.returncode}; "
            f"stdout={_bounded_output(error.stdout)!r}; stderr={_bounded_output(error.stderr)!r}"
        )
    return f"{candidate} could not be started: {error}"
