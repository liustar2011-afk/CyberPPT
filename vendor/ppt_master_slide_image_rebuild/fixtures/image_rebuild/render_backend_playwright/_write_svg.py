#!/usr/bin/env python3
"""Write UTF-8 fixture SVG for render_backend_cairo smoke tests.

Note: this fixture directory is named render_backend_playwright for historical
reasons; it now tests the Cairo backend exclusively.
"""

from __future__ import annotations

from pathlib import Path

FIXTURE = Path(__file__).resolve().parent
OUT = FIXTURE / "svg_output" / "01.svg"

SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <rect x="0" y="0" width="1280" height="720" fill="#ffffff"/>
  <rect x="64" y="64" width="1152" height="592" rx="16" fill="#f3f6fb" stroke="#2563eb" stroke-width="2"/>
  <text x="96" y="160" font-family="Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif" font-size="48" fill="#1e293b">Cairo 渲染测试</text>
  <text x="96" y="240" font-family="Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif" font-size="28" fill="#475569">slide-image-rebuild preview backend smoke</text>
</svg>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(SVG.strip() + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
