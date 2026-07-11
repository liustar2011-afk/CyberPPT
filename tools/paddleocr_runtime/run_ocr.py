#!/usr/bin/env python3
"""Isolated PaddleOCR worker used by CyberPPT.

This script runs inside tools/paddleocr_runtime/.venv and prints raw OCR JSON to
stdout. The caller normalizes it into CyberPPT/vendor canonical JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--model-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    from paddleocr import PaddleOCR  # type: ignore[import-not-found]

    kwargs: dict[str, Any] = {
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }
    if args.model_dir is not None:
        det = args.model_dir / "PP-OCRv5_mobile_det"
        rec = args.model_dir / "PP-OCRv5_mobile_rec"
        if det.is_dir():
            kwargs["text_detection_model_dir"] = str(det)
        if rec.is_dir():
            kwargs["text_recognition_model_dir"] = str(rec)
    ocr = PaddleOCR(**kwargs)
    result = ocr.predict(str(args.image))
    payload = _flatten_result(result)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def _flatten_result(result: Any) -> dict[str, Any]:
    if isinstance(result, list) and result:
        first = result[0]
        if hasattr(first, "json"):
            value = first.json
            if isinstance(value, dict):
                return value.get("res", value)
        if isinstance(first, dict):
            return first.get("res", first)
    if isinstance(result, dict):
        return result.get("res", result)
    return {"raw_result": str(result), "rec_texts": [], "rec_scores": [], "rec_boxes": []}


if __name__ == "__main__":
    raise SystemExit(main())
