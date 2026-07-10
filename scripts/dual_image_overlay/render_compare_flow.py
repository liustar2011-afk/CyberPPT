from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MODEL = "compare_render_crop_mean_abs_diff_v1"


def visual_registry_path_for_page(registry_dir: Path | None, page_number: int) -> Path | None:
    if registry_dir is None:
        return None
    candidates = [
        registry_dir / f"page_{page_number:03d}_visual_element_registry.json",
        registry_dir / f"slide-{page_number:02d}-visual-element-registry.json",
        registry_dir / f"page_{page_number:03d}" / "visual_element_registry.json",
        registry_dir / f"page-{page_number:03d}" / "visual_element_registry.json",
    ]
    return next((path for path in candidates if path.is_file()), None)


def attach_render_compare_measurement(
    source_capture: dict[str, Any],
    *,
    rendered_preview: str,
    render_compare: dict[str, Any],
) -> dict[str, Any]:
    status = "measured" if render_compare.get("passed") else "failed"
    source_capture["render_delta_measurement"] = {
        "status": status,
        "rendered_preview": rendered_preview,
        "model": MODEL,
        "render_compare": render_compare.get("report_path"),
        "measured_registry_dir": render_compare.get("measured_registry_dir"),
    }
    source_capture.setdefault("capture_policy", {})["render_delta_measurement_model"] = MODEL
    return source_capture


def run_render_compare_for_page(
    *,
    blueprint: Path,
    rendered: Path,
    registry_dir: Path | None,
    page_number: int,
    analysis_dir: Path,
) -> dict[str, Any]:
    registry = visual_registry_path_for_page(registry_dir, page_number)
    if registry is None:
        return {
            "available": False,
            "skipped": True,
            "reason": "visual_registry_missing",
            "page_number": page_number,
        }

    report = analysis_dir / f"page_{page_number:03d}_render_compare.json"
    measured_registry_dir = analysis_dir / "visual_registry_measured"
    measured_registry = measured_registry_dir / f"page_{page_number:03d}_visual_element_registry.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "compare_render.py"),
        "--blueprint",
        str(blueprint),
        "--render",
        str(rendered),
        "--registry",
        str(registry),
        "--out",
        str(report),
        "--measured-registry-out",
        str(measured_registry),
    ]
    completed = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    payload: dict[str, Any] = {}
    if report.is_file():
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    return {
        "available": True,
        "skipped": False,
        "page_number": page_number,
        "returncode": completed.returncode,
        "passed": bool(payload.get("passed")),
        "report_path": str(report),
        "registry_path": str(registry),
        "measured_registry_dir": str(measured_registry_dir) if measured_registry.is_file() else None,
        "measured_registry_path": str(measured_registry) if measured_registry.is_file() else None,
        "stderr": completed.stderr,
    }
