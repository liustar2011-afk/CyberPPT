from __future__ import annotations

import json
from pathlib import Path


def scan_background_text(layout_path: Path) -> dict:
    payload = json.loads(layout_path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        items = []
    text_items = [
        item for item in items if isinstance(item, dict) and str(item.get("text") or "").strip()
    ]
    issues = [
        {
            "severity": "error",
            "code": "background_contains_text",
            "text": str(item.get("text") or ""),
            "bbox": item.get("bbox"),
        }
        for item in text_items
    ]
    return {
        "schema": "cyberppt.dual_image.background_text_scan.v1",
        "valid": not issues,
        "policy": "no readable primary text may remain in the no-text background",
        "checked_layout": str(layout_path),
        "issues": issues,
        "error_count": len(issues),
    }
