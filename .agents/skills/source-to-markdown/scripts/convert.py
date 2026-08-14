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


def _markitdown_available() -> bool:
    try:
        import markitdown  # noqa: F401
    except ImportError:
        return False
    return True


def _maybe_delegate_to_local_venv() -> int | None:
    candidate = _venv_python()
    if _markitdown_available() or not candidate.is_file():
        return None

    current = Path(sys.executable).resolve()
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
