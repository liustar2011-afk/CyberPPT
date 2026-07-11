#!/usr/bin/env python3
"""Run a deterministic, offline legacy OCR forensic/render smoke test."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dual_image_overlay.rebuild_engine.ocr_quality_gate import evaluate_ocr_quality
from scripts.dual_image_overlay.rebuild_engine.script_text_overlay import OverlayTextBox, render_overlay_svg
from scripts.dual_image_overlay.rebuild_engine.text_forensics import attach_correction_evidence, build_line_evidence


def run(output_dir: Path) -> dict[str, str]:
    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("SVG rasterization requires cairosvg; install it before running this harness") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / "synthetic_page.png"
    Image.new("RGB", (1672, 941), "white").save(image_path)
    layout = {
        "image_size": {"width": 1672, "height": 941},
        "backend": "paddleocr-local",
        "items": [{
            "text": "经营管理",
            "bbox": [112, 237, 418, 276],
            "polygon": [[112, 237], [418, 237], [418, 276], [112, 276]],
            "confidence": 1.0,
        }],
    }
    forensics = build_line_evidence(layout, image_path, evidence_dir=output_dir / "evidence")
    forensics = attach_correction_evidence(
        forensics,
        policy_path=Path("config/ocr/correction_policy.json"),
        protected_terms_path=Path("config/ocr/protected_terms.json"),
    )
    gate = evaluate_ocr_quality(
        forensics,
        policy={"min_line_recall": 0.95, "max_low_confidence_ratio": 0.10, "max_protected_replacement_failures": 0},
    )
    if gate["status"] != "passed":
        raise RuntimeError(f"synthetic OCR quality gate failed: {gate}")
    forensics_path = output_dir / "text_forensics.json"
    forensics_path.write_text(json.dumps(forensics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    svg_path = output_dir / "legacy_rebuild.svg"
    svg_path.write_text(
        render_overlay_svg(
            background_href=image_path.name,
            canvas={"width": 1672, "height": 941},
            body_region={"x": 26, "y": 136, "width": 1619, "height": 774},
            slide_title="Synthetic legacy rebuild",
            text_boxes=[OverlayTextBox(text="经营管理", x=112, y=237, w=306, h=39, font_size=24)],
        ),
        encoding="utf-8",
    )
    png_path = output_dir / "legacy_rebuild.png"
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=1672, output_height=941)
    if not png_path.is_file() or Image.open(png_path).size != (1672, 941):
        raise RuntimeError("SVG rasterization did not produce a 1672x941 PNG")
    return {"quality": gate["status"], "forensics": str(forensics_path), "svg": str(svg_path), "png": str(png_path)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), ensure_ascii=False, indent=2))
