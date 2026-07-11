"""Single-image, high-fidelity text information extraction facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .controlled_correction import correct_lines
from .paddleocr_local import run_local_ocr
from .text_forensics import build_line_evidence, summarize_style_evidence


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_DIR = REPO_ROOT / "tools" / "paddleocr_runtime"
CORRECTION_POLICY = REPO_ROOT / "config" / "ocr" / "correction_policy.json"
PROTECTED_TERMS = REPO_ROOT / "config" / "ocr" / "protected_terms.json"


def _normalize_local_layout(layout: dict[str, Any]) -> dict[str, Any]:
    size = layout.get("image_size")
    if not isinstance(size, dict) or float(size.get("width", 0)) <= 0 or float(size.get("height", 0)) <= 0:
        raise ValueError("local OCR layout must contain positive image_size")
    items = layout.get("items", [])
    if not isinstance(items, list):
        raise ValueError("local OCR layout items must be a list")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            raise ValueError("local OCR item bbox must contain four numbers")
        values = [float(value) for value in bbox]
        if values[2] <= values[0] or values[3] <= values[1]:
            raise ValueError("local OCR item bbox must satisfy x2>x1 and y2>y1")
        observed = dict(item)
        observed["text"] = str(item["text"]).strip()
        observed["bbox"] = values
        observed["confidence"] = float(item.get("confidence", 1.0))
        normalized.append(observed)
    return {"image_size": {"width": int(float(size["width"])), "height": int(float(size["height"]))}, "items": normalized, "backend": "paddleocr-local"}


def extract_text_info(
    image_path: Path,
    *,
    backend: str = "paddleocr-local",
    runtime_dir: Path | None = None,
    scale: float = 1.0,
    correction: bool = True,
) -> dict[str, Any]:
    """Extract ordered text and bounded visual evidence from exactly one image.

    The facade intentionally has no page, script, manifest, or expected-lines
    parameters.  The local backend calls PaddleOCR directly, so it cannot
    accidentally fall through to remote Vision OCR.
    """
    image_path = Path(image_path).resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if backend != "paddleocr-local":
        raise ValueError("high-fidelity text extraction currently supports only paddleocr-local")
    if scale <= 0:
        raise ValueError("scale must be positive")

    runtime = Path(runtime_dir).resolve() if runtime_dir is not None else DEFAULT_RUNTIME_DIR
    layout = _normalize_local_layout(run_local_ocr(image_path, runtime_dir=runtime, scale=scale))
    evidence_dir = image_path.parent / f".{image_path.stem}.text-evidence"
    result = build_line_evidence(layout, image_path, evidence_dir=evidence_dir)
    if correction:
        result["lines"] = correct_lines(
            list(result.get("lines", [])),
            policy_path=CORRECTION_POLICY,
            protected_terms_path=PROTECTED_TERMS,
            require_candidate_context=True,
        )
    result["quality"] = {
        **dict(result.get("quality") or {}),
        "style_evidence": summarize_style_evidence(list(result.get("lines", []))),
    }
    return {
        "image": result["image"],
        "lines": result["lines"],
        "quality": result["quality"],
        "artifacts": result["artifacts"],
        "provenance": {
            "backend": backend,
            "runtime_dir": str(runtime),
            "scale": scale,
            "correction": correction,
            "remote_vision": False,
        },
    }
