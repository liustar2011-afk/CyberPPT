"""Fuse CyberPPT scene/asset gates with the PPT Master SVG quality checker."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from ..ppt_master_runtime_bridge import resolve_shared_resource
from ..standalone_runtime import check_standalone_runtime
from .image_assets import validate_image_asset_contract
from .page_svg_ir import validate_page_svg_ir


QA_FUSION_SCHEMA = "cyberppt.dual_image.ppt_master_qa_fusion.v1"


def run_ppt_master_svg_checker(svg_path: str | Path, *, expected_format: str | None = None) -> dict[str, Any]:
    """Run the selected PPT Master checker and normalize its result shape."""
    path = Path(svg_path)
    checker_path = resolve_shared_resource("svg_quality_checker")
    if checker_path is None:
        return {"status": "unavailable", "passed": False, "blocking": True, "reason": "svg_quality_checker_not_resolved"}
    module_name = "_cyberppt_ppt_master_svg_quality_checker"
    module = sys.modules.get(module_name)
    if module is None:
        if str(checker_path.parent) not in sys.path:
            sys.path.insert(0, str(checker_path.parent))
        spec = importlib.util.spec_from_file_location(module_name, checker_path)
        if spec is None or spec.loader is None:
            return {"status": "unavailable", "passed": False, "blocking": True, "reason": "checker_module_load_failed"}
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001 - normalized into QA evidence
            sys.modules.pop(module_name, None)
            return {"status": "error", "passed": False, "blocking": True, "reason": str(exc)}
    try:
        checker = module.SVGQualityChecker()
        result = checker.check_file(str(path), expected_format=expected_format)
        return {"status": "checked", "passed": bool(result.get("passed")), "blocking": not bool(result.get("passed")), "checker_path": str(checker_path), "result": result}
    except Exception as exc:  # noqa: BLE001 - checker must not crash the pipeline
        return {"status": "error", "passed": False, "blocking": True, "checker_path": str(checker_path), "reason": str(exc)}


def build_qa_fusion_report(
    *,
    scene_graph_gate: Mapping[str, Any],
    page_svg_ir: Mapping[str, Any],
    image_assets: Mapping[str, Any] | None = None,
    svg_path: str | Path | None = None,
    expected_format: str | None = None,
    require_ppt_master: bool = False,
    copy_edit_report: Mapping[str, Any] | None = None,
    constrained_reflow_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create one blocking report for both CyberPPT and PPT Master QA layers."""
    ir_gate = page_svg_ir.get("page_svg_ir_gate") or validate_page_svg_ir(page_svg_ir)
    asset_gate = (image_assets or page_svg_ir.get("image_assets") or {}).get("gate") if isinstance(image_assets or page_svg_ir.get("image_assets"), Mapping) else None
    asset_gate = asset_gate or validate_image_asset_contract({})
    if svg_path:
        ppt_master = run_ppt_master_svg_checker(svg_path, expected_format=expected_format)
    else:
        ppt_master = {"status": "deferred", "passed": not require_ppt_master, "blocking": bool(require_ppt_master), "reason": "svg_path_not_provided"}
    components = {
        "standalone_runtime": check_standalone_runtime(),
        "scene_graph": dict(scene_graph_gate),
        "page_svg_ir": dict(ir_gate),
        "image_assets": dict(asset_gate),
        "ppt_master_svg": ppt_master,
    }
    if copy_edit_report is not None:
        components["semantic_copy_edit"] = dict(copy_edit_report)
    if constrained_reflow_report is not None:
        components["recognized_constrained_reflow"] = dict(constrained_reflow_report)
    blocking = []
    for name, report in components.items():
        if not bool(report.get("valid", report.get("passed", False))):
            blocking.append({"component": name, "status": report.get("status", "failed"), "reason": report.get("reason")})
    return {
        "schema": QA_FUSION_SCHEMA,
        "valid": not blocking,
        "status": "passed" if not blocking else "blocked",
        "blocking_count": len(blocking),
        "blocking_errors": blocking,
        "components": components,
        "policy": {"all_components_required": True, "require_ppt_master": require_ppt_master, "deferred_checker_is_non_blocking": not require_ppt_master},
    }


def write_qa_fusion_report(path: str | Path, **kwargs: Any) -> dict[str, Any]:
    report = build_qa_fusion_report(**kwargs)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
