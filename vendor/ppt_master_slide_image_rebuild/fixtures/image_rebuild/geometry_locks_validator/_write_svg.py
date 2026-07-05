#!/usr/bin/env python3
from pathlib import Path

OUT = Path(__file__).resolve().parent / "svg_output"
OUT.mkdir(parents=True, exist_ok=True)
svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <line data-geometry-lock-id="lock_title_rule" x1="72" y1="119" x2="1208" y2="119"
        stroke="#C00000" stroke-width="2"/>
</svg>
"""
(OUT / "01.svg").write_text(svg, encoding="utf-8")
