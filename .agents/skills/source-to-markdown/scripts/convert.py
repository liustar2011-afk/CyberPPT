#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _venv_python() -> Path:
    if sys.platform.startswith("win"):
        return ROOT / ".venv" / "Scripts" / "python.exe"
    return ROOT / ".venv" / "bin" / "python"


def _venv_python_candidates() -> tuple[Path, ...]:
    """Return the Skill-local runtime, then the enclosing repository runtime."""
    relative_python = (
        Path("Scripts") / "python.exe"
        if sys.platform.startswith("win")
        else Path("bin") / "python"
    )
    candidates = [_venv_python()]

    for parent in ROOT.parents:
        if (parent / ".git").exists():
            candidates.append(parent / ".venv" / relative_python)
            break

    return tuple(dict.fromkeys(candidates))


def _markitdown_available() -> bool:
    try:
        import markitdown  # noqa: F401
    except ImportError:
        return False
    return True


def _maybe_delegate_to_local_venv() -> int | None:
    if _markitdown_available():
        return None

    current = Path(sys.executable).resolve()
    for candidate in _venv_python_candidates():
        if not candidate.is_file():
            continue

        try:
            if current == candidate.resolve():
                return None
        except OSError:
            pass

        completed = subprocess.run(
            [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]],
            check=False,
        )
        return completed.returncode

    return None


def main() -> int:
    delegated = _maybe_delegate_to_local_venv()
    if delegated is not None:
        return delegated

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from source_to_markdown.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
