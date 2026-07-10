#!/usr/bin/env python3
"""
PPT Master - Visual Diff Report Generator

Build side-by-side, heatmap, overlay PNGs and a markdown failure summary from
reference/preview images and object_similarity_report.json.

Usage:
    python3 scripts/generate_visual_diff_report.py <project_path> --write-report
    python3 scripts/generate_visual_diff_report.py <project_path> --write-report --render

Examples:
    python3 scripts/generate_visual_diff_report.py projects/demo --write-report

Dependencies:
    Pillow; render_preview_backend when --render refreshes preview PNGs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageStat
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow is required. Install project requirements first.") from exc

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from reference_object_similarity_lib import (  # noqa: E402
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    load_json,
    verify_project as verify_object_similarity,
)


def _find_pair(project: Path) -> tuple[Path | None, Path | None]:
    object_report = load_json(project / "exports" / "qa" / "object_similarity_report.json")
    pages = object_report.get("pages", [])
    if isinstance(pages, list) and pages:
        page = pages[0]
        if isinstance(page, dict):
            reference = Path(page.get("reference", ""))
            preview = Path(page.get("preview", ""))
            if reference.is_file() and preview.is_file():
                return reference, preview
    preview_dir = project / "exports" / "preview_qa"
    previews = sorted(preview_dir.glob("*.preview.png")) if preview_dir.is_dir() else []
    reference = None
    for pattern in (
        project / "images" / "reference_layout.png",
        project / "images" / "reference_pages" / "P01.png",
    ):
        if pattern.is_file():
            reference = pattern
            break
    if reference and previews:
        return reference, previews[0]
    return None, None


def _resize_rgb(path: Path, size: tuple[int, int]) -> Image.Image:
    return Image.open(path).convert("RGB").resize(size, Image.Resampling.LANCZOS)


def _write_images(reference: Path, preview: Path, qa_dir: Path) -> dict[str, str]:
    size = (DEFAULT_WIDTH, DEFAULT_HEIGHT)
    ref_img = _resize_rgb(reference, size)
    out_img = _resize_rgb(preview, size)
    diff = ImageChops.difference(ref_img, out_img)
    heatmap = ImageEnhance.Contrast(diff).enhance(4.0)
    overlay = Image.blend(out_img, heatmap, alpha=0.45)
    side_by_side = Image.new("RGB", (size[0] * 2, size[1]))
    side_by_side.paste(ref_img, (0, 0))
    side_by_side.paste(out_img, (size[0], 0))

    outputs = {
        "compare_side_by_side_png": qa_dir / "compare_side_by_side.png",
        "diff_heatmap_png": qa_dir / "diff_heatmap.png",
        "diff_overlay_png": qa_dir / "diff_overlay.png",
    }
    side_by_side.save(outputs["compare_side_by_side_png"])
    heatmap.save(outputs["diff_heatmap_png"])
    overlay.save(outputs["diff_overlay_png"])
    return {
        "compare_side_by_side_png": "exports/qa/compare_side_by_side.png",
        "diff_heatmap_png": "exports/qa/diff_heatmap.png",
        "diff_overlay_png": "exports/qa/diff_overlay.png",
    }


def _draw_object_overlay(preview: Path, object_report: dict[str, Any], qa_dir: Path, project: Path) -> str | None:
    pages = object_report.get("pages", [])
    if not isinstance(pages, list) or not pages:
        return None
    page = pages[0]
    if not isinstance(page, dict):
        return None
    image = _resize_rgb(preview, (DEFAULT_WIDTH, DEFAULT_HEIGHT))
    draw = ImageDraw.Draw(image)
    for failure in page.get("failures", []):
        if not isinstance(failure, dict):
            continue
        bbox = failure.get("reference_bbox_px")
        if not isinstance(bbox, list) or len(bbox) < 4:
            continue
        x, y, w, h = [int(round(float(value))) for value in bbox[:4]]
        draw.rectangle((x, y, x + w, y + h), outline=(220, 40, 40), width=3)
        draw.text((x + 4, max(0, y - 16)), str(failure.get("id", "")), fill=(220, 40, 40))
    out = qa_dir / "object_diff_overlay.png"
    image.save(out)
    return str(out.relative_to(project))


def _failure_summary_md(object_report: dict[str, Any]) -> str:
    lines = ["# 视觉差异返修报告", ""]
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for page in object_report.get("pages", []):
        if not isinstance(page, dict):
            continue
        for failure in page.get("failures", []):
            if isinstance(failure, dict):
                blocking.append(failure)
        for warning in page.get("warnings", []):
            if isinstance(warning, dict):
                warnings.append(warning)

    lines.extend(["## 一、阻断项", ""])
    if blocking:
        lines.extend(["| 对象 | 问题 | 建议动作 |", "|---|---|---|"])
        for item in blocking:
            lines.append(
                f"| {item.get('id', '')} | {item.get('issue_code', item.get('issue', ''))} | {item.get('action', '')} |"
            )
    else:
        lines.append("无阻断项。")

    lines.extend(["", "## 二、非阻断项", ""])
    if warnings:
        lines.extend(["| 对象 | 问题 | 建议动作 |", "|---|---|---|"])
        for item in warnings:
            lines.append(
                f"| {item.get('id', '')} | {item.get('issue_code', item.get('issue', ''))} | {item.get('action', '')} |"
            )
    else:
        lines.append("无非阻断项。")
    lines.append("")
    return "\n".join(lines)


def generate_report(
    project: Path,
    *,
    render: bool = False,
    render_backend: str = "cairo",
    hard_gate: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    qa_dir = project / "exports" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    object_report = verify_object_similarity(
        project,
        render=render,
        render_backend=render_backend,
        hard_gate=hard_gate,
        write_report=True,
    )
    reference, preview = _find_pair(project)
    artifacts: dict[str, str | None] = {
        "object_similarity_report": object_report.get("report_path", "exports/qa/object_similarity_report.json"),
        "failure_summary_md": None,
        "compare_side_by_side_png": None,
        "diff_heatmap_png": None,
        "diff_overlay_png": None,
        "object_diff_overlay_png": None,
    }
    mean_diff = None
    if reference and preview:
        ref_img = _resize_rgb(reference, (DEFAULT_WIDTH, DEFAULT_HEIGHT))
        out_img = _resize_rgb(preview, (DEFAULT_WIDTH, DEFAULT_HEIGHT))
        mean_diff = round(float(ImageStat.Stat(ImageChops.difference(ref_img, out_img)).mean[0]), 2)
        image_paths = _write_images(reference, preview, qa_dir)
        artifacts.update({
            "compare_side_by_side_png": f"exports/qa/compare_side_by_side.png",
            "diff_heatmap_png": f"exports/qa/diff_heatmap.png",
            "diff_overlay_png": f"exports/qa/diff_overlay.png",
        })
        overlay = _draw_object_overlay(preview, object_report, qa_dir, project)
        artifacts["object_diff_overlay_png"] = overlay

    summary_md = _failure_summary_md(object_report)
    summary_path = qa_dir / "failure_summary.md"
    if write_report:
        summary_path.write_text(summary_md, encoding="utf-8")
        artifacts["failure_summary_md"] = str(summary_path.relative_to(project))

    payload = {
        "workflow": "slide-image-rebuild",
        "check": "visual_diff_report",
        "project": str(project),
        "valid": object_report.get("valid", False),
        "mean_diff": mean_diff,
        "artifacts": artifacts,
        "object_similarity": {
            "valid": object_report.get("valid", False),
            "objects_checked": object_report.get("summary", {}).get("objects_checked", 0),
            "objects_failed": object_report.get("summary", {}).get("objects_failed", 0),
        },
    }
    report_path = qa_dir / "visual_diff_report.json"
    if write_report:
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["report_path"] = str(report_path.relative_to(project))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate visual diff artifacts for slide-image rebuild QA.")
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument("--render", action="store_true", help="Refresh preview PNG before generating diff artifacts")
    parser.add_argument(
        "--render-backend",
        choices=["cairo", "none"],
        default="cairo",
        help="Preview render backend when --render (default: cairo)",
    )
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="Pass hard_gate to preview render backend",
    )
    parser.add_argument("--write-report", action="store_true", help="Write exports/qa/failure_summary.md and visual_diff_report.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Project not found: {project}"]}, ensure_ascii=False, indent=2))
        return 1
    payload = generate_report(
        project,
        render=args.render,
        render_backend=args.render_backend,
        hard_gate=args.hard_gate,
        write_report=args.write_report,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
