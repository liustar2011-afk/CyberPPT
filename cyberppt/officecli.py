"""Pinned, repository-local integration for the OfficeCLI renderer.

OfficeCLI is intentionally kept outside the Python dependency set: it is a
platform-native, self-contained executable.  This module downloads a pinned
release only on an explicit ``cyberppt officecli install`` request and verifies
the release digest before it can be used by render QA.
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

from cyberppt.paths import REPO_ROOT


OFFICECLI_VERSION = "1.0.148"
OFFICECLI_RELEASE_URL = (
    "https://github.com/iOfficeAI/OfficeCLI/releases/download/"
    f"v{OFFICECLI_VERSION}"
)
OFFICECLI_ENV = "CYBERPPT_OFFICECLI"


@dataclass(frozen=True)
class OfficeCliAsset:
    """A supported, digest-pinned OfficeCLI release asset."""

    name: str
    sha256: str


_ASSETS = {
    ("Darwin", "arm64"): OfficeCliAsset(
        "officecli-mac-arm64",
        "501a67fe52ad2afc5cc5626287a204082083db431e5532dd361d6b55158caed1",
    ),
    ("Darwin", "x86_64"): OfficeCliAsset(
        "officecli-mac-x64",
        "235055a83a33e9e675bd85de7a03c9ee657a81d57aad6a24fa41b954caede1b6",
    ),
    ("Linux", "aarch64"): OfficeCliAsset(
        "officecli-linux-arm64",
        "edddf5610b97113bb3c0dc99fac16aade3d3f34746c054ab6fe828679ec48438",
    ),
    ("Linux", "x86_64"): OfficeCliAsset(
        "officecli-linux-x64",
        "e424210bce9355f498eeaf692b4d2b13f1f3422e1db34636c41f54c36025249b",
    ),
    ("Windows", "arm64"): OfficeCliAsset(
        "officecli-win-arm64.exe",
        "e3f67a836b42fc05a8437ab56c260338bc9f6135e083dc67e4be1de1e2cfb0c2",
    ),
    ("Windows", "x86_64"): OfficeCliAsset(
        "officecli-win-x64.exe",
        "df91e48fa250500b05ae1043777af26857e51ed12ea75b2f7a57e3333e3813bf",
    ),
}


def _platform_key() -> tuple[str, str]:
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "arm64": "arm64"}.get(machine, machine)
    if platform.system() == "Linux" and machine == "arm64":
        machine = "aarch64"
    return platform.system(), machine


def supported_asset() -> OfficeCliAsset:
    """Return the official asset for this host, or explain why it is unsupported."""
    key = _platform_key()
    try:
        return _ASSETS[key]
    except KeyError as exc:
        supported = ", ".join(f"{system}/{machine}" for system, machine in sorted(_ASSETS))
        raise RuntimeError(
            f"OfficeCLI v{OFFICECLI_VERSION} has no pinned CyberPPT asset for "
            f"{key[0]}/{key[1]}; supported hosts: {supported}"
        ) from exc


def repository_officecli_path() -> Path:
    """Return the expected repository-local path for the current platform."""
    return REPO_ROOT / ".tools" / "officecli" / f"v{OFFICECLI_VERSION}" / supported_asset().name


def resolve_officecli() -> Path | None:
    """Resolve an explicit override, pinned local binary, then PATH installation."""
    explicit = os.environ.get(OFFICECLI_ENV, "").strip()
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.is_file():
            return candidate.resolve()
    local = repository_officecli_path()
    if local.is_file():
        return local
    command = shutil.which("officecli")
    return Path(command).resolve() if command else None


def installed_version(path: Path) -> str | None:
    """Read a binary version without failing status checks on a broken executable."""
    try:
        completed = subprocess.run(
            [str(path), "--version"], check=False, capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or completed.stderr).strip() or None


def officecli_status() -> dict[str, object]:
    """Return a JSON-ready status report for diagnostics and automation."""
    asset = supported_asset()
    local = repository_officecli_path()
    executable = resolve_officecli()
    source = (
        "environment" if os.environ.get(OFFICECLI_ENV, "").strip() else
        "repository" if local.is_file() else "path" if executable else None
    )
    return {
        "version": OFFICECLI_VERSION,
        "asset": asset.name,
        "repository_path": str(local),
        "installed": executable is not None,
        "executable": str(executable) if executable else None,
        "source": source,
        "detected_version": installed_version(executable) if executable else None,
    }


def install_officecli(*, force: bool = False) -> Path:
    """Download and atomically install the release asset after SHA-256 verification."""
    asset = supported_asset()
    target = repository_officecli_path()
    if target.is_file() and not force:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{OFFICECLI_RELEASE_URL}/{asset.name}"
    with tempfile.NamedTemporaryFile(prefix=f"{asset.name}.", dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            with urlopen(url, timeout=120) as response:
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
            actual = hashlib.sha256(temporary.read_bytes()).hexdigest()
            if actual != asset.sha256:
                raise RuntimeError(
                    f"OfficeCLI checksum mismatch for {asset.name}: expected {asset.sha256}, got {actual}"
                )
            temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return target
