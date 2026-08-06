from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..pages_index import active_page_files


_HANDOFF_TARGETS: dict[str, tuple[str, ...]] = {
    "decision": ("decision/01-decision.md",),
    "expression": ("decision/02-expression-logic.md",),
    "outline": ("outline/02-outline.md",),
    "authoring": (
        "decision/01-decision.md",
        "decision/02-expression-logic.md",
        "outline/02-outline.md",
    ),
    "pages": (),  # resolved dynamically
}


def _file_url(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if resolved.startswith("/"):
        return f"file://{resolved}"
    # Windows drive path: D:/...
    return f"file:///{resolved}"


def _open_directory(path: Path) -> None:
    """Open a folder in the OS file manager so the user can browse deliverables."""
    folder = path if path.is_dir() else path.parent
    if not folder.exists():
        return
    target = str(folder.resolve())
    if sys.platform.startswith("win"):
        subprocess.run(["explorer.exe", target], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", target], check=False)
    else:
        subprocess.run(["xdg-open", target], check=False)


def _reveal(path: Path) -> None:
    """Reveal a file (select in folder) or open a directory."""
    if not path.exists():
        return
    if path.is_dir():
        _open_directory(path)
        return
    target = str(path.resolve())
    if sys.platform.startswith("win"):
        subprocess.run(["explorer.exe", f"/select,{target}"], check=False)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", target], check=False)
    else:
        _open_directory(path)


def _with_directories(paths: list[Path]) -> list[Path]:
    """Ensure containing directories appear first so users can open folders via links."""
    ordered: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        folder = resolved if resolved.is_dir() else resolved.parent
        for candidate in (folder, resolved):
            if candidate in seen or not candidate.exists():
                continue
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def resolve_handoff_paths(project: Path, target: str) -> list[Path]:
    key = target.strip().lower()
    if key == "pages":
        paths = active_page_files(project)
        pages_dir = project / "pages"
        if pages_dir.is_dir():
            return _with_directories([pages_dir, *paths])
        return _with_directories(paths)
    if key not in _HANDOFF_TARGETS:
        raise ValueError(
            f"未知 handoff 目标：{target}；可选 decision|expression|outline|authoring|pages"
        )
    return _with_directories([project / relative for relative in _HANDOFF_TARGETS[key]])


def _should_reveal(reveal: bool | None) -> bool:
    """Default: do not open the OS file manager. Opt in via reveal=True or env."""
    if reveal is True:
        return True
    if reveal is False:
        return False
    return os.environ.get("PPT_SCRIPT_HANDOFF_REVEAL") == "1"


def handoff_command(project: Path, target: str, *, reveal: bool | None = None) -> list[Path]:
    paths = resolve_handoff_paths(project, target)
    existing = [path for path in paths if path.exists()]
    if not existing:
        raise FileNotFoundError(f"handoff 目标不存在可用文件：{target}")
    if _should_reveal(reveal):
        # Opt-in: open the primary deliverable directory; then select up to a few files.
        primary_dir = existing[0] if existing[0].is_dir() else existing[0].parent
        _open_directory(primary_dir)
        selected = 0
        for path in existing:
            if path.is_file() and selected < 3:
                _reveal(path)
                selected += 1
    return existing


def format_handoff_links(paths: list[Path]) -> list[str]:
    lines: list[str] = []
    for path in paths:
        if path.is_dir():
            label = f"打开目录：{path.name}/"
        else:
            label = path.name
        lines.append(f"- [{label}]({_file_url(path)})")
    return lines
