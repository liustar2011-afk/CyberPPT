#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "cyberppt-handoff"
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

from scripts.export import main  # type: ignore[import-not-found]


if __name__ == "__main__":
    raise SystemExit(main())
