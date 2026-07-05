from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.dual_image_overlay"


from .background_text_scan import scan_background_text
from .alignment import AlignmentTransform, estimate_alignment
from .container_workspace import build_container_workspace, write_container_workspace
from .layout_qa import check_layout
from .normalize import normalize_image
from .office_textbox_fit import apply_office_textbox_fit
from .qa_registry import write_page_quality_report
from .semantic_plan import load_semantic_plan
from .semantic_typography_qa import apply_semantic_typography_qa
from .source_capture import (
    attach_render_delta_measurement,
    build_source_capture,
    build_source_capture_gate,
    expected_texts_from_source_capture,
)
from .text_content_qa import build_text_content_qa


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _command_path(name: str) -> str | None:
    return shutil.which(name)


def _render_pptx_preview(pptx_path: Path, exports: Path) -> Path:
    soffice = _command_path("soffice") or _command_path("libreoffice")
    pdftoppm = _command_path("pdftoppm")
    if not soffice:
        raise RuntimeError("soffice/libreoffice is required for --render-preview")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is required for --render-preview")

    exports.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_path),
                str(pptx_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        pdf_path = temp_path / f"{pptx_path.stem}.pdf"
        if not pdf_path.exists():
            matches = sorted(temp_path.glob("*.pdf"))
            if not matches:
                raise RuntimeError("LibreOffice did not create a PDF preview")
            pdf_path = matches[0]
        target_pdf = exports / "page-render.pdf"
        shutil.copyfile(pdf_path, target_pdf)
        prefix = temp_path / "page-render"
        subprocess.run(
            [pdftoppm, "-png", "-singlefile", "-r", "144", str(pdf_path), str(prefix)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        rendered = prefix.with_suffix(".png")
        if not rendered.exists():
            raise RuntimeError("pdftoppm did not create a PNG preview")
        target_png = exports / "page-render.png"
        shutil.copyfile(rendered, target_png)
        return target_png


def _build_side_by_side(reference: Path, rendered: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(reference) as left_source, Image.open(rendered) as right_source:
        left = left_source.convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS)
        right = right_source.convert("RGB").resize((1280, 720), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (2560, 720), "#FFFFFF")
        canvas.paste(left, (0, 0))
        canvas.paste(right, (1280, 0))
        canvas.save(target)


def _render_boxes(plan) -> list[dict]:
    boxes = []
    for item in plan.items:
        boxes.append(
            {
                "text": item.display_text,
                "bbox": item.bbox,
                "font_size": item.font_size,
                "font_family": item.font_family,
                "fill": item.fill,
                "bold": item.bold,
                "align": item.align,
                "v_align": "mid" if item.v_align == "middle" else item.v_align,
                "role": item.role,
                "container_id": item.container_id,
            }
        )
    return boxes


def _xyxy_to_rect(box: list[float]) -> dict:
    x1, y1, x2, y2 = [float(value) for value in box]
    return {
        "x": round(x1, 3),
        "y": round(y1, 3),
        "w": round(x2 - x1, 3),
        "h": round(y2 - y1, 3),
    }


def _source_capture_text_mapping(page_number: int, boxes: list[dict]) -> dict:
    mapped = []
    for box in boxes:
        rect = _xyxy_to_rect(list(box["bbox"]))
        mapped.append(
            {
                "text": box["text"],
                **rect,
                "font_size": box["font_size"],
                "font_family": box["font_family"],
                "fill": box["fill"],
                "font_weight": "700" if box.get("bold") else "400",
                "align": box.get("align"),
                "container_id": box.get("container_id"),
                "role": box.get("role"),
                "word_wrap": "\n" in str(box.get("text", "")),
                "source": "semantic_plan",
                "confidence": 1.0,
            }
        )
    return {
        "schema": "cyberppt.dual_image.ocr_text_mapping.v1",
        "page_number": page_number,
        "boxes": mapped,
    }


def _source_capture_containers(page_number: int, plan) -> dict:
    containers = []
    for container in plan.containers:
        rect = _xyxy_to_rect(list(container.bbox))
        safe = _xyxy_to_rect(list(container.text_safe_bbox))
        containers.append(
            {
                "id": container.id,
                "role": container.role,
                **rect,
                "text_safe_bbox": safe,
            }
        )
    return {
        "schema": "cyberppt.dual_image.semantic_containers.v1",
        "page_number": page_number,
        "containers": containers,
    }


def _source_capture_typography(page_number: int, boxes: list[dict]) -> dict:
    return {
        "schema": "cyberppt.dual_image.typography_decisions.v1",
        "page_number": page_number,
        "decisions": [
            {
                "text": box["text"],
                "rendered_text": box["text"],
                "role": box.get("role"),
                "applied_px": box.get("font_size"),
            }
            for box in boxes
        ],
    }


def _source_capture_pair_manifest(page_number: int, full: Path, background: Path) -> dict:
    return {
        "schema": "cyberppt.dual_image.page_image_pairs.v1",
        "generation_contract": {
            "slide_canvas": {"width": 1280, "height": 720},
            "brand_body_region": {"x": 0, "y": 0, "width": 1280, "height": 720},
        },
        "pairs": [
            {
                "page_number": page_number,
                "full": {
                    "filename": full.name,
                    "path": str(full),
                    "status": "ready",
                    "image_size": {"width": 1280, "height": 720},
                },
                "background": {
                    "filename": background.name,
                    "path": str(background),
                    "status": "ready",
                    "image_size": {"width": 1280, "height": 720},
                },
            }
        ],
    }


def _write_source_capture_inputs(
    out_dir: Path,
    *,
    page_number: int,
    plan,
    boxes: list[dict],
    full_norm: Path,
    background_norm: Path,
) -> None:
    _write_json(
        out_dir / "analysis" / "ocr" / f"page_{page_number:03d}_text_mapping.json",
        _source_capture_text_mapping(page_number, boxes),
    )
    _write_json(
        out_dir / "analysis" / "semantic_containers" / f"page_{page_number:03d}_containers.json",
        _source_capture_containers(page_number, plan),
    )
    _write_json(
        out_dir / "analysis" / "typography" / f"page_{page_number:03d}_typography.json",
        _source_capture_typography(page_number, boxes),
    )
    _write_json(
        out_dir / "images" / "page_image_pairs.json",
        _source_capture_pair_manifest(page_number, full_norm, background_norm),
    )


def _alignment_layout(plan) -> dict:
    return {
        "items": [
            {
                "text": item.display_text,
                "bbox": item.source_bbox,
                "role": item.role,
                "container_id": item.container_id,
            }
            for item in plan.items
        ]
    }


def _apply_transform_to_boxes(boxes: list[dict], transform: AlignmentTransform) -> list[dict]:
    transformed = []
    for box in boxes:
        updated = dict(box)
        updated["source_bbox"] = list(box["bbox"])
        updated["bbox"] = [round(value, 3) for value in transform.map_bbox(list(box["bbox"]))]
        transformed.append(updated)
    return transformed


def build_page(args: argparse.Namespace) -> dict:
    out_dir = args.out_dir.resolve()
    normalized = out_dir / "normalized"
    analysis = out_dir / "analysis"
    exports = out_dir / "exports"
    full_norm = normalized / "full-1280x720.png"
    background_norm = normalized / "background-1280x720.png"

    normalize_image(args.full.resolve(), full_norm)
    normalize_image(args.background.resolve(), background_norm)

    plan = load_semantic_plan(args.semantic_plan.resolve())
    layout_qa = check_layout(plan)
    _write_json(analysis / "layout_qa.json", layout_qa)

    background_scan = {
        "valid": True,
        "skipped": True,
        "reason": "no_background_layout_supplied",
        "error_count": 0,
    }
    if args.background_layout:
        background_scan = scan_background_text(args.background_layout.resolve())
    _write_json(analysis / "background_text_scan.json", background_scan)

    if args.align_from_full:
        transform = estimate_alignment(full_norm, background_norm, _alignment_layout(plan))
        geometry_source = "full_to_background_alignment"
    else:
        transform = AlignmentTransform(model="semantic-container-geometry")
        geometry_source = "semantic_plan_containers"

    boxes = _render_boxes(plan)
    if args.align_from_full:
        boxes = _apply_transform_to_boxes(boxes, transform)
    boxes, semantic_typography_qa = apply_semantic_typography_qa(
        boxes,
        report_path=analysis / "semantic_typography_qa.json",
    )
    boxes, office_textbox_fit = apply_office_textbox_fit(
        boxes,
        canvas={"width": 1280, "height": 720},
        background_image=background_norm,
        report_path=analysis / "office_textbox_fit.json",
    )
    container_workspace = build_container_workspace(
        page_number=args.page_number,
        containers=list(plan.containers),
        text_items=boxes,
        stage="overlay",
    )
    container_workspace_path = analysis / "container_workspace" / f"page_{args.page_number:03d}_container_workspace.json"
    write_container_workspace(container_workspace_path, container_workspace)
    _write_source_capture_inputs(
        out_dir,
        page_number=args.page_number,
        plan=plan,
        boxes=boxes,
        full_norm=full_norm,
        background_norm=background_norm,
    )
    source_capture = build_source_capture(out_dir)
    _write_json(analysis / "source_capture.json", source_capture)
    source_capture_gate = build_source_capture_gate(source_capture)
    _write_json(analysis / "source_capture_gate.json", source_capture_gate)
    mapping = {
        "schema": "cyberppt.dual_image.text_mapping.v1",
        "delivery_mode": "dual_image_editable_overlay",
        "canvas": {"width": 1280, "height": 720},
        "background": str(background_norm),
        "semantic_plan": str(args.semantic_plan.resolve()),
        "geometry_source": geometry_source,
        "alignment": transform.to_dict(),
        "semantic_typography_qa": str(analysis / "semantic_typography_qa.json"),
        "office_textbox_fit": str(analysis / "office_textbox_fit.json"),
        "boxes": boxes,
    }
    _write_json(analysis / "text_mapping.json", mapping)

    pptx_path = exports / "page.pptx"
    job = {
        "canvas": {"width": 1280, "height": 720},
        "slide": {"width_in": 13.333, "height_in": 7.5},
        "background": str(background_norm),
        "output_pptx": str(pptx_path),
        "boxes": boxes,
    }
    job_path = analysis / "render_job.json"
    _write_json(job_path, job)
    subprocess.run(
        ["node", str(ROOT / "scripts/dual_image_overlay/render_overlay.mjs"), str(job_path)],
        cwd=ROOT,
        check=True,
    )

    expected = expected_texts_from_source_capture(source_capture)
    text_content_qa = build_text_content_qa(pptx_path, expected)
    _write_json(analysis / "text_content_qa.json", text_content_qa)

    visual_preview = {
        "valid": False,
        "skipped": True,
        "reason": "render_preview_not_requested",
        "artifacts": {},
    }
    if args.render_preview:
        rendered_png = _render_pptx_preview(pptx_path, exports)
        side_by_side = exports / "side-by-side.png"
        _build_side_by_side(full_norm, rendered_png, side_by_side)
        visual_preview = {
            "valid": True,
            "skipped": False,
            "human_review_required": True,
            "artifacts": {
                "ppt_render": str(rendered_png),
                "side_by_side": str(side_by_side),
            },
        }
        source_capture = attach_render_delta_measurement(
            source_capture,
            rendered_preview=str(rendered_png),
        )
        _write_json(analysis / "source_capture.json", source_capture)
        source_capture_gate = build_source_capture_gate(source_capture)
        _write_json(analysis / "source_capture_gate.json", source_capture_gate)
    _write_json(analysis / "visual_preview.json", visual_preview)

    qa_artifacts = {
        "layout_qa": str(analysis / "layout_qa.json"),
        "text_content_qa": str(analysis / "text_content_qa.json"),
        "semantic_typography_qa": str(analysis / "semantic_typography_qa.json"),
        "office_textbox_fit": str(analysis / "office_textbox_fit.json"),
        "container_workspace": str(container_workspace_path),
        "background_text_scan": str(analysis / "background_text_scan.json"),
        "source_capture_gate": str(analysis / "source_capture_gate.json"),
        "visual_preview": str(analysis / "visual_preview.json"),
        "pptx": str(pptx_path),
    }
    page_quality_report = write_page_quality_report(
        analysis / "page_quality_report.json",
        stage="overlay",
        page_number=args.page_number,
        project_path=out_dir,
        artifacts=qa_artifacts,
        reports={
            "layout_qa": layout_qa,
            "text_content_qa": text_content_qa,
            "semantic_typography_qa": semantic_typography_qa,
            "office_textbox_fit": office_textbox_fit,
            "container_workspace": container_workspace,
            "background_text_scan": background_scan,
            "source_capture_gate": source_capture_gate,
            "visual_preview": visual_preview,
        },
        extra={
            "geometry_source": geometry_source,
            "alignment": transform.to_dict(),
        },
    )

    structural_valid = bool(layout_qa["valid"] and text_content_qa["valid"] and background_scan["valid"])
    human_visual_review_pass = False
    readiness = {
        "schema": "cyberppt.dual_image.production_readiness.v1",
        "valid": bool(
            structural_valid
            and source_capture_gate["valid"]
            and visual_preview["valid"]
            and human_visual_review_pass
        ),
        "structural_valid": structural_valid,
        "checks": {
            "delivery_mode": "dual_image_editable_overlay",
            "background_snapshot_editable_text": True,
            "background_has_no_text": bool(background_scan["valid"]),
            "background_image_declared": True,
            "all_key_text_editable": bool(text_content_qa["valid"]),
            "text_content_matches_lock": bool(text_content_qa["valid"]),
            "layout_qa_pass": bool(layout_qa["valid"]),
            "visual_preview_generated": bool(visual_preview["valid"]),
            "human_visual_review_pass": human_visual_review_pass,
            "source_capture_available": bool(source_capture["pages"]),
            "source_capture_consumed": True,
            "source_capture_gate_pass": bool(source_capture_gate["valid"]),
            "source_capture_text_drives_qa": True,
            "source_capture_gaps_resolved": bool(source_capture_gate["checks"]["capture_gaps_resolved"]),
            "page_quality_report_pass": bool(page_quality_report["valid"]),
        },
        "source_capture_gate": source_capture_gate,
        "geometry_source": geometry_source,
        "alignment": transform.to_dict(),
        "status": "source_capture_rework_required"
        if structural_valid and not source_capture_gate["valid"]
        else "ready_for_human_visual_review"
        if structural_valid
        else "structural_rework_required",
        "artifacts": {
            "normalized_full": str(full_norm),
            "normalized_background": str(background_norm),
            "pptx": str(pptx_path),
            "text_mapping": str(analysis / "text_mapping.json"),
            "text_content_qa": str(analysis / "text_content_qa.json"),
            "layout_qa": str(analysis / "layout_qa.json"),
            "semantic_typography_qa": str(analysis / "semantic_typography_qa.json"),
            "container_workspace": str(container_workspace_path),
            "background_text_scan": str(analysis / "background_text_scan.json"),
            "visual_preview": str(analysis / "visual_preview.json"),
            "source_capture": str(analysis / "source_capture.json"),
            "source_capture_gate": str(analysis / "source_capture_gate.json"),
            "page_quality_report": str(analysis / "page_quality_report.json"),
        },
        "semantic_typography_qa": semantic_typography_qa,
        "page_quality_report": page_quality_report,
    }
    _write_json(analysis / "production_readiness.json", readiness)
    return readiness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build one CyberPPT dual image editable overlay page.")
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--semantic-plan", type=Path, required=True)
    parser.add_argument("--background-layout", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--page-number", type=int, default=1)
    parser.add_argument("--render-preview", action="store_true")
    parser.add_argument(
        "--align-from-full",
        action="store_true",
        help="Diagnostic fallback: estimate full-to-background alignment and transform text boxes.",
    )
    return parser


def main() -> int:
    result = build_page(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
