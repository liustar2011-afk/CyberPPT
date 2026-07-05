from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any


TITLE_ROLE_HINTS = {
    "title",
    "ability_title",
    "section_title",
    "panel_title",
    "module_title",
    "card_title",
    "service_title",
    "governance_title",
}

BODY_ROLE_HINTS = {
    "body",
    "bullet",
    "body_text",
    "description",
    "evidence",
    "caption",
    "item",
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _bbox(box: dict[str, Any]) -> list[float]:
    raw = box.get("bbox")
    if not isinstance(raw, list) or len(raw) != 4:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        return [float(value) for value in raw]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]


def _height(box: dict[str, Any]) -> float:
    x1, y1, x2, y2 = _bbox(box)
    return max(0.0, y2 - y1)


def _role_hint(box: dict[str, Any]) -> str:
    for key in ("semantic_role", "role", "typography_role"):
        raw = box.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _semantic_weight_class(box: dict[str, Any]) -> str:
    text = _compact(str(box.get("text") or ""))
    role = _role_hint(box).lower()
    if not text:
        return "body"
    if text in {"•", "·", "-", "–"}:
        return "bullet_marker"
    if text.isdigit() and len(text) <= 2:
        return "index"
    if role in TITLE_ROLE_HINTS or any(role.endswith(f"_{hint}") for hint in TITLE_ROLE_HINTS):
        return "title"
    if role in BODY_ROLE_HINTS or any(role.endswith(f"_{hint}") for hint in BODY_ROLE_HINTS):
        return "body"

    height = _height(box)
    if height >= 13.0:
        return "title"
    return "body"


def _target_bold(weight_class: str) -> bool:
    return weight_class in {"index", "title"}


def _style_group(box: dict[str, Any]) -> str:
    role = _role_hint(box)
    if role:
        return role
    return _semantic_weight_class(box)


def apply_semantic_typography_qa(
    boxes: list[dict[str, Any]],
    *,
    report_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize bold decisions from semantic role/parallel text class.

    This deliberately treats OCR-derived or heuristic initial ``bold`` values as
    observations, not truth. The semantic class decides whether each peer text
    should be bold.
    """
    corrected = [copy.deepcopy(box) for box in boxes]
    corrections: list[dict[str, Any]] = []
    groups: dict[str, dict[str, Any]] = {}

    for index, box in enumerate(corrected):
        weight_class = _semantic_weight_class(box)
        target = _target_bold(weight_class)
        current = bool(box.get("bold", False))
        group = _style_group(box)
        groups.setdefault(
            group,
            {
                "group": group,
                "semantic_weight_class": weight_class,
                "target_bold": target,
                "items": 0,
            },
        )["items"] += 1
        if current != target:
            box["bold"] = target
            box["semantic_typography_corrected"] = True
            box["semantic_typography_reason"] = f"{weight_class}_weight_contract"
            corrections.append(
                {
                    "index": index,
                    "text": str(box.get("text") or ""),
                    "group": group,
                    "semantic_weight_class": weight_class,
                    "from_bold": current,
                    "to_bold": target,
                    "code": "semantic_parallel_bold_normalized",
                }
            )

    report = {
        "schema": "cyberppt.dual_image.semantic_typography_qa.v1",
        "valid": True,
        "checks": {
            "semantic_parallel_weight_contract_applied": True,
            "ocr_initial_bold_not_used_as_truth": True,
        },
        "groups": list(groups.values()),
        "corrections": corrections,
        "correction_count": len(corrections),
        "error_count": 0,
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return corrected, report
