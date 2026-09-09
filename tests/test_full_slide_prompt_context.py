from pathlib import Path

from cyberppt.full_slide_context import default_full_slide_design_context
from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR, FinalPromptIR, FullSlideDesignContextIR, RuntimeLockIR, SemanticGroupIR,
)
from scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt


ROOT = Path(__file__).resolve().parents[1]


def _ir():
    context = default_full_slide_design_context()
    title = context.title_region
    body = context.body_region
    return FinalPromptIR(
        deliverable="Create one finished PowerPoint body visual on a 2048x1024 canvas.",
        page_judgment="形成可信协同能力。",
        dominant_relationship="多主体通过受控接口连接并汇聚形成协同结果。",
        reading_path=("主体", "接口", "结果"),
        semantic_groups=(SemanticGroupIR(id="g1", role="content", summary="可信协同", emphasis="primary"),),
        composition=CompositionIR(
            spatial_organization="one coherent relationship field",
            primary_focus="可信协同",
            visual_responsibility=("Use one relationship-bearing field.",),
        ),
        visible_text=("可信协同",),
        hard_constraints=("Do not render instructions.",),
        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),
        page_title="外置页面标题",
        full_slide_design_context=FullSlideDesignContextIR(
            canvas=context.canvas,
            title_region=(title.x, title.y, title.w, title.h),
            body_region=(body.x, body.y, body.w, body.h),
            body_export_canvas=context.body_export_canvas,
        ),
    )


def test_prompt_knows_16_9_title_region_but_keeps_2_1_body_export():
    prompt = render_final_prompt(_ir())
    assert "Full-slide design context: 1920x1080 (16:9)." in prompt
    assert "External title region: x=128, y=52, w=1664, h=120" in prompt
    assert "Body visual region in the finished slide: x=128, y=216, w=1664, h=832" in prompt
    assert "Body image export remains independent at 2048x1024 (2:1)" in prompt
    assert "do not render title or subtitle into the body image" in prompt


def test_debug_receipt_persists_full_slide_mapping():
    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v5")
    context = receipt["full_slide_design_context"]
    assert context["canvas"] == [1920, 1080, "16:9"]
    assert context["body_export_canvas"] == [2048, 1024, "2:1"]
    assert context["title_render_mode"] == "external_text_layer"


def test_stage02_handoff_declares_full_slide_context_without_replacing_body_canvas():
    source = (ROOT / "cyberppt" / "stage02_handoff.py").read_text(encoding="utf-8")
    assert '"body_image_canvas": dict(BODY_CANVAS)' in source
    assert '"full_slide_design_context": default_full_slide_design_context().to_dict()' in source
    assert '"title_render_mode": "external_text_layer"' in source
