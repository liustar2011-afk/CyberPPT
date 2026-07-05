#!/usr/bin/env python3
"""CyberPPT dual-image manifest -> editable text overlay -> template PPTX route."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from scripts.dual_image_overlay.scene_graph.builder import build_page_scene_graph
from scripts.dual_image_overlay.scene_graph.gate import build_scene_graph_gate
from scripts.dual_image_overlay.scene_graph.layout import build_layout_plan_from_scene_graph
from scripts.dual_image_overlay.scene_graph.schema import scene_graph_to_dict

from ocr_text_locator import load_layout, locate_text
from script_text_overlay import (
    OverlayTextBox,
    SemanticContainer,
    build_overlay_boxes_from_semantic_plan,
    boxes_to_json,
    build_overlay_boxes,
    build_semantic_layout_plan,
    containers_to_json,
    extract_semantic_plan,
    extract_script_truth_sections,
    infer_semantic_containers,
    reconcile_semantic_plan_with_script_truth,
    render_overlay_svg,
    resolve_overlay_coordinate_context,
    semantic_plan_to_json,
    validate_explicit_semantic_plan,
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


def _load_explicit_semantic_plan(semantic_plan_dir: Path | None, page_number: int) -> tuple[Path, dict[str, Any]] | None:
    if semantic_plan_dir is None:
        return None
    candidates = [
        semantic_plan_dir / f"page_{page_number:03d}_semantic_plan.json",
        semantic_plan_dir / f"slide-{page_number:02d}-semantic-plan.json",
        semantic_plan_dir / f"slide-{page_number:02d}-semantic_plan.json",
    ]
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Semantic plan must be a JSON object: {path}")
            return path, data
    return None


def _load_visual_registry(visual_registry_dir: Path | None, page_number: int) -> tuple[Path, dict[str, Any]] | None:
    if visual_registry_dir is None:
        return None
    candidates = [
        visual_registry_dir / f"slide-{page_number:02d}-visual-element-registry.json",
        visual_registry_dir / f"page_{page_number:03d}_visual_element_registry.json",
    ]
    for path in candidates:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"Visual registry must be a JSON object: {path}")
            return path, data
    return None


def _semantic_container_from_plan(container: dict[str, Any]) -> SemanticContainer:
    bbox = container.get("bbox") if isinstance(container.get("bbox"), list) else [0, 0, 0, 0]
    x1, y1, x2, y2 = [float(value) for value in bbox]
    return SemanticContainer(
        id=str(container.get("id") or ""),
        role=str(container.get("role") or "container"),
        x=round(x1, 2),
        y=round(y1, 2),
        w=round(max(1.0, x2 - x1), 2),
        h=round(max(1.0, y2 - y1), 2),
        background=str(container.get("background") or "light"),
        fill=str(container.get("fill") or "#0B1F3D"),
        align=str(container.get("align") or "center"),
        max_lines=int(container.get("max_lines") or 1),
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


def _scene_graph_artifact_paths(project_path: Path, page_number: int) -> dict[str, Path]:
    return {
        "graph": project_path / "analysis" / "scene_graph" / f"page_{page_number:03d}_scene_graph.json",
        "gate": project_path / "analysis" / "scene_graph_gate" / f"page_{page_number:03d}_scene_graph_gate.json",
        "layout": project_path / "analysis" / "page_layout_plan" / f"page_{page_number:03d}_layout_plan.json",
    }


def _scene_graph_gate_blocks_export(gate_path: Path) -> bool:
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    return bool(gate.get("blocking_count") or not gate.get("valid", False))


def _image_size_for_scene_graph(image_size_check: dict[str, Any]) -> dict[str, float]:
    output_size = image_size_check.get("output_size")
    if isinstance(output_size, list) and len(output_size) == 2:
        return {"width": float(output_size[0]), "height": float(output_size[1])}
    full_size = image_size_check.get("full_size")
    if isinstance(full_size, list) and len(full_size) == 2:
        return {"width": float(full_size[0]), "height": float(full_size[1])}
    return {"width": float(CANVAS_SIZE[0]), "height": float(CANVAS_SIZE[1])}


def _write_scene_graph_artifacts(
    *,
    project_path: Path,
    page_number: int,
    source_script: Path,
    semantic_plan_payload: dict[str, Any],
    visual_registry: dict[str, Any] | None,
    image_size_check: dict[str, Any],
) -> dict[str, Path]:
    paths = _scene_graph_artifact_paths(project_path, page_number)
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    graph = build_page_scene_graph(
        page_number=page_number,
        script_sections=extract_script_truth_sections(source_script, page_number),
        semantic_plan=semantic_plan_payload,
        visual_registry=visual_registry or {"blueprint_canvas_px": {"w": CANVAS_SIZE[0], "h": CANVAS_SIZE[1]}, "elements": []},
        image_size=_image_size_for_scene_graph(image_size_check),
    )
    graph_gate = build_scene_graph_gate(graph)
    paths["graph"].write_text(json.dumps(scene_graph_to_dict(graph), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths["gate"].write_text(json.dumps(graph_gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if _scene_graph_gate_blocks_export(paths["gate"]):
        raise ValueError(f"Scene graph gate failed for page {page_number}: {graph_gate['issues']}")
    page_layout_plan = build_layout_plan_from_scene_graph(graph)
    paths["layout"].write_text(json.dumps(page_layout_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return paths


def _overlay_boxes_from_scene_graph_layout(
    page_layout_plan: dict[str, Any],
    body_region: dict[str, float],
    *,
    font_family: str = "Microsoft YaHei",
    fill: str = "#0B1F3D",
) -> list[OverlayTextBox]:
    sx = float(body_region["width"]) / float(CANVAS_SIZE[0])
    sy = float(body_region["height"]) / float(CANVAS_SIZE[1])
    boxes: list[OverlayTextBox] = []
    for index, item in enumerate(page_layout_plan.get("items", [])):
        if not isinstance(item, dict):
            continue
        bbox = item.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"page_layout_plan.items[{index}].bbox must contain four numbers.")
        x1, y1, x2, y2 = [float(value) for value in bbox]
        boxes.append(
            OverlayTextBox(
                text=str(item.get("text") or ""),
                x=round(float(body_region["x"]) + x1 * sx, 2),
                y=round(float(body_region["y"]) + y1 * sy, 2),
                w=round(max(1.0, (x2 - x1) * sx), 2),
                h=round(max(1.0, (y2 - y1) * sy), 2),
                font_size=round(float(item.get("font_size") or 12) * sy, 2),
                font_family=font_family,
                fill=str(item.get("fill") or fill),
                font_weight=str(item.get("font_weight") or "400"),
                align=str(item.get("align") or "left"),
                word_wrap=bool(item.get("word_wrap", True)),
                source="scene_graph_layout",
                confidence=1.0,
            )
        )
    return boxes


def rebuild_from_manifest(
    manifest_path: Path,
    *,
    ocr_backend: str = "vision-json",
    force_ocr: bool = False,
    timeout: int = 300,
    visible_image_variant: str = "background",
    editable_text_visibility: str = "visible",
    explicit_semantic_plan_dir: Path | None = None,
    visual_registry_dir: Path | None = None,
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
    explicit_semantic_dir = explicit_semantic_plan_dir.resolve() if explicit_semantic_plan_dir else None
    explicit_visual_registry_dir = visual_registry_dir.resolve() if visual_registry_dir else None
    semantic_layout_dir = project_path / "analysis" / "semantic_layout_plan"
    semantic_gate_dir = project_path / "analysis" / "semantic_plan_gate"
    containers_dir = project_path / "analysis" / "semantic_containers"
    semantic_plan_dir.mkdir(parents=True, exist_ok=True)
    semantic_layout_dir.mkdir(parents=True, exist_ok=True)
    semantic_gate_dir.mkdir(parents=True, exist_ok=True)
    containers_dir.mkdir(parents=True, exist_ok=True)
    svg_count = 0
    quality_pages: list[dict[str, Any]] = []

    for pair in manifest.get("pairs", []):
        page_number = int(pair["page_number"])
        if "background" not in pair:
            raise ValueError(f"Page {page_number} has no background variant. Run with --dual-image first.")
        full_image = _require_image(pair["full"], "full")
        background_image = _require_image(pair["background"], "background")
        visible_image = full_image if visible_image_variant == "full" else background_image
        prepared_background, image_size_check = _prepare_background_image(
            full_image=full_image,
            background_image=visible_image,
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
        explicit_semantic = _load_explicit_semantic_plan(explicit_semantic_dir, page_number)
        visual_registry_entry = _load_visual_registry(explicit_visual_registry_dir, page_number)
        visual_registry = visual_registry_entry[1] if visual_registry_entry is not None else None
        semantic_plan = extract_semantic_plan(source_script, page_number)
        semantic_plan_path = semantic_plan_dir / f"page_{page_number:03d}_semantic_plan.json"
        if explicit_semantic is not None:
            explicit_path, explicit_plan = explicit_semantic
            explicit_plan = reconcile_semantic_plan_with_script_truth(explicit_plan, source_script, page_number)
            semantic_plan_path.write_text(
                json.dumps(explicit_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            semantic_gate = validate_explicit_semantic_plan(explicit_plan)
            coordinate_context = resolve_overlay_coordinate_context(
                explicit_plan,
                visual_registry=visual_registry,
                background_image=prepared_background,
            )
            semantic_layout_plan = build_semantic_layout_plan(
                explicit_plan,
                visual_registry=visual_registry,
                coordinate_context=coordinate_context,
            )
            if not semantic_gate["valid"]:
                raise ValueError(f"Semantic plan preflight failed for page {page_number}: {semantic_gate['issues']}")
            boxes, semantic_layout_plan, semantic_gate = build_overlay_boxes_from_semantic_plan(
                explicit_plan,
                body,
                visual_registry=visual_registry,
                background_image=prepared_background,
            )
            containers = [
                _semantic_container_from_plan(container)
                for container in explicit_plan.get("containers", [])
                if isinstance(container, dict)
            ]
            semantic_source = str(explicit_path)
            visual_registry_source = str(visual_registry_entry[0]) if visual_registry_entry is not None else None
            scene_graph_semantic_plan = explicit_plan
        else:
            scene_graph_semantic_plan = semantic_plan_to_json(semantic_plan)
            semantic_plan_path.write_text(
                json.dumps(scene_graph_semantic_plan, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            containers = infer_semantic_containers(prepared_background, layout, body, semantic_plan=semantic_plan)
            boxes = build_overlay_boxes(
                source_script,
                page_number,
                layout,
                body,
                background_image=prepared_background,
                semantic_containers=containers,
                semantic_plan=semantic_plan,
            )
            semantic_gate = validate_explicit_semantic_plan(None)
            semantic_layout_plan = {"schema": "cyberppt.dual_image.semantic_layout_plan.v1", "items": []}
            semantic_source = "script_derived_fallback"
            visual_registry_source = str(visual_registry_entry[0]) if visual_registry_entry is not None else None
        scene_graph_paths = _write_scene_graph_artifacts(
            project_path=project_path,
            page_number=page_number,
            source_script=source_script,
            semantic_plan_payload=scene_graph_semantic_plan,
            visual_registry=visual_registry,
            image_size_check=image_size_check,
        )
        page_layout_plan = json.loads(scene_graph_paths["layout"].read_text(encoding="utf-8"))
        boxes = _overlay_boxes_from_scene_graph_layout(page_layout_plan, body)
        semantic_gate_path = semantic_gate_dir / f"page_{page_number:03d}_semantic_plan_gate.json"
        semantic_gate_path.write_text(
            json.dumps(semantic_gate, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        semantic_layout_path = semantic_layout_dir / f"page_{page_number:03d}_layout_plan.json"
        semantic_layout_path.write_text(
            json.dumps(semantic_layout_plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
        mapping_path = ocr_dir / f"page_{page_number:03d}_text_mapping.json"
        mapping_path.write_text(
            json.dumps(
                {
                    "page_number": page_number,
                    "ocr_layout": str(layout_path),
                    "semantic_plan": str(semantic_plan_path),
                    "semantic_plan_gate": str(semantic_gate_path),
                    "semantic_layout_plan": str(semantic_layout_path),
                    "scene_graph": str(scene_graph_paths["graph"]),
                    "scene_graph_gate": str(scene_graph_paths["gate"]),
                    "page_layout_plan": str(scene_graph_paths["layout"]),
                    "semantic_source": semantic_source,
                    "editable_text_layout_source": "scene_graph_layout",
                    "visual_registry_source": visual_registry_source,
                    "geometry_truth": "scene_graph_layout",
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
        text_opacity = 0.0 if editable_text_visibility == "hidden" else 1.0
        svg = render_overlay_svg(
            background_href=background_href,
            canvas={"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
            body_region=body,
            slide_title=slide_title,
            subtitle=subtitle,
            text_boxes=boxes,
            text_opacity=text_opacity,
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
                "semantic_plan_gate": str(semantic_gate_path),
                "semantic_layout_plan": str(semantic_layout_path),
                "scene_graph": str(scene_graph_paths["graph"]),
                "scene_graph_gate": str(scene_graph_paths["gate"]),
                "page_layout_plan": str(scene_graph_paths["layout"]),
                "semantic_source": semantic_source,
                "editable_text_layout_source": "scene_graph_layout",
                "visual_registry_source": visual_registry_source,
                "semantic_containers": str(containers_path),
                "image_size_check": image_size_check,
                "text_color_check": {
                    "white_text_boxes": sum(1 for box in boxes if box.fill.upper() == "#FFFFFF"),
                    "total_text_boxes": len(boxes),
                },
                "visible_image_variant": visible_image_variant,
                "editable_text_visibility": editable_text_visibility,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild CyberPPT full/background image pairs as template PPTX with editable text.")
    sub = parser.add_subparsers(dest="command", required=True)

    rebuild = sub.add_parser("rebuild", help="Rebuild overlay SVG pages from an existing page_image_pairs.json.")
    rebuild.add_argument("manifest", type=Path)
    rebuild.add_argument("--ocr-backend", choices=("vision-json", "paddleocr-vl", "none"), default="vision-json")
    rebuild.add_argument("--force-ocr", action="store_true")
    rebuild.add_argument("--timeout", type=int, default=300)
    rebuild.add_argument("--visible-image-variant", choices=("background", "full"), default="background")
    rebuild.add_argument("--editable-text-visibility", choices=("visible", "hidden"), default="visible")
    rebuild.add_argument("--semantic-plan-dir", type=Path)
    rebuild.add_argument("--visual-registry-dir", type=Path)
    rebuild.add_argument("--export", action="store_true", help="Run SVG quality/finalize/export after rebuilding SVG pages.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = rebuild_from_manifest(
            args.manifest,
            ocr_backend=args.ocr_backend,
            force_ocr=args.force_ocr,
            timeout=args.timeout,
            visible_image_variant=args.visible_image_variant,
            editable_text_visibility=args.editable_text_visibility,
            explicit_semantic_plan_dir=args.semantic_plan_dir.resolve() if args.semantic_plan_dir else None,
            visual_registry_dir=args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
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
