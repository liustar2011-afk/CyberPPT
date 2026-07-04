#!/usr/bin/env python3
"""Write L2 CJK Cairo fixture assets."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow required") from exc

FIXTURE = Path(__file__).resolve().parent
SVG_OUT = FIXTURE / "svg_output" / "01.svg"
REF_OUT = FIXTURE / "images" / "reference_layout.png"

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="1280" height="720" fill="#ffffff"/>
  <rect x="64" y="64" width="1152" height="592" rx="16" fill="#f3f6fb" stroke="#2563eb" stroke-width="2"/>
  <text x="96" y="160" font-family="Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif" font-size="48" fill="#1e293b">Playwright 中文渲染</text>
  <text x="96" y="240" font-family="Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif" font-size="28" fill="#475569">L2 CJK preview fixture</text>
</svg>
"""


def main() -> None:
    SVG_OUT.parent.mkdir(parents=True, exist_ok=True)
    REF_OUT.parent.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(SVG.strip() + "\n", encoding="utf-8")
    Image.new("RGB", (1280, 720), (255, 255, 255)).save(REF_OUT)
    print(SVG_OUT)
    print(REF_OUT)


if __name__ == "__main__":
    main()
