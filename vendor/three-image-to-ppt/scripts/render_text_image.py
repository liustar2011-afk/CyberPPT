#!/usr/bin/env python3
"""Render a pure-text OCR source image from canonical line geometry."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


FONT = "/Users/liuxing/Library/Fonts/msyh.ttc"


def main() -> None:
    ocr_path, reference_path, output_path = map(Path, sys.argv[1:4])
    with Image.open(reference_path) as reference:
        canvas = Image.new("RGBA", reference.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(canvas)
    payload = json.loads(ocr_path.read_text(encoding="utf-8"))
    for line in payload["canonical"]["lines"]:
        x, y, _, height = line["bbox"]
        size = max(9, min(24, round(height * 0.56)))
        face = ImageFont.truetype(FONT, size, index=0)
        draw.text((x, y), line["text"], font=face, fill="#101820")
    canvas.save(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("Usage: render_text_image.py OCR.json reference.png text.png")
    main()
