import pytest

from cyberppt.page_artifact_spec import _visual_budget as artifact_visual_budget
from cyberppt.text_capacity import (
    CONTENT_ACTION_CONTINUE, CONTENT_ACTION_RETURN_STAGE01,
    assert_text_capacity, assess_text_capacity,
)
from cyberppt.visual_stage.compiler import (
    _stage02_text_capacity, _visual_budget as compiler_visual_budget,
)


def test_passed_capacity_declares_continue_stage02_action():
    assessment = assess_text_capacity(
        ["主判断", "支撑事实", "业务结果"],
        root_count=2, hierarchy_levels=(1, 2, 2), canvas=(2048, 1024),
    )
    assert assessment.status == "passed"
    assert assessment.content_action == CONTENT_ACTION_CONTINUE


def test_blocked_capacity_declares_return_to_stage01_action():
    texts = ["高密度正文" * 30 for _ in range(30)]
    assessment = assess_text_capacity(
        texts, root_count=12, hierarchy_levels=(5,) * 30, canvas=(2048, 1024),
    )
    assert assessment.status == "blocked"
    assert assessment.content_action == CONTENT_ACTION_RETURN_STAGE01
    with pytest.raises(ValueError, match="content_action=return_to_stage01"):
        assert_text_capacity(
            texts, root_count=12, hierarchy_levels=(5,) * 30, canvas=(2048, 1024),
        )


def test_dense_text_no_longer_forces_zero_visual_budget_in_artifact_spec():
    dense = tuple("正文" * 30 for _ in range(16))
    budget = artifact_visual_budget(
        {}, topology="parallel_set", scene_policy="allowed", visible_text=dense,
    )
    assert budget.mode == "integrated_scene"
    assert budget.max_auxiliary_fragments > 0


def test_dense_flag_no_longer_forces_zero_visual_budget_in_visual_compiler():
    budget = compiler_visual_budget(
        True,
        {"preferred": "business_scene", "scene_policy": "allowed"},
    )
    assert budget["mode"] == "integrated_scene"
    assert budget["max_auxiliary_fragments"] > 0


def test_visual_stage_capacity_gate_blocks_before_visual_planning():
    source = {
        "locked_text_items": [
            {"text_id": f"T{i}", "text": "高密度正文" * 30}
            for i in range(30)
        ],
        "content_integrity": {
            "root_nodes": [f"R{i}" for i in range(12)],
            "nodes": [{"source_level": 5} for _ in range(30)],
        },
        "body_image_canvas": {"width": 2048, "height": 1024},
    }
    with pytest.raises(ValueError, match="return_to_stage01"):
        _stage02_text_capacity(source, "P09")
