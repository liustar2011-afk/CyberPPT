from __future__ import annotations

import pytest

from cyberppt.page_artifact_spec import _visual_budget as artifact_visual_budget

from cyberppt.visual_stage.compiler import (
    _decision_execution_design,
    _fallback_spatial_organization,
    _resolve_scene_policy,
    _visual_budget,
)


def test_semantic_brief_defaults_to_auto_scene_policy() -> None:
    source = {
        "prompt_mode": "semantic_brief",
        "core_judgment": "四项能力共同构成可信数据服务能力",
        "business_relationships": [
            {
                "subject": "可信数据服务",
                "relation": "包括",
                "objects": ["数据获取", "知识内容", "模型与智能", "分析监测"],
            }
        ],
    }
    design = _decision_execution_design(
        source,
        {"evidence_units": []},
        {"semantic_focus": {"evidence_key": "e1"}},
        "P01",
        "peer_field",
    )

    assert design["scene_policy"] == "auto"
    assert design["use_scene"] is False
    assert "同权证据" in str(design["spatial_organization"])


def test_scene_policy_preserves_legacy_bool_compatibility() -> None:
    assert _resolve_scene_policy({"use_scene": True}, "directed_composition", "P01") == "allowed"
    assert _resolve_scene_policy({"use_scene": False}, "directed_composition", "P01") == "forbidden"


def test_scene_policy_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="unsupported scene_policy"):
        _resolve_scene_policy({"scene_policy": "sometimes"}, "semantic_brief", "P01")


def test_visual_budget_no_longer_depends_on_topology_or_prompt_mode() -> None:
    assert _visual_budget(False, "auto") == {
        "mode": "integrated_scene",
        "max_auxiliary_fragments": 4,
        "scope": "region",
        "region_local_visuals": True,
    }
    assert _visual_budget(False, "forbidden") == {
        "mode": "shared_field",
        "max_auxiliary_fragments": 1,
        "scope": "page",
        "region_local_visuals": False,
    }


def test_dense_page_still_limits_visual_fragments() -> None:
    assert _visual_budget(True, "required") == {
        "mode": "relationship_field_only",
        "max_auxiliary_fragments": 0,
        "scope": "page",
        "region_local_visuals": False,
    }


def test_fallback_spatial_copy_respects_focus_policy() -> None:
    peer = _fallback_spatial_organization("peer_field", "能力一", "能力体系")
    sequence = _fallback_spatial_organization("sequence_focus", "环节一", "业务流程")
    single = _fallback_spatial_organization("single_anchor", "最终结果", "业务链")

    assert "相近视觉权重" in peer
    assert "阶段推进" in sequence
    assert "主视觉锚点" in single
    assert "唯一视觉焦点" not in peer


def test_artifact_budget_allows_parallel_auto_scene_policy() -> None:
    budget = artifact_visual_budget({}, topology="parallel_set", use_scene=False, scene_policy="auto")
    assert budget.mode == "integrated_scene"
    assert budget.region_local_visuals is True
