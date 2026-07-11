"""Repository-local PaddleOCR adapter for CyberPPT image-to-text assets.

The main CyberPPT interpreter must not import PaddleOCR directly.  This module
normalizes output from an isolated runtime worker under tools/paddleocr_runtime.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "tools" / "paddleocr_runtime"
DEFAULT_WORKER = DEFAULT_RUNTIME_DIR / "run_ocr.py"


def run_local_ocr(
    image_path: Path,
    output_path: Path,
    *,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    model_dir: Path | None = None,
    timeout: int = 180,
) -> Path:
    """Run local OCR for one image and write vendor-compatible canonical JSON."""

    image = image_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    runtime = runtime_dir.expanduser().resolve()
    raw = _invoke_runtime(image_path=image, runtime_dir=runtime, model_dir=model_dir, timeout=timeout)
    payload = _to_canonical(raw, image, runtime)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _invoke_runtime(
    *,
    image_path: Path,
    runtime_dir: Path,
    model_dir: Path | None,
    timeout: int,
) -> dict[str, Any]:
    python = runtime_dir / ".venv" / "bin" / "python"
    if not python.is_file():
        raise RuntimeError(f"local PaddleOCR runtime is missing: {python}")
    worker = runtime_dir / "run_ocr.py"
    if not worker.is_file():
        worker = DEFAULT_WORKER
    command = [str(python), str(worker), "--image", str(image_path)]
    if model_dir is not None:
        command.extend(["--model-dir", str(model_dir.expanduser().resolve())])
    completed = subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "local PaddleOCR failed"
        raise RuntimeError(message)
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("local PaddleOCR worker must return a JSON object")
    return payload


def _to_canonical(raw: dict[str, Any], image_path: Path, runtime_dir: Path) -> dict[str, Any]:
    with Image.open(image_path) as image:
        width, height = image.size

    texts = _sequence(raw, "rec_texts", "texts")
    scores = _sequence(raw, "rec_scores", "scores")
    boxes = _sequence(raw, "rec_boxes", "boxes")
    polygons = _sequence(raw, "dt_polys", "polys", "polygons")
    styles = _sequence(raw, "styles")

    lines: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        if text is None or str(text) == "":
            continue
        polygon = _polygon_at(polygons, boxes, index)
        bbox = _bbox_from_polygon_or_box(polygon, _value_at(boxes, index))
        if bbox is None:
            continue
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            continue
        x = max(0, min(x, width))
        y = max(0, min(y, height))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))
        line_text = str(text)
        style = _style_for_line(_value_at(styles, index), line_text, h)
        line = {
            "text": line_text,
            "bbox": [round(x), round(y), round(w), round(h)],
            "score": float(_value_at(scores, index, 1.0)),
            "runs": [style],
        }
        if polygon:
            line["polygon"] = [[round(px), round(py)] for px, py in polygon]
        lines.append(line)

    lines.sort(key=lambda line: (line["bbox"][1] + line["bbox"][3] / 2, line["bbox"][0]))
    return {
        "canonical": {
            "metadata": {
                "backend": "paddleocr-local",
                "image_path": str(image_path),
                "image_size": {"width": width, "height": height},
                "runtime_dir": str(runtime_dir),
            },
            "lines": lines,
        }
    }


def _sequence(raw: dict[str, Any], *keys: str) -> list[Any]:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, list):
            return value
    return []


def _value_at(values: list[Any], index: int, default: Any = None) -> Any:
    return values[index] if index < len(values) else default


def _polygon_at(polygons: list[Any], boxes: list[Any], index: int) -> list[tuple[float, float]]:
    value = _value_at(polygons, index)
    if isinstance(value, list) and len(value) >= 4:
        try:
            return [(float(point[0]), float(point[1])) for point in value[:4]]
        except (TypeError, ValueError, IndexError):
            pass
    box = _value_at(boxes, index)
    if isinstance(box, list) and len(box) == 4:
        try:
            x1, y1, x2, y2 = (float(item) for item in box)
            return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        except (TypeError, ValueError):
            return []
    return []


def _bbox_from_polygon_or_box(
    polygon: list[tuple[float, float]],
    box: Any,
) -> tuple[float, float, float, float] | None:
    if polygon:
        xs = [point[0] for point in polygon]
        ys = [point[1] for point in polygon]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    if isinstance(box, list) and len(box) == 4:
        try:
            x1, y1, x2, y2 = (float(item) for item in box)
            return x1, y1, x2 - x1, y2 - y1
        except (TypeError, ValueError):
            return None
    return None


def _style_for_line(value: Any, text: str, height: float) -> dict[str, Any]:
    style = dict(value) if isinstance(value, dict) else {}
    return {
        "text": text,
        "font_size": float(style.get("font_size", max(6.0, height * 0.75))),
        "bold": bool(style.get("bold", False)),
        **({"color": str(style["color"]).removeprefix("#").upper()} if style.get("color") else {}),
    }
