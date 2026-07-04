#!/usr/bin/env python3
"""Write cairo CJK tofu negative fixture assets."""

from __future__ import annotations

from pathlib import Path

FIXTURE = Path(__file__).resolve().parent
SVG_OUT = FIXTURE / "svg_output" / "01.svg"
REF_OUT = FIXTURE / "images" / "reference_layout.png"

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="1280" height="720" fill="#ffffff"/>
  <text x="96" y="180" font-family="PPTMasterMissingFont2026, serif" font-size="56" fill="#111827">中文应出现 tofu</text>
</svg>
"""


def main() -> None:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("Pillow required") from exc
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    REF_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(SVG.strip() + "\n", encoding="utf-8")
    Image.new("RGB", (1280, 720), (255, 255, 255)).save(REF_OUT)
    print(SVG_OUT)


if __name__ == "__main__":
    main()
