"""Run repository-local compatibility scripts from the product CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cyberppt.paths import SCRIPTS_DIR


SCRIPT_ALIASES: dict[str, str] = {
    "build-visual-qa": "build_visual_qa_gate.py",
    "body-blueprint-prompts": "body_blueprint_prompt.py",
    "clean-stage": "dual_image_overlay/clean_stage.py",
    "compare-merged-render": "compare_merged_render.py",
    "compare-render": "compare_render.py",
    "component-signature": "build_component_signature.py",
    "inspect": "inspect_pptx_objects.py",
    "image-ppt": "dual_image_overlay/rebuild_engine/template_image_ppt_export.py",
    "lock-content": "build_content_lock.py",
    "measure-blueprint": "measure_blueprint.py",
    "merge-pages": "merge_verified_pages.py",
    "pair-manifest": "dual_image_overlay/cyberppt_pair_manifest.py",
    "rework-report": "build_rework_report.py",
    "source-capture": "dual_image_overlay/source_capture.py",
    "template-rebuild": "dual_image_overlay/template_rebuild.py",
    "validate": "validate_pptx.py",
}


def script_path(script_name: str) -> Path:
    if script_name not in SCRIPT_ALIASES:
        raise KeyError(f"unknown CyberPPT script alias: {script_name}")
    path = SCRIPTS_DIR / SCRIPT_ALIASES[script_name]
    if not path.exists():
        raise FileNotFoundError(f"script not found: {path}")
    return path


def run_script(script_name: str, args: list[str]) -> int:
    path = script_path(script_name)
    completed = subprocess.run([sys.executable, str(path), *args], check=False)
    return int(completed.returncode)
