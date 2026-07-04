"""Resolve the repo-local .venv Python for preview / strict pipeline scripts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPTS_DIR.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def repo_root() -> Path:
    return REPO_ROOT


def venv_python() -> Path | None:
    return VENV_PYTHON if VENV_PYTHON.is_file() else None


def using_venv_python() -> bool:
    """True when the active interpreter is the repo .venv (not merely the same base binary)."""
    try:
        return Path(sys.prefix).resolve() == (REPO_ROOT / ".venv").resolve()
    except OSError:
        return False


def module_importable(python: Path, module: str) -> bool:
    probe = subprocess.run(
        [str(python), "-c", f"import {module}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return probe.returncode == 0


def missing_modules(python: Path | None = None, *, modules: tuple[str, ...] = ("cairosvg",)) -> list[str]:
    interpreter = python or Path(sys.executable)
    return [name for name in modules if not module_importable(interpreter, name)]


def preview_runtime_hint() -> str:
    if venv_python() is None:
        return (
            f"No .venv found at {REPO_ROOT / '.venv'}. "
            "Create one and install cairosvg: "
            "python3 -m venv .venv && .venv/bin/pip install cairosvg"
        )
    lines = [
        f"source {REPO_ROOT / '.venv' / 'bin' / 'activate'}",
    ]
    if sys.platform == "darwin":
        lines.append("macOS: brew install cairo")
    lines.append(f"Or run scripts with: {VENV_PYTHON.relative_to(REPO_ROOT)}")
    return "\n".join(lines)


def maybe_reexec_with_venv(*, modules: tuple[str, ...] = ("cairosvg",)) -> None:
    """
    Re-exec the current script with repo .venv when the active interpreter lacks
    preview dependencies but .venv has them.
    """
    if not missing_modules():
        return
    candidate = venv_python()
    if candidate is None or using_venv_python():
        return
    if missing_modules(candidate, modules=modules):
        return
    os.execv(str(candidate), [str(candidate), *sys.argv])


def venv_cairo_status() -> dict[str, object]:
    candidate = venv_python()
    if candidate is None:
        return {"available": False, "path": None, "cairosvg": False}
    return {
        "available": True,
        "path": str(candidate.relative_to(REPO_ROOT)),
        "cairosvg": not missing_modules(candidate, modules=("cairosvg",)),
    }
