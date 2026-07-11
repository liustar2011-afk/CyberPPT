#!/usr/bin/env python3
"""Resolve a page canvas from its script, falling back to 1920×1080."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    source: str


def resolve(script: str) -> Canvas:
    pixels = re.search(r"(?<!\d)(\d{3,5})\s*[×xX]\s*(\d{3,5})(?!\d)", script)
    if pixels:
        return Canvas(int(pixels.group(1)), int(pixels.group(2)), "script_pixels")
    ratio = re.search(r"(?<!\d)(\d{1,2})\s*[:：]\s*(\d{1,2})(?!\d)", script)
    if ratio:
        x, y = int(ratio.group(1)), int(ratio.group(2))
        width = 1920
        return Canvas(width, round(width * y / x), "script_ratio")
    return Canvas(1920, 1080, "global_default")


if __name__ == "__main__":
    script = Path(sys.argv[1]).read_text(encoding="utf-8") if len(sys.argv) > 1 else ""
    print(json.dumps(asdict(resolve(script)), ensure_ascii=False))
