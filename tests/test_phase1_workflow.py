from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cyberppt.commands.init_project import init_project
from cyberppt.phase1 import workflow
from cyberppt.phase1.artifacts import phase1_paths, sha256_file


VALID_SOURCE_ANALYSIS_JSON = json.dumps(
    {
        "material_type": "工作方案",
        "reporting_task": "领导审定",
        "audience": "分管领导",
        "evidence": [
            {
                "claim": "供需总体平衡",
                "verbatim_support": "供需总体平衡",
                "source_unit_ids": ["U0001"],
                "numbers": [],
                "confidence": "high",
                "caveat": "未提供计算底表",
                "meaning": "说明当前判断",
                "visual": "结论框",
            }
        ],
        "storylines": [],
        "material_pool": [],
        "confirmation_questions": ["是否确认首期范围？"],
    },
    ensure_ascii=False,
)


def prepare_fixture_project(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project"
    init_project(project)
    source = project / "workbench/stages/01-analysis/source_extract.md"
    source.write_text("## P1\n供需总体平衡\n", encoding="utf-8")
    return project, source


def test_prepare_writes_reviewable_prompt_without_calling_model(tmp_path: Path, monkeypatch) -> None:
    project, source = prepare_fixture_project(tmp_path)
    called = Mock(side_effect=AssertionError("prepare must not call the model"))
    monkeypatch.setattr(workflow, "run_codex_text", called)

    result = workflow.prepare_phase1_prompt(project, "source_analysis", source)

    paths = phase1_paths(project, "source_analysis")
    assert result["status"] == "prompt_ready"
    assert paths.prompt.exists()
    assert paths.source_bundle_json.exists()
    assert json.loads(paths.run_manifest.read_text(encoding="utf-8"))["status"] == "prompt_ready"
    called.assert_not_called()


def test_generate_consumes_edited_prompt_without_overwriting_it(tmp_path: Path, monkeypatch) -> None:
    project, source = prepare_fixture_project(tmp_path)
    prepared = workflow.prepare_phase1_prompt(project, "source_analysis", source)
    prompt = Path(prepared["prompt"])
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\n人工补充约束。\n", encoding="utf-8")
    monkeypatch.setattr(workflow, "run_codex_text", lambda **kwargs: VALID_SOURCE_ANALYSIS_JSON)

    generated = workflow.generate_phase1_candidate(project, "source_analysis", model="test-model")

    assert generated["status"] == "candidate_ready"
    assert "人工补充约束" in prompt.read_text(encoding="utf-8")
    assert generated["prompt_sha256"] == sha256_file(prompt)
    assert Path(generated["candidate"]).exists()
    assert Path(generated["raw_output"]).read_text(encoding="utf-8").strip() == VALID_SOURCE_ANALYSIS_JSON


def test_model_failure_preserves_prompt_and_writes_resumable_run(tmp_path: Path, monkeypatch) -> None:
    project, source = prepare_fixture_project(tmp_path)
    workflow.prepare_phase1_prompt(project, "source_analysis", source)
    monkeypatch.setattr(workflow, "run_codex_text", Mock(side_effect=RuntimeError("SSL EOF")))

    with pytest.raises(RuntimeError, match="SSL EOF"):
        workflow.generate_phase1_candidate(project, "source_analysis")

    paths = phase1_paths(project, "source_analysis")
    run = json.loads(paths.run_manifest.read_text(encoding="utf-8"))
    assert run["status"] == "model_failed"
    assert run["error"] == "SSL EOF"
    assert run["resume_command"].startswith("python3 -m cyberppt phase1 generate")
    assert paths.prompt.exists()


def test_generate_rejects_stale_source_dependency(tmp_path: Path, monkeypatch) -> None:
    project, source = prepare_fixture_project(tmp_path)
    workflow.prepare_phase1_prompt(project, "source_analysis", source)
    source.write_text("## P1\n源材料已被修改。\n", encoding="utf-8")
    monkeypatch.setattr(workflow, "run_codex_text", Mock(return_value=VALID_SOURCE_ANALYSIS_JSON))

    with pytest.raises(ValueError, match="dependency is stale"):
        workflow.generate_phase1_candidate(project, "source_analysis")
