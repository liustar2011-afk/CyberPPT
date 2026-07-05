from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.dual_image_overlay"

from .rebuild_modes import resolve_rebuild_mode as _resolve_rebuild_mode
from .rebuild_modes import visual_reference_for_mode as _visual_reference_for_mode
from .source_capture import attach_render_delta_measurement, build_source_capture, build_source_capture_gate


ROOT = Path(__file__).resolve().parents[2]
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
    subprocess.run(command, cwd=ROOT, check=True)


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

    source_capture = build_source_capture(
        project_path,
        pair_manifest_path=manifest_path,
        visual_registry_dir=visual_registry_dir,
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

    exported_pptx = _latest_pptx(project_path)
    template_gate = _template_gate(project_path, export_requested=export_requested, exported_pptx=exported_pptx)
    _write_json(analysis_dir / "template_gate.json", template_gate)
    scene_graph_gates = _load_scene_graph_gates(project_path)
    scene_graph_valid = bool(scene_graph_gates) and all(gate.get("valid") for gate in scene_graph_gates)

    valid = bool(template_gate["valid"] and source_capture_gate["valid"] and scene_graph_valid)
    if not template_gate["valid"]:
        status = "template_rebuild_required"
    elif not scene_graph_valid:
        status = "scene_graph_rework_required"
    elif not source_capture_gate["valid"]:
        status = "source_capture_rework_required"
    else:
        status = "ready_for_visual_qa"

    readiness = {
        "schema": "cyberppt.dual_image.template_rebuild_readiness.v1",
        "valid": valid,
        "status": status,
        "project_path": str(project_path),
        "pair_manifest": str(manifest_path),
        "rebuild_mode": rebuild_mode,
        "visual_reference_mode": visual_reference_mode,
        "visual_registry_dir": str(visual_registry_dir) if visual_registry_dir else None,
        "semantic_plan_dir": str(semantic_plan_dir) if semantic_plan_dir else None,
        "rendered_preview": str(rendered_preview) if rendered_preview else None,
        "checks": {
            "template_rebuild_consumed": True,
            "template_gate_pass": bool(template_gate["valid"]),
            "source_capture_consumed": True,
            "source_capture_gate_pass": bool(source_capture_gate["valid"]),
            "scene_graph_gate_pass": scene_graph_valid,
            "scene_graph_gate_pages": len(scene_graph_gates),
        },
        "template_gate": template_gate,
        "source_capture_gate": source_capture_gate,
        "scene_graph_gates": scene_graph_gates,
        "artifacts": {
            "source_capture": str(analysis_dir / "source_capture.json"),
            "source_capture_gate": str(analysis_dir / "source_capture_gate.json"),
            "template_gate": str(analysis_dir / "template_gate.json"),
            "scene_graph_gate_dir": str(analysis_dir / "scene_graph_gate"),
            "exported_pptx": exported_pptx,
            "visual_reference": visual_reference,
        },
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
            visual_registry_dir=args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
        )
    readiness = build_template_rebuild_readiness(
        manifest_path,
        export_requested=args.export,
        visual_registry_dir=args.visual_registry_dir.resolve() if args.visual_registry_dir else None,
        semantic_plan_dir=args.semantic_plan_dir.resolve() if args.semantic_plan_dir else None,
        rendered_preview=args.rendered_preview.resolve() if args.rendered_preview else None,
        measurement_model=args.measurement_model,
    )
    print(json.dumps(readiness, ensure_ascii=False, indent=2))
    return 0 if readiness["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
