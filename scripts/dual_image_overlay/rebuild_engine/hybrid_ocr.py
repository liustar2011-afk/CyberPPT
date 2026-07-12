"""Combine PaddleOCR text accuracy with macOS Vision line geometry."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VISION_SCRIPT = REPO_ROOT / "vendor/three-image-to-ppt/scripts/vision_ocr.swift"


def run_vision_ocr(
    image_path: Path,
    *,
    script_path: Path | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Run the repository macOS Vision script and validate canonical output."""

    image = image_path.expanduser().resolve()
    script = (script_path or DEFAULT_VISION_SCRIPT).expanduser().resolve()
    completed = subprocess.run(
        ["swift", str(script), str(image)],
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "macOS Vision OCR failed"
        raise RuntimeError(message)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("macOS Vision OCR returned invalid JSON") from error
    canonical = payload.get("canonical") if isinstance(payload, dict) else None
    if not isinstance(canonical, dict) or not isinstance(canonical.get("lines"), list):
        raise RuntimeError("macOS Vision OCR must return canonical.lines")
    return payload


def _normalized(text: object) -> str:
    return re.sub(r"\s+", "", str(text or "")).casefold()


def _box(line: dict[str, Any]) -> tuple[float, float, float, float] | None:
    raw = line.get("bbox")
    if not isinstance(raw, list) or len(raw) != 4:
        return None
    try:
        x, y, width, height = (float(value) for value in raw)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return x, y, width, height


def _clipped(line: dict[str, Any], size: tuple[int, int]) -> dict[str, Any] | None:
    box = _box(line)
    if box is None:
        return None
    x, y, width, height = box
    canvas_width, canvas_height = size
    left, top = max(0.0, x), max(0.0, y)
    right, bottom = min(float(canvas_width), x + width), min(float(canvas_height), y + height)
    if right <= left or bottom <= top:
        return None
    result = dict(line)
    result["bbox"] = [round(left), round(top), round(right - left), round(bottom - top)]
    return result


def _intersection_ratio(first: dict[str, Any], second: dict[str, Any]) -> float:
    left_box, right_box = _box(first), _box(second)
    if left_box is None or right_box is None:
        return 0.0
    ax, ay, aw, ah = left_box
    bx, by, bw, bh = right_box
    overlap_x = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    overlap_y = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    intersection = overlap_x * overlap_y
    return intersection / min(aw * ah, bw * bh) if intersection else 0.0


def _candidate_score(first: dict[str, Any], second: dict[str, Any]) -> float:
    first_box, second_box = _box(first), _box(second)
    if first_box is None or second_box is None:
        return 0.0
    first_area = first_box[2] * first_box[3]
    second_area = second_box[2] * second_box[3]
    if max(first_area, second_area) / min(first_area, second_area) > 5.0:
        return 0.0
    return _intersection_ratio(first, second)


def _evidence(
    paddle: dict[str, Any],
    vision: list[dict[str, Any]],
    match_type: str,
    score: float,
    requires_review: bool,
) -> dict[str, Any]:
    return {
        "match_type": match_type,
        "match_score": round(score, 4),
        "requires_review": requires_review,
        "paddle": {"text": paddle.get("text", ""), "bbox": paddle.get("bbox"), "score": paddle.get("score")},
        "vision": [
            {"text": line.get("text", ""), "bbox": line.get("bbox"), "score": line.get("score")}
            for line in vision
        ],
    }


def _split_text(paddle_text: str, vision: list[dict[str, Any]]) -> list[str] | None:
    parts = [str(line.get("text") or "") for line in vision]
    if not all(parts) or "".join(_normalized(part) for part in parts) != _normalized(paddle_text):
        return None
    return parts


def merge_hybrid_ocr(
    paddle: dict[str, Any],
    vision: dict[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Return canonical OCR with Paddle text and safe Vision geometry matches."""

    paddle_lines = list(paddle.get("canonical", {}).get("lines", []))
    vision_lines = [
        clipped
        for line in vision.get("canonical", {}).get("lines", [])
        if isinstance(line, dict) and (clipped := _clipped(line, image_size)) is not None
    ]
    merged: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for source_index, paddle_line in enumerate(paddle_lines):
        candidates = [
            line for line in vision_lines if _candidate_score(paddle_line, line) >= 0.25
        ]
        candidates.sort(key=lambda line: (_box(line)[0], _box(line)[1]))
        scores = [_candidate_score(paddle_line, line) for line in candidates]
        if len(candidates) == 1:
            line = dict(paddle_line)
            line["bbox"] = candidates[0]["bbox"]
            line["hybrid_evidence"] = _evidence(
                paddle_line, candidates, "one_to_one", scores[0], False
            )
            merged.append(line)
            continue
        split = _split_text(str(paddle_line.get("text") or ""), candidates) if len(candidates) > 1 else None
        if split is not None:
            for text, candidate, score in zip(split, candidates, scores):
                line = dict(paddle_line)
                line["text"] = text
                line["bbox"] = candidate["bbox"]
                source_runs = paddle_line.get("runs")
                if isinstance(source_runs, list) and source_runs:
                    split_run = dict(source_runs[0]) if isinstance(source_runs[0], dict) else {}
                    split_run["text"] = text
                    line["runs"] = [split_run]
                line["hybrid_evidence"] = _evidence(
                    paddle_line, candidates, "one_to_many", score, False
                )
                merged.append(line)
            continue
        line = dict(paddle_line)
        rule = "hybrid_ocr_ambiguous_split" if candidates else "hybrid_ocr_unmatched"
        match_type = "ambiguous" if candidates else "paddle_fallback"
        line["hybrid_evidence"] = _evidence(
            paddle_line, candidates, match_type, max(scores, default=0.0), True
        )
        merged.append(line)
        review_items.append(
            {"rule": rule, "source_index": source_index, "text": paddle_line.get("text", "")}
        )
    return {
        "canonical": {
            "metadata": {
                "backend": "paddle-text+vision-geometry",
                "image_size": {"width": image_size[0], "height": image_size[1]},
            },
            "lines": merged,
            "review_items": review_items,
        }
    }
