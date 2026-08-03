from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ppt_compiler.extractors import initialise_project
from ppt_compiler.state import lock_stage
from ppt_compiler.validators import validate_stage


@pytest.fixture
def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def complete_project(tmp_path: Path, skill_root: Path) -> Path:
    project = tmp_path / "demo_project"
    source = skill_root / "references/examples/source_sample.md"
    profile = skill_root / "assets/profiles/cec_leadership.yaml"
    initialise_project([source], project, profile)
    stages = [
        ("information_assets.sample.json", "stages/01_information_assets.json", "assets"),
        ("page_plan.sample.json", "stages/02_page_plan.json", "plan"),
        ("screen_copy.sample.json", "stages/03_screen_copy.json", "copy"),
        ("visual_plan.sample.json", "stages/04_visual_plan.json", "visual"),
        ("semantic_audit.sample.json", "stages/05_semantic_audit.json", "audit"),
    ]
    for sample, destination, stage in stages:
        shutil.copy2(skill_root / "references/examples" / sample, project / destination)
        findings = validate_stage(skill_root, project, stage)
        assert not [f for f in findings if f.severity == "error"]
        lock_stage(project, stage)
    return project
