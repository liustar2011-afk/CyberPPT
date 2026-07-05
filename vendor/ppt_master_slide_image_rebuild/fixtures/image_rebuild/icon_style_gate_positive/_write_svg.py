#!/usr/bin/env python3
from pathlib import Path

OUT = Path(__file__).resolve().parent / "svg_output"
OUT.mkdir(parents=True, exist_ok=True)
svg = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <g data-icon-id="icon_a" data-icon-bbox="100 100 28 28">
    <circle cx="114" cy="114" r="10" fill="none" stroke="#003C8F" stroke-width="2"/>
  </g>
  <g data-icon-id="icon_b" data-icon-bbox="200 100 28 28">
    <rect x="206" y="106" width="16" height="16" fill="none" stroke="#003C8F" stroke-width="2"/>
  </g>
</svg>
"""
(OUT / "01.svg").write_text(svg, encoding="utf-8")
