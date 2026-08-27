"""Compatibility facade for the modular Stage 02 visual-structure pipeline."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from cyberppt.visual_stage import audit as _audit
from cyberppt.visual_stage import execution as _execution
from cyberppt.visual_stage import prompt_gate as _prompt_gate
from cyberppt.visual_stage.compiler import (
    ALLOWED_TOPOLOGY,
    _DEFAULT_FORBIDDEN_STRUCTURES,
    _DIRECTION_MAP,
    _FORBIDDEN_STRUCTURES_BY_TOPOLOGY,
    _UNIVERSAL_FORBIDDEN_STRUCTURES,
    _build_executable_page,
    _decision_execution_design,
    _expression_contract,
    _fail,
    _page_id,
    _quality_contract,
    _render_business_relationships,
    _render_visual_structure_markdown,
    compile_visual_spec,
)
from cyberppt.visual_stage.persistence import (
    SKILL_RELATIVE,
    VISUAL_FILES,
    _read_json,
    _register_visual_artifacts,
    _sha256,
    _spec_content_sha256,
    _utc_now,
    write_json,
)


# Kept as facade-level patch points because existing regression tests and a few
# external callers patch these private names directly.
_skill_root = _execution._skill_root


def _sync_legacy_patch_points() -> None:
    _execution._skill_root = _skill_root
    _audit._skill_root = _skill_root
    _prompt_gate._skill_root = _skill_root


def _write_visual_design_input(project: Path, handoff: Path) -> Path:
    _sync_legacy_patch_points()
    return _execution._write_visual_design_input(project, handoff)


def visual_structure_required(project: Path) -> bool:
    _sync_legacy_patch_points()
    return _execution.visual_structure_required(project)


def _write_skill_request(project: Path, script: Path, design_input: Path) -> Path:
    _sync_legacy_patch_points()
    return _execution._write_skill_request(project, script, design_input)


def prepare_visual_structure_stage(
    project: Path,
    script: Path,
    *,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
) -> Path:
    _sync_legacy_patch_points()
    return _execution.prepare_visual_structure_stage(
        project,
        script,
        lightweight_stage01_confirmed=lightweight_stage01_confirmed,
        reuse_current_handoff=reuse_current_handoff,
    )


def execute_visual_structure_stage(project: Path, script: Path) -> dict[str, Path]:
    _sync_legacy_patch_points()
    return _execution.execute_visual_structure_stage(project, script)


def record_visual_structure_execution(
    project: Path,
    script: Path,
    *,
    executor: str,
    model: str,
    note: str = "",
) -> Path:
    _sync_legacy_patch_points()
    return _execution.record_visual_structure_execution(
        project,
        script,
        executor=executor,
        model=model,
        note=note,
    )


def _audit_execution_receipt(project: Path, script: Path, skill_root: Path) -> dict[str, Any]:
    _sync_legacy_patch_points()
    return _execution._audit_execution_receipt(project, script, skill_root)


def _prompt_inputs_sha256(project: Path, script: Path, skill_root: Path) -> dict[str, str]:
    _sync_legacy_patch_points()
    return _prompt_gate._prompt_inputs_sha256(project, script, skill_root)


def _render_visual_review_summary(
    spec: dict[str, Any], decisions: dict[str, Any], validation: dict[str, Any]
) -> str:
    return _audit._render_visual_review_summary(spec, decisions, validation)


def run_visual_structure_audit(project: Path, script: Path) -> tuple[int, dict[str, Any]]:
    _sync_legacy_patch_points()
    return _audit.run_visual_structure_audit(project, script)


def assert_visual_structure_ready(project: Path, script: Path) -> Path | None:
    _sync_legacy_patch_points()
    return _prompt_gate.assert_visual_structure_ready(project, script)
