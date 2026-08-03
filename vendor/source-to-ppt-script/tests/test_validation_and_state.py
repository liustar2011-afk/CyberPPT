from __future__ import annotations

from pathlib import Path

from ppt_compiler.state import all_status, lock_stage, stage_status
from ppt_compiler.utils import read_json, write_json
from ppt_compiler.validators import validate_stage


def test_complete_project_is_current(complete_project: Path) -> None:
    assert {item["status"] for item in all_status(complete_project)} == {"current"}


def test_upstream_change_invalidates_downstream(complete_project: Path, skill_root: Path) -> None:
    assets_path = complete_project / "stages/01_information_assets.json"
    assets = read_json(assets_path, {})
    assets["document"]["purpose"] += "（修订）"
    write_json(assets_path, assets)
    assert stage_status(complete_project, "assets")["status"] == "dirty"
    findings = validate_stage(skill_root, complete_project, "assets")
    assert not [f for f in findings if f.severity == "error"]
    lock_stage(complete_project, "assets")
    assert stage_status(complete_project, "assets")["status"] == "current"
    assert stage_status(complete_project, "plan")["status"] == "unlocked"
    assert stage_status(complete_project, "copy")["status"] == "unlocked"


def test_invalid_source_reference_is_error(complete_project: Path, skill_root: Path) -> None:
    assets_path = complete_project / "stages/01_information_assets.json"
    assets = read_json(assets_path, {})
    assets["assets"][0]["source_refs"] = ["D99-S99999"]
    write_json(assets_path, assets)
    findings = validate_stage(skill_root, complete_project, "assets")
    assert any(f.code == "INVALID_SOURCE_REF" and f.severity == "error" for f in findings)
