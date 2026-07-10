"""Run repository-local compatibility scripts from the product CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import assert_analysis_expression_ready
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
    "speaker-notes": "speaker_notes.py",
    "template-rebuild": "dual_image_overlay/template_rebuild.py",
    "validate": "validate_pptx.py",
}

_STAGE_2_PLUS_GENERATION_ALIASES = frozenset(
    {"body-blueprint-prompts", "image-ppt", "pair-manifest", "source-capture", "speaker-notes", "template-rebuild"}
)
_PROJECT_OPTION_NAMES = ("--project", "--project-path", "--project-dir", "--project-root")


def script_path(script_name: str) -> Path:
    if script_name not in SCRIPT_ALIASES:
        raise KeyError(f"unknown CyberPPT script alias: {script_name}")
    path = SCRIPTS_DIR / SCRIPT_ALIASES[script_name]
    if not path.exists():
        raise FileNotFoundError(f"script not found: {path}")
    return path


def run_script(script_name: str, args: list[str]) -> int:
    _assert_generation_alias_ready(script_name, args)
    path = script_path(script_name)
    completed = subprocess.run([sys.executable, str(path), *args], check=False)
    return int(completed.returncode)


def _assert_generation_alias_ready(script_name: str, args: list[str]) -> None:
    if script_name not in _STAGE_2_PLUS_GENERATION_ALIASES:
        return
    for candidate in _generation_project_candidates(script_name, args):
        if (candidate / "workbench" / "analysis_expression" / "contract.json").exists():
            assert_analysis_expression_ready(candidate)


def _generation_project_candidates(script_name: str, args: list[str]) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for index, arg in enumerate(args[:-1]):
        if arg in _PROJECT_OPTION_NAMES:
            candidates.append(Path(args[index + 1]).expanduser().resolve())
    for arg in args:
        option, separator, value = arg.partition("=")
        if separator and option in _PROJECT_OPTION_NAMES:
            candidates.append(Path(value).expanduser().resolve())
    if script_name == "source-capture" and args and not args[0].startswith("-"):
        candidates.append(Path(args[0]).expanduser().resolve())
    for arg in args:
        if arg.startswith("-"):
            continue
        path = Path(arg).expanduser()
        if path.exists():
            resolved = path.resolve()
            candidates.extend(
                parent
                for parent in (resolved, *resolved.parents)
                if (parent / "workbench" / "analysis_expression" / "contract.json").exists()
            )
    return tuple(dict.fromkeys(candidates))
