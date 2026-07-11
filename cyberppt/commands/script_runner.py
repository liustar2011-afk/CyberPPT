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
    "speaker-notes": "speaker_notes.py",
    "validate": "validate_pptx.py",
}

_STAGE_2_PLUS_GENERATION_ALIASES = frozenset(
    {"body-blueprint-prompts", "image-ppt", "pair-manifest", "speaker-notes"}
)
_PROJECT_CONTEXT_ERROR = "production-capable aliases require exactly one --project <path>"


def script_path(script_name: str) -> Path:
    if script_name not in SCRIPT_ALIASES:
        raise KeyError(f"unknown CyberPPT script alias: {script_name}")
    path = SCRIPTS_DIR / SCRIPT_ALIASES[script_name]
    if not path.exists():
        raise FileNotFoundError(f"script not found: {path}")
    return path


def run_script(script_name: str, args: list[str]) -> int:
    forwarded_args = _assert_generation_alias_ready(script_name, args)
    path = script_path(script_name)
    completed = subprocess.run([sys.executable, str(path), *forwarded_args], check=False)
    return int(completed.returncode)


def generation_project(args: list[str]) -> Path:
    values = _option_values(args, "--project")
    if len(values) != 1:
        raise ValueError(_PROJECT_CONTEXT_ERROR)
    project = Path(values[0]).expanduser().resolve()
    contract = project / "workbench" / "analysis_expression" / "contract.json"
    if not contract.is_file():
        raise ValueError(f"CyberPPT project contract not found: {contract}")
    return project


def _assert_generation_alias_ready(script_name: str, args: list[str]) -> list[str]:
    if script_name not in _STAGE_2_PLUS_GENERATION_ALIASES:
        return args
    project = generation_project(args)
    assert_analysis_expression_ready(project)
    return _without_option(args, "--project")


def _option_values(args: list[str], option: str) -> list[str]:
    values: list[str] = []
    equals_option = f"{option}="
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == option:
            if index + 1 >= len(args) or args[index + 1].startswith("-"):
                raise ValueError(_PROJECT_CONTEXT_ERROR)
            values.append(args[index + 1])
            index += 2
            continue
        if arg.startswith(equals_option):
            value = arg.removeprefix(equals_option)
            if not value:
                raise ValueError(_PROJECT_CONTEXT_ERROR)
            values.append(value)
        index += 1
    return values


def _without_option(args: list[str], option: str) -> list[str]:
    forwarded: list[str] = []
    index = 0
    while index < len(args):
        if args[index] == option:
            index += 2
            continue
        if args[index].startswith(f"{option}="):
            index += 1
            continue
        forwarded.append(args[index])
        index += 1
    return forwarded
