#!/usr/bin/env python3
"""Run the V1 three-image review/batch page pipeline."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_page_json import build_page_spec, write_page_spec
from scripts.map_text_coordinates import AffineTransform, map_lines
from scripts.normalize_ocr import normalize_ocr
from scripts.qa_text_style import compare_page_text_styles
from scripts.recover_text_styles import recover_page_styles
from scripts.validate_inputs import validate_images

DEFAULT_PRESENTATION_TOOLS = Path(
    "/root/.codex/skills/builtins/presentations/container_tools"
)


def _presentation_tool(name: str) -> Path:
    """Resolve presentation QA tools, allowing local Codex runtime overrides."""
    directory = Path(
        os.environ.get("THREE_IMAGE_TO_PPT_PRESENTATIONS_TOOLS", DEFAULT_PRESENTATION_TOOLS)
    )
    return directory / name


def _presentations_python() -> str:
    """Use a dedicated interpreter for rendering tools when their deps differ."""
    return os.environ.get("THREE_IMAGE_TO_PPT_PRESENTATIONS_PYTHON", sys.executable)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("review", "batch"), required=True)
    for name in ("full", "background", "ocr", "registration"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--text", type=Path)
    parser.add_argument("--input-mode", choices=("two-image", "three-image"), default="two-image")
    parser.add_argument("--manifest", type=Path, help="Batch manifest: {pages:[{full,background,ocr,registration,output_dir,page_id,input_mode,text?}]}")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--page-id", default="page")
    return parser.parse_args()


def _write_qa(output_dir: Path, qa: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _registration(path: Path) -> tuple[AffineTransform, dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matrix = payload["matrix"]
    if len(matrix) < 2 or any(len(row) < 3 for row in matrix[:2]):
        raise ValueError("registration matrix must contain two rows of three values")
    transform = AffineTransform(
        a=matrix[0][0], b=matrix[0][1], c=matrix[0][2],
        d=matrix[1][0], e=matrix[1][1], f=matrix[1][2],
        transform_id=payload["transform_id"],
    )
    corrections = payload.get("line_corrections", {})
    if not isinstance(corrections, dict):
        raise ValueError("line_corrections must be a map keyed by line_id")
    return transform, corrections


def _ocr_payload(path: Path) -> tuple[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for provider in ("canonical", "paddleocr-vl", "baidu"):
        if provider in payload:
            return provider, payload[provider]
    return "canonical", payload


def _qa_for_lines(
    lines: list[Any], mapped: list[Any] | None = None,
    page_width: int | None = None, page_height: int | None = None,
) -> dict[str, Any]:
    review_items = [
        {
            "rule": "ocr_line_confidence",
            "line_id": line.line_id,
            "value": line.confidence,
            "message": "OCR confidence is below the 0.95 pass threshold",
        }
        for line in lines
        if 0.80 <= line.confidence < 0.95
    ]
    failed_items = [
        {
            "rule": "ocr_line_confidence",
            "line_id": line.line_id,
            "value": line.confidence,
            "message": "OCR confidence is below the 0.80 failure threshold",
        }
        for line in lines
        if line.confidence < 0.80
    ]
    for item in mapped or []:
        if item.within_safe_area:
            continue
        box = item.mapped_bbox
        valid = box.width > 0 and box.height > 0
        on_slide = (
            valid and page_width is not None and page_height is not None
            and box.x >= 0 and box.y >= 0
            and box.x + box.width <= page_width
            and box.y + box.height <= page_height
        )
        finding = {
            "rule": "inside_safe_area", "line_id": item.line.line_id,
            "value": False,
            "message": "mapped line is outside the approved safe area",
        }
        (review_items if on_slide else failed_items).append(finding)
    status = "failed" if failed_items else "review" if review_items else "passed"
    return {
        "status": status,
        "review_items": review_items,
        "failed_items": failed_items,
        "checks": {"visual_line_count": len(lines), "newline_count": 0},
    }


def run(args: argparse.Namespace) -> int:
    required = ("full", "background", "ocr", "registration", "output_dir")
    missing = [name for name in required if getattr(args, name, None) is None]
    if missing:
        raise ValueError(f"missing required inputs: {', '.join(missing)}")
    if getattr(args, "input_mode", "two-image") == "three-image" and args.text is None:
        raise ValueError("three-image mode requires --text")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _remove_stale_outputs(args.output_dir)
    try:
        three_image_mode = getattr(args, "input_mode", "two-image") == "three-image"
        ocr_image = args.text if three_image_mode else args.full
        validation = validate_images(args.full, args.background, ocr_image)
        if not validation.valid:
            qa = {
                "status": "failed",
                "review_items": [],
                "failed_items": [
                    {"rule": "input_validation", "message": message}
                    for message in validation.errors
                ],
            }
            _write_qa(args.output_dir, qa)
            return 1

        provider, ocr_payload = _ocr_payload(args.ocr)
        lines = normalize_ocr(
            ocr_payload, provider, validation.width_px, validation.height_px
        )
        if not lines:
            _write_qa(
                args.output_dir,
                {
                    "status": "failed",
                    "review_items": [],
                    "failed_items": [
                        {
                            "rule": "ocr_line_count",
                            "value": 0,
                            "message": "OCR must contain at least one visual line",
                        }
                    ],
                },
            )
            return 1
        transform, line_corrections = _registration(args.registration)
        correction_errors = _validate_font_corrections(line_corrections)
        if correction_errors:
            qa = {"status": "failed", "review_items": [], "failed_items": correction_errors}
            _write_qa(args.output_dir, qa)
            return 1
        canvas_container = {
            "container_id": "canvas",
            "safe_bbox": {
                "x": 0,
                "y": 0,
                "width": validation.width_px,
                "height": validation.height_px,
            },
        }
        recovery = None
        if three_image_mode:
            recovery = recover_page_styles(
                full_path=args.full,
                background_path=args.background,
                text_path=ocr_image,
                lines=lines,
                containers=[canvas_container],
            )
            lines = list(recovery.lines)
        spec = build_page_spec(
            args.page_id,
            ({"full": args.full, "background": args.background, "text": ocr_image}
             if three_image_mode
             else {"full": args.full, "background": args.background}),
            lines,
            transform,
            [canvas_container],
            line_corrections,
        )
        if three_image_mode:
            spec = replace(spec, schema_version="1.1")
        mapped = map_lines(lines, transform, [canvas_container], line_corrections)
        qa = _qa_for_lines(lines, mapped, validation.width_px, validation.height_px)
        if recovery is not None and recovery.review_items:
            qa["review_items"].extend(dict(item) for item in recovery.review_items)
            if qa["status"] == "passed":
                qa["status"] = "review"
        if args.mode == "review":
            qa["manual_review_items"] = [
                {"checkpoint": "full_image", "status": "pending"},
                {"checkpoint": "background_geometry", "status": "pending"},
                {"checkpoint": "text_image_and_ocr", "status": "pending"},
                {"checkpoint": "ppt_render", "status": "pending"},
            ]
        spec = replace(spec, qa=qa)
        page_json = write_page_spec(spec, args.output_dir / "page.json")

        if qa["status"] == "failed":
            _remove_stale_outputs(args.output_dir)
            _write_qa(args.output_dir, qa)
            return 1

        pptx = args.output_dir / "page.pptx"
        subprocess.run(
            [
                "node", str(PROJECT_ROOT / "scripts" / "render_ppt.mjs"),
                "--json", str(page_json), "--background", str(args.background),
                "--out", str(pptx),
            ],
            check=True,
        )
        subprocess.run(
            [_presentations_python(), str(_presentation_tool("render_slides.py")), str(pptx), "--output_dir", str(args.output_dir)],
            check=True,
        )
        overflow = subprocess.run(
            [_presentations_python(), str(_presentation_tool("slides_test.py")), str(pptx)],
            text=True,
            capture_output=True,
        )
        qa["checks"]["overflow_check"] = {
            "passed": overflow.returncode == 0,
            "output": (overflow.stdout + overflow.stderr).strip(),
        }
        if overflow.returncode != 0:
            qa["status"] = "failed"
            qa["failed_items"].append(
                {"rule": "ppt_overflow", "message": "slides_test.py reported overflow"}
            )
        if three_image_mode:
            style_qa = compare_page_text_styles(
                args.output_dir / "slide-1.png",
                args.full,
                args.background,
                page_json,
                args.output_dir / "text_style_qa.json",
                overflow=overflow.returncode != 0,
            )
            qa["checks"]["text_style_qa"] = {
                "status": style_qa["status"],
                "report": "text_style_qa.json",
                "line_count": style_qa["checks"]["line_count"],
            }
            for line in style_qa["lines"]:
                if line["status"] == "passed":
                    continue
                finding = {
                    "rule": "editable_text_visual_match",
                    "line_id": line["line_id"],
                    "value": {
                        "mask_iou": line["mask_iou"],
                        "color_distance_rgb": line["color_distance_rgb"],
                        "contrast_ratio": line["contrast_ratio"],
                    },
                    "message": "editable text differs from FULL/BACKGROUND evidence",
                }
                target = qa["failed_items"] if line["status"] == "failed" else qa["review_items"]
                target.append(finding)
            if style_qa["status"] == "failed":
                qa["status"] = "failed"
            elif style_qa["status"] == "review" and qa["status"] == "passed":
                qa["status"] = "review"
        if qa["status"] == "failed":
            _remove_stale_outputs(args.output_dir)
        else:
            write_page_spec(replace(spec, qa=qa), page_json)
        _write_qa(args.output_dir, qa)
        return 0 if qa["status"] != "failed" else 1
    except Exception as error:
        _remove_stale_outputs(args.output_dir)
        _write_qa(
            args.output_dir,
            {
                "status": "failed",
                "review_items": [],
                "failed_items": [{"rule": "pipeline", "message": str(error)}],
            },
        )
        print(error, file=sys.stderr)
        return 1


def _validate_font_corrections(corrections: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    failures = []
    for line_id, correction in corrections.items():
        scale = correction.get("font_scale", 1.0)
        if not isinstance(scale, (int, float)) or abs(scale - 1.0) > 0.0300001:
            failures.append({
                "rule": "font_correction_limit", "line_id": line_id, "value": scale,
                "message": "font correction exceeds the 3% single-step limit",
            })
        cumulative = correction.get("cumulative_font_scale", scale)
        if isinstance(cumulative, (int, float)) and abs(cumulative - 1.0) > 0.0800001:
            failures.append({
                "rule": "font_correction_limit", "line_id": line_id, "value": cumulative,
                "message": "font correction exceeds the 8% cumulative limit",
            })
    return failures


def _remove_stale_outputs(output_dir: Path) -> None:
    for name in ("page.json", "page.pptx", "slide-1.png"):
        (output_dir / name).unlink(missing_ok=True)
    for path in output_dir.glob("rendered*.png"):
        if path.is_file():
            path.unlink()


if __name__ == "__main__":
    args = parse_args()
    if args.manifest:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        results = []
        for page in payload["pages"]:
            page_args = argparse.Namespace(**{
                "mode": "batch", "input_mode": payload.get("input_mode", "two-image"),
                "text": None, **{key: Path(value) if key in {"full", "background", "text", "ocr", "registration", "output_dir"} and value else value for key, value in page.items()},
            })
            results.append({"page_id": page_args.page_id, "exit_code": run(page_args)})
        print(json.dumps({"pages": results}, ensure_ascii=False))
        raise SystemExit(0 if all(item["exit_code"] == 0 for item in results) else 1)
    raise SystemExit(run(args))
