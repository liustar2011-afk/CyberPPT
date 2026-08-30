from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from cyberppt.commands.init_project import init_project
from cyberppt.project_status import _production_stage_status, build_project_status


def test_production_status_preserves_pipeline_progress_states() -> None:
    assert _production_stage_status("production_ready") == "passed"
    assert _production_stage_status("image_assets_verified") == "pending"
    assert _production_stage_status("failed") == "failed"


def test_project_status_reports_missing_source_without_writing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    report = build_project_status(project)

    assert report["status"] == "in_progress"
    assert report["current_stage"] == "source"
    assert list(project.iterdir()) == []


def test_project_status_reports_initialized_profile(tmp_path: Path) -> None:
    project = tmp_path / "strict-project"
    init_project(project, profile="strict")

    report = build_project_status(project)

    assert report["profile"] == "strict"


def test_strict_status_ignores_stale_script_source_index(tmp_path: Path) -> None:
    project = tmp_path / "strict-project"
    init_project(project, profile="strict")
    script = project / "script"
    (script / "foundation.json").write_text(
        json.dumps({"sources": [], "facts": [], "concepts": [], "relations": [], "arguments": []}),
        encoding="utf-8",
    )
    cache = script / ".cache"
    cache.mkdir(exist_ok=True)
    (cache / "source-index.json").write_text(
        json.dumps({"schema": "cyberppt.source_index.v2", "sources": [], "source_structure": [], "units": []}),
        encoding="utf-8",
    )

    report = build_project_status(project)

    foundation = next(stage for stage in report["stages"] if stage["name"] == "foundation")
    assert "reading_strategy is required for script-profile Foundation" not in foundation["issues"]


def test_init_project_defaults_to_strict_profile(tmp_path: Path) -> None:
    project = tmp_path / "default-project"

    init_project(project)

    manifest = (project / "manifest.yml").read_text(encoding="utf-8")
    assert "profile: strict" in manifest
    assert "source_truth:" in manifest


def test_project_status_surfaces_live_handoff_failure(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source = project / "source"
    source.mkdir(parents=True)
    (source / "source.md").write_text("source", encoding="utf-8")
    script = project / "script"
    (script / "dist").mkdir(parents=True)
    foundation = {"sources": [], "facts": [], "concepts": [], "relations": [], "arguments": []}
    plan = {"communication_goal": "goal", "evidence_fit_review_mode": "strict", "chapters": [], "pages": []}
    final = {"deck": {"title": "deck"}, "slides": []}
    (script / "foundation.json").write_text(json.dumps(foundation), encoding="utf-8")
    (script / "deck-plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (script / "dist/final-script.json").write_text(json.dumps(final), encoding="utf-8")
    handoff = project / "workbench/stages/02-handoff/stage02-handoff.json"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("{}", encoding="utf-8")
    failed = {
        "status": "failed",
        "blocking_issues": [{"code": "HANDOFF_BINDING_MISSING"}],
        "warnings": [],
    }

    with (
        patch(
            "cyberppt.project_status._stage01",
            return_value=[{"name": "final_script", "status": "passed"}],
        ),
        patch("cyberppt.project_status.audit_stage02_handoff", return_value=failed),
    ):
        report = build_project_status(project)

    assert report["status"] == "blocked"
    assert report["current_stage"] == "stage02_handoff"
    handoff_stage = next(stage for stage in report["stages"] if stage["name"] == "stage02_handoff")
    assert handoff_stage["issues"][0]["code"] == "HANDOFF_BINDING_MISSING"
