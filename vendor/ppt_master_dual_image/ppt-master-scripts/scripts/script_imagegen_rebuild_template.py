#!/usr/bin/env python3
"""Script imagegen -> OCR text overlay -> template PPTX route."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

import page_image_pair_batch
from ocr_text_locator import load_layout, locate_text
from script_text_overlay import (
    boxes_to_json,
    build_overlay_boxes,
    containers_to_json,
    extract_semantic_plan,
    infer_semantic_containers,
    render_overlay_svg,
    semantic_plan_to_json,
)
from template_image_ppt_export import (
    CANVAS_SIZE,
    copy_brand,
    extract_content,
    inset_content_region,
    load_brand_rules,
    page_notes_text,
    page_stem,
    parse_page_blocks,
    scale_region,
    write_spec_lock,
)


SCRIPTS_DIR = Path(__file__).resolve().parent


def load_pair_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Pair manifest must be a JSON object.")
    return data


def resolve_project_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    raw = manifest.get("project_path")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser().resolve()
    # Expected path: <project>/images/script_imagegen/page_image_pairs.json
    return manifest_path.resolve().parents[2]


def _require_image(item: dict[str, Any], key: str) -> Path:
    raw = item.get("path")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"Missing {key}.path in pair manifest.")
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"Missing {key} image: {path}")
    return path


def _copy_image_to_project(image_path: Path, project_path: Path) -> str:
    images_dir = project_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / image_path.name
    if image_path.resolve() != target.resolve():
        shutil.copy2(image_path, target)
    return "../images/" + target.name


def _prepare_background_image(
    *,
    full_image: Path,
    background_image: Path,
    project_path: Path,
) -> tuple[Path, dict[str, Any]]:
    images_dir = project_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / background_image.name
    with Image.open(full_image) as full, Image.open(background_image) as background:
        full_size = full.size
        background_size = background.size
        if full_size == background_size:
            if background_image.resolve() != target.resolve():
                shutil.copy2(background_image, target)
            return target, {
                "status": "matched",
                "full_size": list(full_size),
                "background_size": list(background_size),
                "output_size": list(full_size),
                "output_path": str(target),
            }
        normalized = background.convert("RGB").resize(full_size, Image.Resampling.LANCZOS)
        normalized.save(target)
        return target, {
            "status": "normalized",
            "full_size": list(full_size),
            "background_size": list(background_size),
            "output_size": list(full_size),
            "output_path": str(target),
        }


def _write_rebuild_quality(project_path: Path, pages: list[dict[str, Any]]) -> None:
    quality_path = project_path / "analysis" / "rebuild_quality.json"
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text(
        json.dumps({"pages": pages}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _body_region() -> dict[str, int]:
    rules = load_brand_rules()
    brand_body_region = scale_region(rules["content_regions"]["body_pages"], CANVAS_SIZE)
    return inset_content_region(brand_body_region)


def _ensure_project_shell(project_path: Path) -> None:
    for subdir in ("svg_output", "notes", "templates", "images", "exports", "analysis/ocr"):
        (project_path / subdir).mkdir(parents=True, exist_ok=True)
    rules = load_brand_rules()
    copy_brand(project_path)
    write_spec_lock(project_path, rules, CANVAS_SIZE)


def _layout_for_page(
    *,
    full_image: Path,
    ocr_dir: Path,
    page_number: int,
    ocr_backend: str,
    force_ocr: bool,
    timeout: int,
) -> tuple[Path, dict[str, Any]]:
    layout_path = ocr_dir / f"page_{page_number:03d}_text_layout.json"
    if layout_path.is_file() and not force_ocr:
        return layout_path, load_layout(layout_path)
    layout = locate_text(full_image, backend=ocr_backend, output_path=layout_path, timeout=timeout)
    return layout_path, layout


def rebuild_from_manifest(
    manifest_path: Path,
    *,
    ocr_backend: str = "vision-json",
    force_ocr: bool = False,
    timeout: int = 300,
) -> dict[str, Any]:
    """Create overlay SVG pages from generated full/background image pairs."""
    manifest_path = manifest_path.resolve()
    manifest = load_pair_manifest(manifest_path)
    project_path = resolve_project_path(manifest_path, manifest)
    source_script = Path(str(manifest.get("source_script", ""))).expanduser().resolve()
    if not source_script.is_file():
        raise FileNotFoundError(f"Source script not found: {source_script}")

    _ensure_project_shell(project_path)
    body = _body_region()
    pages = parse_page_blocks(source_script)
    ocr_dir = project_path / "analysis" / "ocr"
    semantic_plan_dir = project_path / "analysis" / "semantic_plan"
    containers_dir = project_path / "analysis" / "semantic_containers"
    semantic_plan_dir.mkdir(parents=True, exist_ok=True)
    containers_dir.mkdir(parents=True, exist_ok=True)
    svg_count = 0
    quality_pages: list[dict[str, Any]] = []

    for pair in manifest.get("pairs", []):
        page_number = int(pair["page_number"])
        if "background" not in pair:
            raise ValueError(f"Page {page_number} has no background variant. Run with --dual-image first.")
        full_image = _require_image(pair["full"], "full")
        background_image = _require_image(pair["background"], "background")
        prepared_background, image_size_check = _prepare_background_image(
            full_image=full_image,
            background_image=background_image,
            project_path=project_path,
        )
        layout_path, layout = _layout_for_page(
            full_image=full_image,
            ocr_dir=ocr_dir,
            page_number=page_number,
            ocr_backend=ocr_backend,
            force_ocr=force_ocr,
            timeout=timeout,
        )
        semantic_plan = extract_semantic_plan(source_script, page_number)
        semantic_plan_path = semantic_plan_dir / f"page_{page_number:03d}_semantic_plan.json"
        semantic_plan_path.write_text(
            json.dumps(semantic_plan_to_json(semantic_plan), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        containers = infer_semantic_containers(prepared_background, layout, body, semantic_plan=semantic_plan)
        containers_path = containers_dir / f"page_{page_number:03d}_containers.json"
        containers_path.write_text(
            json.dumps(
                {
                    "page_number": page_number,
                    "background_image": str(prepared_background),
                    "semantic_plan": str(semantic_plan_path),
                    "containers": containers_to_json(containers),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        boxes = build_overlay_boxes(
            source_script,
            page_number,
            layout,
            body,
            background_image=prepared_background,
            semantic_containers=containers,
            semantic_plan=semantic_plan,
        )
        mapping_path = ocr_dir / f"page_{page_number:03d}_text_mapping.json"
        mapping_path.write_text(
            json.dumps(
                {
                    "page_number": page_number,
                    "ocr_layout": str(layout_path),
                    "boxes": boxes_to_json(boxes),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        block = pages.get(page_number)
        if block is not None:
            content = extract_content(block)
            slide_title = content.title
            subtitle = content.subtitle
            notes_text = page_notes_text(block)
            title_for_name = block.title
        else:
            slide_title = str(pair.get("title") or page_number)
            subtitle = ""
            notes_text = ""
            title_for_name = slide_title

        background_href = "../images/" + prepared_background.name
        svg = render_overlay_svg(
            background_href=background_href,
            canvas={"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
            body_region=body,
            slide_title=slide_title,
            subtitle=subtitle,
            text_boxes=boxes,
        )
        stem = page_stem(page_number, title_for_name)
        (project_path / "svg_output" / f"{stem}.svg").write_text(svg, encoding="utf-8")
        (project_path / "notes" / f"{stem}.md").write_text(f"# {slide_title}\n\n{notes_text}\n", encoding="utf-8")
        svg_count += 1
        quality_pages.append(
            {
                "page_number": page_number,
                "title": title_for_name,
                "semantic_plan": str(semantic_plan_path),
                "semantic_containers": str(containers_path),
                "image_size_check": image_size_check,
                "text_color_check": {
                    "white_text_boxes": sum(1 for box in boxes if box.fill.upper() == "#FFFFFF"),
                    "total_text_boxes": len(boxes),
                },
            }
        )

    _write_rebuild_quality(project_path, quality_pages)
    return {"project_path": str(project_path), "slides": svg_count, "svg_dir": str(project_path / "svg_output")}


def export_project(project_path: Path) -> Path:
    commands = [
        [sys.executable, str(SCRIPTS_DIR / "svg_quality_checker.py"), str(project_path)],
        [sys.executable, str(SCRIPTS_DIR / "finalize_svg.py"), str(project_path)],
        [sys.executable, str(SCRIPTS_DIR / "svg_to_pptx.py"), str(project_path), "-t", "none", "-a", "none"],
    ]
    for command in commands:
        subprocess.run(command, check=True)
    exports = sorted((project_path / "exports").glob("*.pptx"), key=lambda p: p.stat().st_mtime)
    if not exports:
        raise FileNotFoundError(f"No PPTX exported in {project_path / 'exports'}")
    return exports[-1]


def run_script_imagegen_rebuild(args: argparse.Namespace) -> dict[str, Any]:
    """Generate full/background pairs, rebuild editable text overlays, and export PPTX."""
    page_image_pair_batch.apply_run_speed_options(args)
    args.dual_image = True
    project_path, project_script = page_image_pair_batch._resolve_or_create_project(args)
    images_dir = (
        args.images_dir.resolve()
        if args.images_dir
        else project_path / "images" / "script_imagegen"
    )
    images_dir.mkdir(parents=True, exist_ok=True)

    _manifest, manifest_path, page_numbers = page_image_pair_batch._create_plan(
        script_path=project_script,
        pages_raw=args.pages,
        output_dir=images_dir,
        aspect_ratio=args.aspect_ratio,
        image_size=args.image_size,
        canvas=args.canvas,
        project_path=project_path,
        image_style_name=args.image_style,
        resume=args.resume,
        include_background=True,
    )
    print(f"Project: {project_path}")
    print(f"Source script: {project_script}")
    print(f"Pair manifest: {manifest_path}")
    print(f"Image dir: {images_dir}")
    print(f"Pages: {', '.join(str(num) for num in page_numbers)}")

    generate_args = argparse.Namespace(
        manifest=manifest_path,
        model=args.model,
        size=args.size,
        quality=args.quality,
        background_method="codex-edit",
        timeout=args.timeout,
        full_retries=args.full_retries,
        background_retries=args.background_retries,
        parallel_pages=args.parallel_pages,
        include_background=True,
        force=args.force,
        dry_run=args.dry_run,
    )
    rc = page_image_pair_batch.generate_pairs(generate_args)
    if rc != 0 or args.dry_run:
        return {
            "project_path": str(project_path),
            "source_script": str(project_script),
            "pair_manifest": str(manifest_path),
            "pages": page_numbers,
            "dry_run": bool(args.dry_run),
            "exported_pptx": None,
        }

    verify_args = argparse.Namespace(manifest=manifest_path, mark_missing_manual=False)
    rc = page_image_pair_batch.verify_manifest(verify_args)
    if rc != 0:
        raise RuntimeError(f"Image verification failed: {manifest_path}")

    rebuild_result = rebuild_from_manifest(
        manifest_path,
        ocr_backend=args.ocr_backend,
        force_ocr=args.force_ocr,
        timeout=args.ocr_timeout,
    )
    pptx = export_project(Path(rebuild_result["project_path"])) if args.export else None
    return {
        **rebuild_result,
        "source_script": str(project_script),
        "pair_manifest": str(manifest_path),
        "pages": page_numbers,
        "exported_pptx": str(pptx) if pptx else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild script-imagegen full/background pairs as template PPTX with editable text.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser(
        "run",
        help="Run script-imagegen -> full/background images -> OCR text overlay -> template PPTX.",
    )
    run.add_argument("--script", required=True, type=Path, help="script-imagegen-compact.md")
    run.add_argument("--pages", default="all", help="Page selection, e.g. 11, 8-13, 1,3,5-7, or all.")
    run.add_argument("--project-name", default=None, help="Project name prefix. Defaults to script stem + selected pages.")
    run.add_argument("--projects-dir", default=Path("projects"), type=Path, help="Base directory for newly created projects.")
    run.add_argument("--project-path", default=None, type=Path, help="Reuse an existing PPT Master project instead of creating a new one.")
    run.add_argument("--format", default="ppt169", help="Canvas format for newly created projects.")
    run.add_argument("--images-dir", default=None, type=Path, help="Override image/task directory. Defaults to <project>/images/script_imagegen.")
    run.add_argument("--aspect-ratio", default=page_image_pair_batch.DEFAULT_ASPECT_RATIO, help="Generation aspect ratio.")
    run.add_argument("--image-size", default=page_image_pair_batch.DEFAULT_IMAGE_SIZE, help="Generation image size label.")
    run.add_argument("--canvas", default=page_image_pair_batch.DEFAULT_CANVAS, help="Canvas size label written into tasks.")
    run.add_argument("--image-style", default=page_image_pair_batch.DEFAULT_STYLE_NAME, help="Image style preset name or style JSON/Markdown path.")
    run.add_argument("--model", default="gpt-image-2", help="Image model for Codex OAuth.")
    run.add_argument("--size", default=None, help="Codex output size, e.g. 1280x720. Defaults to each task canvas.")
    run.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="high")
    run.add_argument("--timeout", type=int, default=300, help="Image generation timeout.")
    run.add_argument("--full-retries", type=int, default=1)
    run.add_argument("--background-retries", type=int, default=1)
    run.add_argument("--parallel-pages", type=int, default=1)
    run.add_argument("--draft", action="store_true", help="Use faster draft image settings unless explicitly overridden.")
    run.add_argument("--resume", action="store_true", help="Reuse an existing page_image_pairs.json in the image directory.")
    run.add_argument("--force", action="store_true", help="Overwrite existing images.")
    run.add_argument("--dry-run", action="store_true", help="Plan and show image request metadata without calling the image backend.")
    run.add_argument("--ocr-backend", choices=("vision-json", "paddleocr-vl", "none"), default="vision-json")
    run.add_argument("--force-ocr", action="store_true")
    run.add_argument("--ocr-timeout", type=int, default=300)
    run.add_argument("--export", action="store_true", default=True, help="Export PPTX after rebuilding overlay SVG pages.")
    run.add_argument("--no-export", action="store_false", dest="export", help="Only rebuild SVG/mapping artifacts.")

    rebuild = sub.add_parser("rebuild", help="Rebuild overlay SVG pages from an existing page_image_pairs.json.")
    rebuild.add_argument("manifest", type=Path)
    rebuild.add_argument("--ocr-backend", choices=("vision-json", "paddleocr-vl", "none"), default="vision-json")
    rebuild.add_argument("--force-ocr", action="store_true")
    rebuild.add_argument("--timeout", type=int, default=300)
    rebuild.add_argument("--export", action="store_true", help="Run SVG quality/finalize/export after rebuilding SVG pages.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            result = run_script_imagegen_rebuild(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            result = rebuild_from_manifest(
                args.manifest,
                ocr_backend=args.ocr_backend,
                force_ocr=args.force_ocr,
                timeout=args.timeout,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if args.export:
                pptx = export_project(Path(result["project_path"]))
                print(f"PPTX: {pptx}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
