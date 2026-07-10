"""Project-scoped preparation and state reporting for the production workflow."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.commands.analysis_expression_gate import assert_analysis_expression_ready
from cyberppt.commands.blueprint_gate import (
    assert_blueprint_input_ready,
    assert_speaker_notes_review_ready,
    stage_speaker_notes_review,
)
from cyberppt.commands.final_script_pages import run_final_script_pages


STAGE_ROOT = Path("workbench/stages/02-blueprint-dual-image")
BLUEPRINT_APPROVAL = STAGE_ROOT / "blueprint_input.approved.json"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _project(project: Path) -> Path:
    return project.expanduser().resolve()


def _approved_blueprint_script(project: Path) -> Path:
    approval_path = project / BLUEPRINT_APPROVAL
    if not approval_path.is_file():
        raise ValueError("blueprint input approval is required")
    approval = _read_json(approval_path)
    script = Path(str(approval.get("artifact", ""))).expanduser().resolve()
    if not script.is_file():
        raise ValueError(f"approved blueprint input is missing: {script}")
    if _sha256(script) != approval.get("source_sha256"):
        raise ValueError("approved blueprint input changed; stage and approve blueprint input again")
    return script


def _prepare_path(project: Path, pages_raw: str) -> Path | None:
    for candidate in sorted((project / STAGE_ROOT).glob("*/production_prepare.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            payload = _read_json(candidate)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if payload.get("pages_raw") == pages_raw:
            return candidate
    return None


def _base_status(project: Path, pages_raw: str) -> dict[str, Any]:
    return {
        "schema": "cyberppt.production_status.v1",
        "project": str(project),
        "pages_raw": pages_raw,
        "gates": [],
        "artifacts": {},
        "failures": [],
    }


def prepare_production(project: Path, pages_raw: str) -> dict[str, Any]:
    """Compile approved production inputs and stop for speaker-notes review."""

    root = _project(project)
    assert_analysis_expression_ready(root)
    script = _approved_blueprint_script(root)
    style_lock = assert_blueprint_input_ready(root, script, None)
    prepared = run_final_script_pages(
        project=root,
        script=script,
        pages_raw=pages_raw,
        style_lock=style_lock,
        production_build=False,
    )
    notes_manifest = Path(str(prepared["artifacts"]["speaker_notes_manifest"])).resolve()
    if not notes_manifest.is_file():
        raise RuntimeError("speaker-notes manifest was not produced during preparation")
    pending = stage_speaker_notes_review(root, notes_manifest, pages_raw)
    output_dir = Path(str(prepared["artifacts"]["output_dir"])).resolve()
    prepare_path = _write_json(
        output_dir / "production_prepare.json",
        {
            "schema": "cyberppt.production_prepare.v1",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project": str(root),
            "pages_raw": pages_raw,
            "script": str(script),
            "script_sha256": _sha256(script),
            "visual_style_lock": str(style_lock),
            "template_text_lock": prepared["artifacts"]["template_text_lock"],
            "page_image_pairs": prepared["artifacts"]["page_image_pairs"],
            "speaker_notes_manifest": str(notes_manifest),
            "speaker_notes_pending_confirmation": str(pending),
            "resume_command": f"python3 -m cyberppt produce assemble {root} --pages {pages_raw}",
        },
    )
    return {
        "schema": "cyberppt.production_prepare_result.v1",
        "status": "production_inputs_prepared",
        "next_gate": "speaker_notes_approval_required",
        "next_command": f"approve-speaker-notes-review {root} --option-id confirm_speaker_notes",
        "pages": prepared["pages"],
        "artifacts": {
            **prepared["artifacts"],
            "speaker_notes_pending_confirmation": str(pending),
            "production_prepare": str(prepare_path),
        },
    }


def get_production_status(project: Path, pages_raw: str) -> dict[str, Any]:
    """Calculate the next legal production transition from current artifacts."""

    root = _project(project)
    result = _base_status(root, pages_raw)
    try:
        assert_analysis_expression_ready(root)
    except ValueError as exc:
        result.update(status="blocked", next_gate="analysis_approval_required", next_command="analysis-expression-status")
        result["failures"].append(str(exc))
        return result
    result["gates"].append("analysis_approved")

    try:
        script = _approved_blueprint_script(root)
        style_lock = assert_blueprint_input_ready(root, script, None)
    except ValueError as exc:
        result.update(status="blocked", next_gate="blueprint_input_approval_required", next_command="stage-blueprint-input")
        result["failures"].append(str(exc))
        return result
    result["gates"].extend(("visual_style_approved", "blueprint_input_approved"))
    result["artifacts"].update({"script": str(script), "visual_style_lock": str(style_lock)})

    prepare_path = _prepare_path(root, pages_raw)
    if prepare_path is None:
        result.update(
            status="blueprint_input_approved",
            next_gate="production_inputs_prepare_required",
            next_command=f"produce prepare {root} --pages {pages_raw}",
        )
        return result
    prepared = _read_json(prepare_path)
    if prepared.get("script_sha256") != _sha256(script):
        result.update(
            status="blueprint_input_approved",
            next_gate="production_inputs_prepare_required",
            next_command=f"produce prepare {root} --pages {pages_raw}",
        )
        result["failures"].append("prepared production inputs are stale")
        return result
    result["gates"].append("production_inputs_prepared")
    result["artifacts"].update(prepared)

    try:
        notes_manifest = assert_speaker_notes_review_ready(root, pages_raw)
    except ValueError as exc:
        result.update(
            status="production_inputs_prepared",
            next_gate="speaker_notes_approval_required",
            next_command=f"approve-speaker-notes-review {root} --option-id confirm_speaker_notes",
        )
        result["failures"].append(str(exc))
        return result
    result["gates"].append("speaker_notes_approved")
    result["artifacts"]["speaker_notes_manifest"] = str(notes_manifest)
    result.update(
        status="speaker_notes_approved",
        next_gate="blueprint_images_approval_required",
        next_command=f"stage-blueprint-image-review {root} --manifest {prepared['page_image_pairs']}",
    )
    return result
