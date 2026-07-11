"""Subprocess-isolated PaddleOCR adapter for the local OCR backend."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


_RUNTIME_CODE = r'''
import json, sys
from pathlib import Path
from paddleocr import PaddleOCR

image_path, output_path, model_dir, scale = sys.argv[1:5]
scale = float(scale)
ocr_kwargs = dict(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
if model_dir:
    ocr_kwargs["text_detection_model_dir"] = model_dir
    ocr_kwargs["text_recognition_model_dir"] = model_dir
ocr = PaddleOCR(**ocr_kwargs)
results = ocr.predict(image_path)
result = next(iter(results), {})
def value(name):
    if isinstance(result, dict):
        value = result.get(name, [])
    else:
        value = getattr(result, name, [])
    return value.tolist() if hasattr(value, "tolist") else value
payload = {name: value(name) for name in ("rec_texts", "rec_scores", "rec_boxes", "dt_polys")}
Path(output_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
'''


def _invoke_runtime(
    *, image_path: Path, runtime_dir: Path, output_path: Path,
    model_dir: Path | None = None, scale: float = 1.0,
) -> dict[str, Any]:
    python = runtime_dir / ".venv" / "bin" / "python"
    if not python.is_file():
        raise FileNotFoundError(f"PaddleOCR runtime interpreter not found: {python}")
    subprocess.run(
        [str(python), "-c", _RUNTIME_CODE, str(image_path), str(output_path),
         str(model_dir) if model_dir else "", str(scale)],
        check=True, timeout=600,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _box(value: Any) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 4 and all(isinstance(v, (int, float)) for v in value):
        return [float(v) for v in value]
    if isinstance(value, (list, tuple)) and value and all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in value):
        xs = [float(p[0]) for p in value]
        ys = [float(p[1]) for p in value]
        return [min(xs), min(ys), max(xs), max(ys)]
    return None


def run_local_ocr(
    image_path: Path, *, runtime_dir: Path, model_dir: Path | None = None, scale: float = 1.0,
) -> dict[str, Any]:
    """Run pinned local PaddleOCR and return the locator contract plus raw evidence."""
    image_path = Path(image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if scale <= 0:
        raise ValueError("scale must be positive")
    with Image.open(image_path) as image:
        width, height = image.size
    with tempfile.TemporaryDirectory(prefix="cyberppt-paddleocr-") as directory:
        output_path = Path(directory) / "result.json"
        raw = _invoke_runtime(image_path=image_path, runtime_dir=Path(runtime_dir), output_path=output_path,
                              model_dir=model_dir, scale=scale)
    texts = raw.get("rec_texts") or []
    scores = raw.get("rec_scores") or []
    boxes = raw.get("rec_boxes") or raw.get("dt_polys") or []
    items: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        text = str(text or "").strip()
        bbox = _box(boxes[index] if index < len(boxes) else None)
        if not text or bbox is None:
            continue
        x1, y1, x2, y2 = [coord / scale for coord in bbox]
        x1, x2 = max(0.0, min(float(width), x1)), max(0.0, min(float(width), x2))
        y1, y2 = max(0.0, min(float(height), y1)), max(0.0, min(float(height), y2))
        if x2 <= x1 or y2 <= y1:
            continue
        confidence = float(scores[index]) if index < len(scores) else 1.0
        items.append({"text": text, "bbox": [x1, y1, x2, y2], "confidence": confidence, "source": "paddleocr-local"})
    return {
        "image_size": {"width": width, "height": height}, "items": items, "raw_items": raw,
        "backend": "paddleocr-local", "runtime": str(Path(runtime_dir).resolve()),
    }
