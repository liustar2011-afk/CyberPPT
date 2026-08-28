from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cyberppt.stage02_handoff import HANDOFF_JSON, audit_stage02_handoff
from cyberppt.visual_stage.persistence import VISUAL_FILES
from script_engine.analysis_audit import audit_deck_plan, audit_final_script, audit_foundation_analysis
from script_engine.contracts import (
    check_full_copy_duplication,
    check_onscreen_detail_length,
    check_onscreen_structure,
    check_onscreen_terminal_punctuation,
    check_speaker_notes_length,
    lint_final_script,
    validate_deck_plan,
    validate_final_script,
    validate_foundation,
)
from script_engine.delivery_cleanliness import check_delivery_cleanliness
from script_engine.render import render_stage02_markdown


STYLE_LOCK = Path("workbench/locks/visual_style_lock.json")
IMAGEGEN_ROOT = Path("workbench/stages/02-imagegen")
PRODUCTION_COMPLETE_STATUSES = {
    "production_ready",
    "passed",
    "completed",
    "ready",
    "delivery_ready",
}
PRODUCTION_PENDING_STATUSES = {
    "blueprint_created",
    "image_assets_generated",
    "ready_for_image_generation",
    "image_assets_verified",
    "rendered_pending_visual_review",
    "in_progress",
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _stage(name: str, status: str, **details: Any) -> dict[str, Any]:
    return {"name": name, "status": status, **details}


def _production_stage_status(status: str) -> str:
    if status in PRODUCTION_COMPLETE_STATUSES:
        return "passed"
    if status in PRODUCTION_PENDING_STATUSES:
        return "pending"
    return "failed"


def _stage01(project: Path) -> list[dict[str, Any]]:
    source_dir = project / "source"
    sources = sorted(
        path.name
        for path in source_dir.glob("*")
        if path.is_file() and path.name != ".gitkeep"
    ) if source_dir.is_dir() else []
    stages = [_stage("source", "passed" if sources else "pending", files=sources)]
    foundation_path = project / "script/foundation.json"
    plan_path = project / "script/deck-plan.json"
    final_path = project / "script/dist/final-script.json"

    if not foundation_path.is_file():
        return stages + [_stage("foundation", "pending", path=str(foundation_path))]
    try:
        foundation = _read_json(foundation_path)
        issues = validate_foundation(foundation)
        semantic_issues, semantic_warnings = audit_foundation_analysis(foundation)
        issues = [*issues, *semantic_issues]
        stages.append(_stage("foundation", "failed" if issues else "passed", path=str(foundation_path), issues=issues, warnings=semantic_warnings))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stages + [_stage("foundation", "failed", path=str(foundation_path), issues=[str(exc)])]
    if issues:
        return stages

    if not plan_path.is_file():
        return stages + [_stage("plan", "pending", path=str(plan_path))]
    try:
        plan = _read_json(plan_path)
        issues = validate_deck_plan(plan)
        semantic_issues, semantic_warnings = audit_deck_plan(plan, foundation)
        issues = [*issues, *semantic_issues]
        stages.append(_stage("plan", "failed" if issues else "passed", path=str(plan_path), issues=issues, warnings=semantic_warnings))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stages + [_stage("plan", "failed", path=str(plan_path), issues=[str(exc)])]
    if issues:
        return stages

    if not final_path.is_file():
        return stages + [_stage("final_script", "pending", path=str(final_path))]
    try:
        final = _read_json(final_path)
        issues = validate_final_script(final)
        markdown = render_stage02_markdown(final)
        issues.extend(lint_final_script(final))
        issues.extend(check_onscreen_structure(final))
        issues.extend(check_full_copy_duplication(final))
        issues.extend(check_speaker_notes_length(final))
        issues.extend(check_delivery_cleanliness(markdown))
        issues.extend(check_onscreen_terminal_punctuation(final))
        issues.extend(check_onscreen_detail_length(final))
        semantic_issues, semantic_warnings = audit_final_script(final, plan, foundation)
        issues.extend(semantic_issues)
        stages.append(_stage("final_script", "failed" if issues else "passed", path=str(final_path), issues=issues, warnings=semantic_warnings))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stages.append(_stage("final_script", "failed", path=str(final_path), issues=[str(exc)]))
    return stages


def _stage02(project: Path) -> list[dict[str, Any]]:
    handoff_path = project / HANDOFF_JSON
    if not handoff_path.is_file():
        return [_stage("stage02_handoff", "pending", path=str(handoff_path))]
    try:
        handoff = audit_stage02_handoff(project)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [_stage("stage02_handoff", "failed", path=str(handoff_path), issues=[str(exc)])]
    stages = [_stage(
        "stage02_handoff",
        "passed" if handoff.get("status") == "passed" else "failed",
        path=str(handoff_path),
        issues=handoff.get("blocking_issues", []),
        warnings=handoff.get("warnings", []),
    )]
    if stages[-1]["status"] == "failed":
        return stages

    visual_report_path = project / VISUAL_FILES["validation"]
    required_visual = [
        project / VISUAL_FILES[key]
        for key in ("decisions", "execution_receipt", "spec_json", "spec_markdown", "validation")
    ]
    missing_visual = [str(path) for path in required_visual if not path.is_file()]
    if missing_visual:
        return stages + [_stage("visual_structure", "pending", missing=missing_visual)]
    try:
        visual_report = _read_json(visual_report_path)
        visual_status = "passed" if visual_report.get("status") == "passed" else "failed"
        stages.append(_stage("visual_structure", visual_status, path=str(visual_report_path)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stages + [_stage("visual_structure", "failed", path=str(visual_report_path), issues=[str(exc)])]
    if stages[-1]["status"] == "failed":
        return stages

    style_path = project / STYLE_LOCK
    if not style_path.is_file():
        return stages + [_stage("style_lock", "pending", path=str(style_path))]
    try:
        style = _read_json(style_path)
        style_status = "passed" if style.get("schema") == "cyberppt.visual_style_lock.v1" else "failed"
        stages.append(_stage("style_lock", style_status, path=str(style_path)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return stages + [_stage("style_lock", "failed", path=str(style_path), issues=[str(exc)])]
    if stages[-1]["status"] == "failed":
        return stages

    imagegen_root = project / IMAGEGEN_ROOT
    summaries = sorted(
        imagegen_root.rglob("*_final_script_pages_run.json") if imagegen_root.is_dir() else [],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not summaries:
        return stages + [_stage("stage02_production", "pending", path=str(imagegen_root))]
    latest = summaries[0]
    try:
        summary = _read_json(latest)
        production_status = str(summary.get("status") or "unknown")
        stages.append(_stage(
            "stage02_production",
            _production_stage_status(production_status),
            path=str(latest),
            production_status=production_status,
        ))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stages.append(_stage("stage02_production", "failed", path=str(latest), issues=[str(exc)]))
    return stages


def build_project_status(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    stages = _stage01(project)
    if stages and stages[-1]["status"] == "passed" and stages[-1]["name"] == "final_script":
        stages.extend(_stage02(project))
    blocker = next((stage for stage in stages if stage["status"] == "failed"), None)
    pending = next((stage for stage in stages if stage["status"] == "pending"), None)
    if blocker:
        status, current = "blocked", blocker["name"]
    elif pending:
        status, current = "in_progress", pending["name"]
    else:
        status = "complete"
        current = stages[-1]["name"] if stages else "source"
    return {
        "schema": "cyberppt.project_status.v1",
        "project": str(project),
        "status": status,
        "current_stage": current,
        "stages": stages,
    }


__all__ = ["build_project_status"]
