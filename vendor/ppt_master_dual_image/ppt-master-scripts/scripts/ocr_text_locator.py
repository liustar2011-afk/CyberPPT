#!/usr/bin/env python3
"""Locate text boxes in slide images and normalize OCR output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from codex_oauth_image import run_codex_vision_text


VISION_JSON_PROMPT = """识别这张 PPT 页面图片中的所有可读文字，并返回严格 JSON。
不要输出 Markdown，不要解释。
坐标使用输入图片像素坐标，bbox 格式为 [x1, y1, x2, y2]。
返回格式：
{
  "image_size": {"width": 图片宽度, "height": 图片高度},
  "items": [
    {"text": "文字", "bbox": [x1, y1, x2, y2], "confidence": 0.0}
  ]
}
"""


def image_size(path: Path) -> dict[str, int]:
    with Image.open(path) as image:
        return {"width": image.width, "height": image.height}


def parse_json_output(text: str) -> dict[str, Any]:
    """Parse JSON returned by a vision model, accepting fenced JSON blocks."""
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(?P<body>\{.*?\})\s*```", raw, re.S)
    if fenced:
        raw = fenced.group("body")
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw = raw[start : end + 1]
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("OCR output must be a JSON object.")
    return data


def _number(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc


def normalize_layout(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize OCR layout to the repo-local text locator contract."""
    size = data.get("image_size")
    if not isinstance(size, dict):
        raise ValueError("OCR layout missing image_size object.")
    width = int(_number(size.get("width"), field="image_size.width"))
    height = int(_number(size.get("height"), field="image_size.height"))
    if width <= 0 or height <= 0:
        raise ValueError("image_size width/height must be positive.")

    normalized_items: list[dict[str, Any]] = []
    items = data.get("items", [])
    if not isinstance(items, list):
        raise ValueError("OCR layout items must be an array.")
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{index}] must be an object.")
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"items[{index}].bbox must contain four numbers.")
        x1, y1, x2, y2 = [_number(value, field=f"items[{index}].bbox") for value in bbox]
        if x2 <= x1 or y2 <= y1:
            raise ValueError(f"items[{index}].bbox must satisfy x2>x1 and y2>y1.")
        confidence = item.get("confidence", 1.0)
        normalized_items.append(
            {
                "text": text,
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidence) if confidence is not None else 1.0,
                "source": str(item.get("source") or data.get("backend") or "ocr"),
            }
        )
    return {"image_size": {"width": width, "height": height}, "items": normalized_items}


def load_layout(path: Path) -> dict[str, Any]:
    return normalize_layout(json.loads(path.read_text(encoding="utf-8")))


def locate_text(
    image_path: Path,
    *,
    backend: str = "vision-json",
    output_path: Path | None = None,
    dry_run: bool = False,
    timeout: int = 300,
) -> dict[str, Any]:
    """Locate text in an image and optionally write the normalized JSON."""
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if backend == "none":
        layout = {"image_size": image_size(image_path), "items": []}
    elif backend in {"vision-json", "paddleocr-vl"}:
        if dry_run:
            layout = {"image_size": image_size(image_path), "items": []}
        else:
            raw = run_codex_vision_text(prompt=VISION_JSON_PROMPT, image_paths=[image_path], timeout=timeout)
            data = parse_json_output(raw)
            data.setdefault("backend", backend)
            layout = normalize_layout(data)
    else:
        raise ValueError(f"Unsupported OCR backend: {backend}")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return layout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Locate text boxes in a slide image.")
    parser.add_argument("image", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--backend", choices=("vision-json", "paddleocr-vl", "none"), default="vision-json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        layout = locate_text(
            args.image,
            backend=args.backend,
            output_path=args.out,
            dry_run=args.dry_run,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.out is None:
        print(json.dumps(layout, ensure_ascii=False, indent=2))
    else:
        print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
