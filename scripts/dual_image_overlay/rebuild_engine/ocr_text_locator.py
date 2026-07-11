#!/usr/bin/env python3
"""Locate text boxes in slide images and normalize OCR output."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from PIL import Image

from codex_oauth_image import run_codex_vision_text
from paddleocr_local import run_local_ocr


DEFAULT_TRANSIENT_RETRY_DELAYS: tuple[float, ...] = (1.0, 3.0, 9.0)
DEFAULT_QUALITY_RETRIES = 2


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
        normalized_item = {
                "text": text,
                "bbox": [x1, y1, x2, y2],
                "confidence": float(confidence) if confidence is not None else 1.0,
                "source": str(item.get("source") or data.get("backend") or "ocr"),
            }
        # Keep polygon evidence when an OCR backend provides it.  The bbox
        # remains the canonical normalized geometry used by existing callers.
        polygon = item.get("polygon")
        if isinstance(polygon, list) and polygon:
            normalized_item["polygon"] = polygon
        normalized_items.append(normalized_item)
    return {"image_size": {"width": width, "height": height}, "items": normalized_items}


def load_layout(path: Path) -> dict[str, Any]:
    return normalize_layout(json.loads(path.read_text(encoding="utf-8")))


def _call_vision_backend_once(
    image_path: Path,
    *,
    timeout: int,
    retry_delays: tuple[float, ...] = DEFAULT_TRANSIENT_RETRY_DELAYS,
) -> dict[str, Any]:
    """Call the vision OCR backend, retrying on transient network failures.

    The Codex OAuth Responses call occasionally fails with a transient network
    error (e.g. SSL EOF) that has nothing to do with the image or prompt; a
    plain retry with backoff resolves it without a human needing to notice the
    stack trace and manually re-run the whole rebuild command.
    """
    last_error: Exception | None = None
    for attempt, delay in enumerate((0.0, *retry_delays)):
        if delay:
            print(
                f"OCR vision call failed ({last_error}); retrying in {delay:.0f}s "
                f"(attempt {attempt + 1}/{len(retry_delays) + 1}).",
                file=sys.stderr,
            )
            time.sleep(delay)
        try:
            raw = run_codex_vision_text(prompt=VISION_JSON_PROMPT, image_paths=[image_path], timeout=timeout)
            return parse_json_output(raw)
        except Exception as exc:  # noqa: BLE001 - network/SSL/JSON hiccups are all transient here
            last_error = exc
    raise RuntimeError(
        f"OCR vision backend failed after {len(retry_delays) + 1} attempts: {last_error}"
    ) from last_error


def locate_text(
    image_path: Path,
    *,
    backend: str = "vision-json",
    output_path: Path | None = None,
    dry_run: bool = False,
    timeout: int = 300,
    min_expected_items: int | None = None,
    quality_retries: int = DEFAULT_QUALITY_RETRIES,
    ocr_scale: float = 1.0,
) -> dict[str, Any]:
    """Locate text in an image and optionally write the normalized JSON.

    `min_expected_items`, when given, is a rough floor for how many distinct
    text items the source content should contain (e.g. the number of known
    body lines in the page script). The vision OCR backend is not
    deterministic: the same image can come back with adjacent lines merged
    into one blob on one call and cleanly separated on the next. When the
    first attempt detects fewer items than expected, this resamples up to
    `quality_retries` more times and keeps whichever attempt found the most
    items, instead of silently accepting a likely-merged result.
    """
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if backend == "none":
        layout = {"image_size": image_size(image_path), "items": []}
    elif backend == "paddleocr-local":
        if dry_run:
            layout = {"image_size": image_size(image_path), "items": []}
        else:
            layout = normalize_layout(
                run_local_ocr(
                    image_path,
                    runtime_dir=Path(__file__).resolve().parents[3] / "tools" / "paddleocr_runtime",
                    scale=ocr_scale,
                )
            )
    elif backend in {"vision-json", "paddleocr-vl"}:
        if dry_run:
            layout = {"image_size": image_size(image_path), "items": []}
        else:
            best_layout: dict[str, Any] | None = None
            attempts_used = 0
            for attempt in range(1 + max(0, quality_retries)):
                data = _call_vision_backend_once(image_path, timeout=timeout)
                data.setdefault("backend", backend)
                candidate = normalize_layout(data)
                attempts_used += 1
                if best_layout is None or len(candidate["items"]) > len(best_layout["items"]):
                    best_layout = candidate
                if min_expected_items is None or len(candidate["items"]) >= min_expected_items:
                    break
                print(
                    f"OCR detected only {len(candidate['items'])} text item(s), "
                    f"expected at least {min_expected_items}; resampling "
                    f"({attempt + 1}/{1 + quality_retries}).",
                    file=sys.stderr,
                )
            assert best_layout is not None
            layout = best_layout
            if attempts_used > 1:
                layout["quality_retry_attempts"] = attempts_used
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
    parser.add_argument("--backend", choices=("vision-json", "paddleocr-vl", "paddleocr-local", "none"), default="vision-json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--ocr-scale", type=float, default=1.0)
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
            ocr_scale=args.ocr_scale,
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
