from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.dual_image_overlay"

from .rebuild_modes import resolve_rebuild_mode as _resolve_rebuild_mode
from .rebuild_modes import visual_reference_for_mode as _visual_reference_for_mode
from .container_workspace import build_container_workspace, write_container_workspace
from .qa_registry import write_page_quality_report
from .source_capture import (
    attach_render_delta_measurement,
    build_source_capture,
    build_source_capture_gate,
    discover_visual_registry_dir,
)
from .structure_inference import infer_structure_containers
from .workspace_assignment import build_workspace_assignment, write_workspace_assignment


ROOT = Path(__file__).resolve().parents[2]
DUAL_IMAGE_DIR = Path(__file__).resolve().parent
PREFLIGHT_RULES = DUAL_IMAGE_DIR / "preflight_quality_rules.json"
BUILD_RULES = DUAL_IMAGE_DIR / "build_quality_rules.json"
POSTFLIGHT_RULES = DUAL_IMAGE_DIR / "postflight_quality_rules.json"
REBUILD_ENGINE = (
    ROOT
    / "scripts"
    / "dual_image_overlay"
    / "rebuild_engine"
    / "editable_overlay_rebuild.py"
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_project_path(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    raw = manifest.get("project_path")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser().resolve()
    return manifest_path.resolve().parents[2]


def _latest_pptx(project_path: Path) -> str | None:
    exports = sorted((project_path / "exports").glob("*.pptx"), key=lambda path: path.stat().st_mtime)
    return str(exports[-1]) if exports else None


def _template_gate(project_path: Path, *, export_requested: bool, exported_pptx: str | None) -> dict[str, Any]:
    checks = {
        "spec_lock_available": (project_path / "spec_lock.md").is_file(),
        "brand_rules_available": (project_path / "templates" / "brand_rules.json").is_file(),
        "master_chrome_available": (project_path / "templates" / "master_elements.svg").is_file(),
        "svg_output_available": any((project_path / "svg_output").glob("*.svg")),
        "pptx_exported": bool(exported_pptx) if export_requested else True,
    }
    return {
        "schema": "cyberppt.dual_image.template_gate.v1",
        "valid": all(checks.values()),
        "checks": checks,
        "export_requested": export_requested,
        "exported_pptx": exported_pptx,
    }


def _load_scene_graph_gates(project_path: Path) -> list[dict[str, Any]]:
    gate_paths = sorted((project_path / "analysis" / "scene_graph_gate").glob("page_*_scene_graph_gate.json"))
    return [_read_json(path) for path in gate_paths]


def _load_visual_qa_gate(project_path: Path) -> dict[str, Any] | None:
    path = project_path / "analysis" / "visual_qa_gate.json"
    return _read_json(path) if path.exists() else None


def _quality_rules(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"Quality rules must be a list: {path}")
    return [rule for rule in rules if isinstance(rule, dict)]


def _scene_graph_visual_elements(value: Any) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if any(key in value for key in ("bbox", "blueprint_bbox_px", "render_bbox_px", "ppt_target_bbox_px")):
            element = {key: item for key, item in value.items() if key in {"id", "element_id", "element_type", "type", "kind", "role", "bbox", "blueprint_bbox_px", "render_bbox_px", "ppt_target_bbox_px"}}
            element.setdefault("element_type", value.get("element_type") or value.get("type") or value.get("kind") or value.get("role") or "visual")
            element.setdefault("source", {"kind": "scene_graph"})
            elements.append(element)
        for child in value.values():
            elements.extend(_scene_graph_visual_elements(child))
    elif isinstance(value, list):
        for child in value:
            elements.extend(_scene_graph_visual_elements(child))
    return elements


def _build_template_container_workspaces(
    project_path: Path,
    source_capture: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace_dir = project_path / "analysis" / "container_workspace"
    assignment_dir = project_path / "analysis" / "workspace_assignment"
    structure_dir = project_path / "analysis" / "structure_inference"
    pages: list[dict[str, Any]] = []
    assignment_pages: list[dict[str, Any]] = []
    structure_pages: list[dict[str, Any]] = []
    for page in source_capture.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_number = page.get("page_number")
        containers = [item for item in page.get("containers", []) if isinstance(item, dict)]
        text_items = [item for item in page.get("text_objects", []) if isinstance(item, dict)]
        inferred = infer_structure_containers(
            page_number=page_number if isinstance(page_number, int) else None,
            text_items=text_items,
            canvas=(page.get("image_regions") or {}).get("canvas") if isinstance(page.get("image_regions"), dict) else None,
        )
        structure_pages.append(inferred)
        if isinstance(page_number, int):
            _write_json(structure_dir / f"page_{page_number:03d}_structure_inference.json", inferred)
        if inferred.get("valid") and int(inferred.get("container_count", 0) or 0) > len(containers):
            containers = [item for item in inferred.get("containers", []) if isinstance(item, dict)]
            text_items = [item for item in inferred.get("text_items", []) if isinstance(item, dict)]
        elif len(containers) == 1:
            fallback_container_id = containers[0].get("id")
            text_items = [
                {**item, "container_id": item.get("container_id") or fallback_container_id}
                for item in text_items
            ]
        visual_elements = [
            item for item in page.get("visual_element_inventory", []) if isinstance(item, dict)
        ]
        visual_elements.extend(_scene_graph_visual_elements(page.get("scene_graph")))
        workspace = build_container_workspace(
            page_number=page_number if isinstance(page_number, int) else None,
            containers=containers,
            text_items=text_items,
            stage="template",
            visual_elements=visual_elements,
        )
        if isinstance(page_number, int):
            write_container_workspace(
                workspace_dir / f"page_{page_number:03d}_container_workspace.json",
                workspace,
            )
        assignment = build_workspace_assignment(
            page_number=page_number if isinstance(page_number, int) else None,
            workspace=workspace,
            text_items=text_items,
            stage="template",
        )
        if isinstance(page_number, int):
            write_workspace_assignment(
                assignment_dir / f"page_{page_number:03d}_workspace_assignment.json",
                assignment,
            )
        pages.append(workspace)
        assignment_pages.append(assignment)
    error_count = sum(int(page.get("error_count", 0) or 0) for page in pages)
    aggregate = {
        "schema": "cyberppt.dual_image.container_workspace_set.v1",
        "stage": "template",
        "valid": bool(pages) and all(page.get("valid") for page in pages),
        "page_count": len(pages),
        "container_count": sum(int(page.get("container_count", 0) or 0) for page in pages),
        "slot_count": sum(int(page.get("slot_count", 0) or 0) for page in pages),
        "error_count": error_count,
        "pages": pages,
    }
    write_container_workspace(workspace_dir / "container_workspace_index.json", aggregate)
    assignment_error_count = sum(int(page.get("error_count", 0) or 0) for page in assignment_pages)
    assignment_aggregate = {
        "schema": "cyberppt.dual_image.workspace_assignment_set.v1",
        "stage": "template",
        "valid": bool(assignment_pages) and all(page.get("valid") for page in assignment_pages),
        "page_count": len(assignment_pages),
        "assignment_count": sum(int(page.get("assignment_count", 0) or 0) for page in assignment_pages),
        "error_count": assignment_error_count,
        "pages": assignment_pages,
    }
    write_workspace_assignment(assignment_dir / "workspace_assignment_index.json", assignment_aggregate)
    _write_json(
        structure_dir / "structure_inference_index.json",
        {
            "schema": "cyberppt.dual_image.structure_inference_set.v1",
            "valid": bool(structure_pages) and all(page.get("valid") for page in structure_pages),
            "page_count": len(structure_pages),
            "container_count": sum(int(page.get("container_count", 0) or 0) for page in structure_pages),
            "pages": structure_pages,
        },
    )
    return aggregate, assignment_aggregate


def run_vendor_rebuild(
    manifest_path: Path,
    *,
    ocr_backend: str,
    force_ocr: bool,
    timeout: int,
    export: bool,
    visible_image_variant: str = "background",
    editable_text_visibility: str = "visible",
    semantic_plan_dir: Path | None = None,
    visual_registry_dir: Path | None = None,
) -> None:
    command = [
        sys.executable,
        str(REBUILD_ENGINE),
        "rebuild",
        str(manifest_path),
        "--ocr-backend",
        ocr_backend,
        "--timeout",
        str(timeout),
        "--visible-image-variant",
        visible_image_variant,
        "--editable-text-visibility",
        editable_text_visibility,
    ]
    if semantic_plan_dir is not None:
        command.extend(["--semantic-plan-dir", str(semantic_plan_dir)])
    if visual_registry_dir is not None:
        command.extend(["--visual-registry-dir", str(visual_registry_dir)])
    if force_ocr:
        command.append("--force-ocr")
    if export:
        command.append("--export")
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not existing_pythonpath else f"{ROOT}{os.pathsep}{existing_pythonpath}"
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def build_template_rebuild_readiness(
    manifest_path: Path,
    *,
    export_requested: bool,
    visual_registry_dir: Path | None = None,
    semantic_plan_dir: Path | None = None,
    rendered_preview: Path | None = None,
    measurement_model: str = "pptx_render_preview_presence",
) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    project_path = resolve_project_path(manifest_path, manifest)
    analysis_dir = project_path / "analysis"
    rebuild_mode = _resolve_rebuild_mode(manifest)
    visual_reference_mode, visual_reference = _visual_reference_for_mode(
        project_path,
        manifest,
        rebuild_mode,
        manifest_path=manifest_path,
    )
    resolved_visual_registry_dir = discover_visual_registry_dir(project_path, visual_registry_dir)

    source_capture = build_source_capture(
        project_path,
        pair_manifest_path=manifest_path,
        visual_registry_dir=resolved_visual_registry_dir,
    )
    if rendered_preview is not None:
        source_capture = attach_render_delta_measurement(
            source_capture,
            rendered_preview=str(rendered_preview),
            measurement_model=measurement_model,
        )
    _write_json(analysis_dir / "source_capture.json", source_capture)
    source_capture_gate = build_source_capture_gate(source_capture)
    _write_json(analysis_dir / "source_capture_gate.json", source_capture_gate)
    container_workspace, workspace_assignment = _build_template_container_workspaces(project_path, source_capture)

    exported_pptx = _latest_pptx(project_path)
    template_gate = _template_gate(project_path, export_requested=export_requested, exported_pptx=exported_pptx)
    _write_json(analysis_dir / "template_gate.json", template_gate)
    scene_graph_gates = _load_scene_graph_gates(project_path)
    scene_graph_valid = bool(scene_graph_gates) and all(gate.get("valid") for gate in scene_graph_gates)
    visual_qa_gate = _load_visual_qa_gate(project_path)
    visual_qa_gate_valid = bool(visual_qa_gate and visual_qa_gate.get("valid"))
    page_number = None
    pairs = manifest.get("pairs")
    if isinstance(pairs, list) and pairs and isinstance(pairs[0], dict) and isinstance(pairs[0].get("page_number"), int):
        page_number = int(pairs[0]["page_number"])
    quality_artifacts = {
        "pair_manifest": str(manifest_path),
        "source_capture": str(analysis_dir / "source_capture.json"),
        "source_capture_gate": str(analysis_dir / "source_capture_gate.json"),
        "template_gate": str(analysis_dir / "template_gate.json"),
        "scene_graph_gates": str(analysis_dir / "scene_graph_gate"),
        "container_workspace": str(analysis_dir / "container_workspace"),
        "workspace_assignment": str(analysis_dir / "workspace_assignment"),
        "visual_reference": visual_reference,
        "rendered_preview": str(rendered_preview) if rendered_preview else None,
        "exported_pptx": exported_pptx,
        "visual_qa_gate": str(analysis_dir / "visual_qa_gate.json"),
    }
    quality_reports = {
        "pair_manifest": manifest,
        "source_capture": source_capture,
        "source_capture_gate": source_capture_gate,
        "template_gate": template_gate,
        "scene_graph_gates": scene_graph_gates,
        "container_workspace": container_workspace,
        "workspace_assignment": workspace_assignment,
        "visual_qa_gate": visual_qa_gate,
    }
    quality_extra = {
        "rebuild_mode": rebuild_mode,
        "visual_reference_mode": visual_reference_mode,
        "export_requested": export_requested,
    }
    preflight_gate = write_page_quality_report(
        analysis_dir / "preflight_gate.json",
        stage="preflight",
        page_number=page_number,
        project_path=project_path,
        artifacts=quality_artifacts,
        reports=quality_reports,
        extra=quality_extra,
        rules=_quality_rules(PREFLIGHT_RULES),
    )
    build_gate = write_page_quality_report(
        analysis_dir / "build_gate.json",
        stage="build",
        page_number=page_number,
        project_path=project_path,
        artifacts=quality_artifacts,
        reports=quality_reports,
        extra=quality_extra,
        rules=_quality_rules(BUILD_RULES),
    )
    postflight_gate = write_page_quality_report(
        analysis_dir / "postflight_gate.json",
        stage="postflight",
        page_number=page_number,
        project_path=project_path,
        artifacts=quality_artifacts,
        reports=quality_reports,
        extra=quality_extra,
        rules=_quality_rules(POSTFLIGHT_RULES),
    )
    page_quality_report = write_page_quality_report(
        analysis_dir / "page_quality_report.json",
        stage="template",
        page_number=page_number,
        project_path=project_path,
        artifacts=quality_artifacts,
        reports=quality_reports,
        extra=quality_extra,
    )

    valid = bool(
        preflight_gate["valid"]
        and build_gate["valid"]
        and postflight_gate["valid"]
        and page_quality_report["valid"]
    )
    if not preflight_gate["valid"]:
        status = "preflight_rework_required"
    elif not build_gate["valid"]:
        status = "build_rework_required"
    elif not postflight_gate["valid"]:
        status = "postflight_rework_required"
    elif not page_quality_report["valid"]:
        status = "page_quality_rework_required"
    else:
        status = "ready_for_delivery"

    readiness = {
        "schema": "cyberppt.dual_image.template_rebuild_readiness.v1",
        "valid": valid,
        "status": status,
        "project_path": str(project_path),
        "pair_manifest": str(manifest_path),
        "rebuild_mode": rebuild_mode,
        "visual_reference_mode": visual_reference_mode,
        "visual_registry_dir": str(resolved_visual_registry_dir) if resolved_visual_registry_dir else None,
        "semantic_plan_dir": str(semantic_plan_dir) if semantic_plan_dir else None,
        "rendered_preview": str(rendered_preview) if rendered_preview else None,
        "checks": {
            "template_rebuild_consumed": True,
            "preflight_gate_pass": bool(preflight_gate["valid"]),
            "build_gate_pass": bool(build_gate["valid"]),
            "postflight_gate_pass": bool(postflight_gate["valid"]),
            "template_gate_pass": bool(template_gate["valid"]),
            "source_capture_consumed": True,
            "source_capture_gate_pass": bool(source_capture_gate["valid"]),
            "scene_graph_gate_pass": scene_graph_valid,
            "scene_graph_gate_pages": len(scene_graph_gates),
            "visual_qa_gate_pass": visual_qa_gate_valid,
            "page_quality_report_pass": bool(page_quality_report["valid"]),
        },
        "template_gate": template_gate,
        "preflight_gate": preflight_gate,
        "build_gate": build_gate,
        "postflight_gate": postflight_gate,
        "source_capture_gate": source_capture_gate,
        "scene_graph_gates": scene_graph_gates,
        "artifacts": {
            "source_capture": str(analysis_dir / "source_capture.json"),
            "source_capture_gate": str(analysis_dir / "source_capture_gate.json"),
            "template_gate": str(analysis_dir / "template_gate.json"),
            "preflight_gate": str(analysis_dir / "preflight_gate.json"),
            "build_gate": str(analysis_dir / "build_gate.json"),
            "postflight_gate": str(analysis_dir / "postflight_gate.json"),
            "scene_graph_gate_dir": str(analysis_dir / "scene_graph_gate"),
            "container_workspace": str(analysis_dir / "container_workspace" / "container_workspace_index.json"),
            "workspace_assignment": str(analysis_dir / "workspace_assignment" / "workspace_assignment_index.json"),
            "exported_pptx": exported_pptx,
            "visual_reference": visual_reference,
            "visual_qa_gate": str(analysis_dir / "visual_qa_gate.json"),
            "page_quality_report": str(analysis_dir / "page_quality_report.json"),
        },
        "page_quality_report": page_quality_report,
    }
    _write_json(analysis_dir / "template_rebuild_readiness.json", readiness)
    return readiness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the vendored dual-image template rebuild, then consume source_capture as a CyberPPT gate."
    )
    parser.add_argument("manifest", type=Path, help="page_image_pairs.json")
    parser.add_argument("--ocr-backend", choices=("vision-json", "paddleocr-vl", "none"), default="vision-json")
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--visible-image-variant", choices=("background", "full"), default="background")
    parser.add_argument("--editable-text-visibility", choices=("visible", "hidden"), default="visible")
    parser.add_argument("--visual-registry-dir", type=Path)
    parser.add_argument("--semantic-plan-dir", type=Path)
    parser.add_argument("--rendered-preview", type=Path)
    parser.add_argument("--measurement-model", default="pptx_render_preview_presence")
    parser.add_argument("--export", action="store_true", default=True)
    parser.add_argument("--no-export", action="store_false", dest="export")
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Only consume existing template rebuild artifacts; intended for tests and resumed runs.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    manifest = _read_json(manifest_path)
    project_path = resolve_project_path(manifest_path, manifest)
    visual_registry_dir = discover_visual_registry_dir(
        project_path,
        args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
    )
    if not args.skip_rebuild:
        run_vendor_rebuild(
            manifest_path,
            ocr_backend=args.ocr_backend,
            force_ocr=args.force_ocr,
            timeout=args.timeout,
            export=args.export,
            visible_image_variant=args.visible_image_variant,
            editable_text_visibility=args.editable_text_visibility,
            semantic_plan_dir=args.semantic_plan_dir.resolve() if args.semantic_plan_dir else None,
            visual_registry_dir=visual_registry_dir,
        )
    readiness = build_template_rebuild_readiness(
        manifest_path,
        export_requested=args.export,
        visual_registry_dir=visual_registry_dir,
        semantic_plan_dir=args.semantic_plan_dir.resolve() if args.semantic_plan_dir else None,
        rendered_preview=args.rendered_preview.resolve() if args.rendered_preview else None,
        measurement_model=args.measurement_model,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2))
    return 0 if readiness["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
