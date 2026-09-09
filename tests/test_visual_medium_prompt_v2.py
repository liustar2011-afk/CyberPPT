from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR, FinalPromptIR, RuntimeLockIR, SemanticGroupIR, VisualMediumPolicyIR,
)
from scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt


def _ir():
    return FinalPromptIR(
        deliverable="Create one finished PowerPoint body visual.",
        page_judgment="形成可信协同能力。",
        dominant_relationship="多主体通过受控接口形成可信协同关系。",
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
        visual_medium_policy=VisualMediumPolicyIR(
            preferred="relationship_diagram",
            secondary="object_illustration",
            allowed=("relationship_diagram", "object_illustration"),
            forbidden=("business_scene", "data_visualization", "mixed"),
            scene_policy="forbidden",
            confidence=0.86,
            rationale="preferred=relationship_diagram score=0.82; semantic relationship signal",
        ),
    )


def test_prompt_exposes_public_medium_v2_contract_without_backend_tokens():
    prompt = render_final_prompt(_ir())
    assert "Preferred visual medium: relationship diagram." in prompt
    assert "Secondary visual medium: object illustration." in prompt
    assert "Forbidden visual media: business scene; data visualization; mixed." in prompt
    assert "Medium confidence: 0.86." in prompt
    assert "relationship_diagram" not in prompt
    assert "object_illustration" not in prompt


def test_debug_receipt_keeps_raw_medium_v2_audit_fields():
    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v5")
    policy = receipt["visual_medium_policy"]
    assert policy["preferred"] == "relationship_diagram"
    assert policy["secondary"] == "object_illustration"
    assert policy["forbidden"] == ["business_scene", "data_visualization", "mixed"]
    assert policy["confidence"] == 0.86
