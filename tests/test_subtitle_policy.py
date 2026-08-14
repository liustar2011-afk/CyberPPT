from __future__ import annotations

from cyberppt.subtitle_policy import resolve_subtitle_policy


def test_comparison_lifecycle_generates_source_bounded_subtitle() -> None:
    result = resolve_subtitle_policy(
        core_message=(
            "平台对产品和场景实行全过程阶段门控，产品和场景分别沿生命周期推进，"
            "进入持续运营和标准化复制。"
        ),
        visual_intent_type="comparison_2col",
        onscreen_expression_form="comparison_2col",
        onscreen_modules=[
            {"display_title": "产品生命周期", "source_refs": ["ST0001"]},
            {"display_title": "场景服务生命周期", "source_refs": ["ST0002"]},
        ],
        content_units=[],
    )

    assert result["mode"] == "generated"
    assert result["subtitle"] == "产品与场景分别在阶段门控下进入持续运营与标准化复制"
    assert result["source_refs"] == ["ST0001", "ST0002"]
    assert result["derived_from"] == ["core_message", "onscreen_modules"]


def test_non_structural_definition_does_not_force_subtitle() -> None:
    result = resolve_subtitle_policy(
        core_message="数据产品是可以独立登记和管理的数据成果。",
        visual_intent_type="concept_definition",
        onscreen_expression_form="",
        onscreen_modules=[{"display_title": "数据产品", "source_refs": ["ST0001"]}],
        content_units=[],
    )

    assert result["mode"] == "not_needed"
    assert result["subtitle"] == ""
    assert result["source_refs"] == []
    assert result["derived_from"] == []


def test_uncertain_or_conditional_relation_requires_author_instead_of_upgrading() -> None:
    result = resolve_subtitle_policy(
        core_message="在条件确认后，拟开展联合试点并验证持续运营可行性。",
        visual_intent_type="phase",
        onscreen_expression_form="flow_3_5",
        onscreen_modules=[
            {"display_title": "条件确认", "source_refs": ["ST0003"]},
            {"display_title": "联合试点", "source_refs": ["ST0004"]},
        ],
        content_units=[],
    )

    assert result["mode"] == "author_required"
    assert result["subtitle"] == ""
    assert result["source_refs"] == ["ST0003", "ST0004"]
