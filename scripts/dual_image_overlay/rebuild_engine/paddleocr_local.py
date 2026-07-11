"""Subprocess-isolated PaddleOCR adapter for the local OCR backend."""

from __future__ import annotations

import json
import math
import os
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


_RUNTIME_CODE = r'''
import json, sys
from pathlib import Path
from paddleocr import PaddleOCR

image_path, output_path, det_model_dir, rec_model_dir, scale = sys.argv[1:6]
scale = float(scale)
ocr_kwargs = dict(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
if not det_model_dir or not rec_model_dir:
    raise RuntimeError("verified local PaddleOCR detection/recognition model directories are required")
ocr_kwargs["text_detection_model_dir"] = det_model_dir
ocr_kwargs["text_recognition_model_dir"] = rec_model_dir
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
    model_dir: Path | None = None, det_model_dir: Path | None = None,
    rec_model_dir: Path | None = None, scale: float = 1.0,
) -> dict[str, Any]:
    python = runtime_dir / ".venv" / "bin" / "python"
    if not python.is_file():
        raise FileNotFoundError(f"PaddleOCR runtime interpreter not found: {python}")
    if model_dir is None:
        model_dir = runtime_dir / "models"
    if model_dir is not None:
        det_model_dir = det_model_dir or model_dir / "PP-OCRv5_mobile_det"
        rec_model_dir = rec_model_dir or model_dir / "PP-OCRv5_mobile_rec"
        det_model_dir = det_model_dir if Path(det_model_dir).is_dir() else next((model_dir / n for n in ("det", "detection") if (model_dir / n).is_dir()), det_model_dir)
        rec_model_dir = rec_model_dir if Path(rec_model_dir).is_dir() else next((model_dir / n for n in ("rec", "recognition") if (model_dir / n).is_dir()), rec_model_dir)
    if not det_model_dir or not rec_model_dir or not Path(det_model_dir).is_dir() or not Path(rec_model_dir).is_dir():
        raise RuntimeError("verified local PaddleOCR model directories are required; refusing network-backed defaults")
    manifest = runtime_dir / "runtime_manifest.json"
    if manifest.is_file():
        spec = json.loads(manifest.read_text(encoding="utf-8"))
        for name, path in (("PP-OCRv5_mobile_det", Path(det_model_dir)), ("PP-OCRv5_mobile_rec", Path(rec_model_dir))):
            entry = next((m for m in spec.get("models", []) if m.get("name") == name), {})
            expected = entry.get("directory_sha256")
            verified = False
            if expected:
                digest = hashlib.sha256()
                for child in sorted(p for p in path.rglob("*") if p.is_file()):
                    digest.update(str(child.relative_to(path)).encode()); digest.update(child.read_bytes())
                if digest.hexdigest() != expected:
                    raise RuntimeError(f"model directory hash mismatch: {name}")
                verified = True
            archive = runtime_dir / "models" / f"{name}_infer.tar"
            if archive.is_file() and entry.get("sha256"):
                digest = hashlib.sha256()
                with archive.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != entry["sha256"]:
                    raise RuntimeError(f"model archive hash mismatch: {name}")
                verified = True
            sidecar = path / ".sha256"
            if sidecar.is_file() and entry.get("sha256") and sidecar.read_text(encoding="utf-8").strip() != entry["sha256"]:
                raise RuntimeError(f"model archive hash mismatch: {name}")
            verified = verified or sidecar.is_file()
            if entry.get("sha256") and not verified:
                raise RuntimeError(f"unverified model payload: {name}")
    env = dict(os.environ)
    env.update({"PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK": "True", "PADDLEOCR_HOME": str(Path(det_model_dir).parent)})
    subprocess.run(
        [str(python), "-c", _RUNTIME_CODE, str(image_path), str(output_path),
         str(det_model_dir), str(rec_model_dir), str(scale)],
        check=True, timeout=600, env=env,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _box(value: Any) -> list[float] | None:
    def numeric(v: Any) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))
    if isinstance(value, (list, tuple)) and len(value) == 4 and all(numeric(v) for v in value):
        box = [float(v) for v in value]
        return box if box[2] > box[0] and box[3] > box[1] else None
    if isinstance(value, (list, tuple)) and len(value) >= 3 and all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in value):
        if not all(numeric(p[0]) and numeric(p[1]) for p in value):
            return None
        xs = [float(p[0]) for p in value]
        ys = [float(p[1]) for p in value]
        box = [min(xs), min(ys), max(xs), max(ys)]
        return box if box[2] > box[0] and box[3] > box[1] else None
    return None


def _polygon(value: Any, scale: float) -> list[list[float]] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    points = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return None
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) for v in point[:2]):
            return None
        points.append([float(point[0]) / scale, float(point[1]) / scale])
    return points


def run_local_ocr(
    image_path: Path, *, runtime_dir: Path, model_dir: Path | None = None, scale: float = 1.0,
) -> dict[str, Any]:
    """Run pinned local PaddleOCR and return the locator contract plus raw evidence."""
    image_path = Path(image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be a finite positive number")
    with Image.open(image_path) as image:
        width, height = image.size
    with tempfile.TemporaryDirectory(prefix="cyberppt-paddleocr-") as directory:
        runtime_image = image_path
        if scale != 1.0:
            runtime_image = Path(directory) / "scaled.png"
            with Image.open(image_path) as image:
                runtime_size = (max(1, round(width * scale)), max(1, round(height * scale)))
                image.resize(runtime_size).save(runtime_image)
        output_path = Path(directory) / "result.json"
        raw = _invoke_runtime(image_path=runtime_image, runtime_dir=Path(runtime_dir), output_path=output_path,
                              model_dir=model_dir, scale=scale)
    texts = raw.get("rec_texts") or []
    scores = raw.get("rec_scores") or []
    rec_boxes = raw.get("rec_boxes") or []
    dt_polys = raw.get("dt_polys") or []
    runtime_root = Path(runtime_dir)
    if model_dir is None:
        candidate = runtime_root / "models"
        if candidate.is_dir():
            model_dir = candidate
    items: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        text = str(text or "").strip()
        bbox = _box(rec_boxes[index] if index < len(rec_boxes) else None)
        if bbox is None:
            bbox = _box(dt_polys[index] if index < len(dt_polys) else None)
        if not text or bbox is None:
            continue
        x1, y1, x2, y2 = [coord / scale for coord in bbox]
        x1, x2 = max(0.0, min(float(width), x1)), max(0.0, min(float(width), x2))
        y1, y2 = max(0.0, min(float(height), y1)), max(0.0, min(float(height), y2))
        if x2 <= x1 or y2 <= y1:
            continue
        confidence = float(scores[index]) if index < len(scores) else 1.0
        polygon = _polygon(dt_polys[index], scale) if index < len(dt_polys) else None
        item = {"text": text, "bbox": [x1, y1, x2, y2], "confidence": confidence, "source": "paddleocr-local"}
        if polygon:
            item["polygon"] = polygon
            item["polygon_scaled"] = [[p[0] * scale, p[1] * scale] for p in polygon]
        items.append(item)
    return {
        "image_size": {"width": width, "height": height}, "items": items, "raw_items": raw,
        "backend": "paddleocr-local", "runtime": str(Path(runtime_dir).resolve()),
    }
