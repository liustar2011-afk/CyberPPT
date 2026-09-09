from pathlib import Path

import pytest

from cyberppt.visual_stage.compiler import _selected_visual_thesis


ROOT = Path(__file__).resolve().parents[1]


def test_compiler_blocks_missing_visual_thesis_without_core_judgment_fallback():
    with pytest.raises(ValueError, match="P03: VISUAL_THESIS_REQUIRED"):
        _selected_visual_thesis({}, {"core_judgment": "形成可信协同能力"}, "P03")


def test_compiler_blocks_visual_thesis_equal_to_core_judgment():
    with pytest.raises(ValueError, match="VISUAL_THESIS_DUPLICATES_CORE_JUDGMENT"):
        _selected_visual_thesis(
            {"visual_thesis": "形成可信协同能力"},
            {"core_judgment": "形成可信协同能力"},
            "P03",
        )


def test_compiler_accepts_relational_visual_thesis():
    thesis = "数据从来源进入受控处理区，并通过接口流向可信服务结果"
    assert _selected_visual_thesis(
        {"visual_thesis": thesis},
        {"core_judgment": "形成可信服务能力"},
        "P03",
    ) == thesis


def test_compiler_source_contains_no_visual_thesis_core_judgment_fallback():
    source = (ROOT / "cyberppt" / "visual_stage" / "compiler.py").read_text(encoding="utf-8")
    assert 'selected.get("visual_thesis") or source["core_judgment"]' not in source
    assert '"visual_thesis": visual_thesis' in source


def test_visual_structure_skill_documents_strong_visual_thesis_contract():
    skill = (ROOT / "vendor" / "skills" / "ppt-visual-structure-designer" / "SKILL.md").read_text(encoding="utf-8")
    assert "`visual_thesis`为必填独立合同" in skill
    assert "不得直接或近似复用`core_judgment`" in skill
    assert "缺少关系性信号" in skill
