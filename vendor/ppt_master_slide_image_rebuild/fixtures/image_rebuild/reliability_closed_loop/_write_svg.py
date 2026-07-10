#!/usr/bin/env python3
"""UTF-8 fixture writer — copies checked-in svg_output/01.svg (regenerate from projects fixture source)."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "svg_output" / "01.svg"
DST = ROOT / "svg_output" / "01.svg"


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"missing fixture SVG: {SRC}")
    DST.parent.mkdir(parents=True, exist_ok=True)
    if SRC.resolve() != DST.resolve():
        shutil.copy2(SRC, DST)
    print(f"Wrote {DST}")


if __name__ == "__main__":
    main()
