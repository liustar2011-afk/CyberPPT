from pathlib import Path

from cyberppt.visual_prompt_consumer import VisualDesignIR
from scripts.imagegen_pipeline.style09_adapter import adapt_style09


def _design(*, use_scene: bool) -> VisualDesignIR:
    return VisualDesignIR(
        page_number=6,
        visual_thesis="可信编排把分散能力组织为可调用服务",
        business_object="可信服务脊柱",
        primary_focus="统一服务脊柱",
        spatial_organization="贯穿输入、编排与交付的服务脊柱",
        relationship_encoding="以承接和尺度层级表达输入、编排与交付",
        text_integration_method="文字贴附于接口、动作和交付结果",
        semantic_role="业务对象和关系共同承载画面",
        use_scene=use_scene,
        scene_type="电力调度与数据服务协同现场",
        spatial_grammar=("path", "convergence"),
        avoid=("等权卡片墙",),
        source_path=Path("/tmp/deck-visual-spec.json"),
        source_sha256="source",
        page_block_sha256="page",
        source_mode="governed_json",
    )


def test_style09_adapter_preserves_business_semantics_as_non_onscreen_context() -> None:
    adapted = adapt_style09(_design(use_scene=True))

    assert adapted.scene_role == "integrated_scene"
    block = adapted.render_non_onscreen()
    assert "可信编排把分散能力组织为可调用服务" in block
    assert "可信服务脊柱" in block
    assert "以承接和尺度层级表达输入、编排与交付" in block
    assert "文字贴附于接口、动作和交付结果" in block
    assert "等权卡片墙" in block
    assert "不得将字段名或其中业务语句额外渲染为可见文字" in block


def test_style09_adapter_uses_relationship_field_when_scene_is_not_requested() -> None:
    adapted = adapt_style09(_design(use_scene=False))

    assert adapted.scene_role == "business_relationship_field"
    assert "no scene" not in adapted.render_non_onscreen().lower()
