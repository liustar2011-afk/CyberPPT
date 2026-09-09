import pytest

from cyberppt.acceptance_contract import build_acceptance_spec
from cyberppt.composition_strategy import resolve_composition_strategy, validate_composition_strategy
from scripts.imagegen_pipeline.final_prompt_ir import (
    AcceptanceIR, CompositionIR, FinalPromptIR, RuntimeLockIR, SemanticGroupIR,
)
from scripts.imagegen_pipeline.final_prompt_renderer import (
    ACCEPTANCE_HEADING, render_debug_receipt, render_final_prompt,
)
from scripts.imagegen_pipeline.prompt_compiler import (
    ARTIFACT_PROMPT_COMPILER, ARTIFACT_PROMPT_COMPILER_V3, PROMPT_COMPILERS,
    validate_prompt_compiler,
)


def _ir():
    return FinalPromptIR(
        deliverable="Create one finished PowerPoint body visual.",
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
        acceptance=AcceptanceIR(
            exact_copy_coverage=1.0, extra_text_count=0,
            region_ownership="all_declared_copy_stays_in_assigned_macro_region",
            relationship_accuracy="source_supported_relationships_only",
            hierarchy_preservation="preserve_declared_hierarchy",
            minimum_readability="readable_at_normal_slide_view",
            forbidden_structure_absence=True, style_lock_conformance=True,
        ),
    )


def test_final_prompt_contains_machine_readable_acceptance_section():
    prompt = render_final_prompt(_ir())
    assert prompt.count(ACCEPTANCE_HEADING) == 1
    assert "Exact copy coverage: 100% of locked copy must be present exactly once." in prompt
    assert "Maximum extra visible text count: 0." in prompt
    assert "Region ownership: all declared copy stays in assigned macro region." in prompt
    assert "Relationship accuracy: source supported relationships only." in prompt
    assert "Hierarchy preservation: preserve declared hierarchy." in prompt
    assert "Minimum readability: readable at normal slide view." in prompt
    assert "Forbidden structure absence: required." in prompt
    assert "Style lock conformance: required." in prompt
    assert prompt.index(ACCEPTANCE_HEADING) < prompt.index("[Hard constraints]") < prompt.index("[7. Runtime lock]")


def test_debug_receipt_acceptance_matches_prompt_ir():
    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v6")
    acceptance = receipt["acceptance"]
    assert acceptance["exact_copy_coverage"] == 1.0
    assert acceptance["extra_text_count"] == 0
    assert acceptance["style_lock_conformance"] is True


def test_acceptance_domain_projects_to_ir_values():
    domain = build_acceptance_spec()
    assert domain.to_dict()["exact_copy_coverage"] == 1.0


def test_composition_strategy_mapping_validator_preserves_blueprint():
    strategy = resolve_composition_strategy(
        topology="directed_flow", focus_policy="sequence_focus", evidence_count=3,
        medium="business_scene", page_index=1,
    )
    restored = validate_composition_strategy(strategy.to_dict())
    assert restored.strategy_id == strategy.strategy_id
    drift = strategy.to_dict(); drift["primary_axis"] = "radial"
    with pytest.raises(ValueError, match="drifted"):
        validate_composition_strategy(drift)


def test_artifact_spec_v3_is_additive_and_v2_remains_valid():
    assert ARTIFACT_PROMPT_COMPILER in PROMPT_COMPILERS
    assert ARTIFACT_PROMPT_COMPILER_V3 in PROMPT_COMPILERS
    assert validate_prompt_compiler("artifact-spec-v2") == "artifact-spec-v2"
    assert validate_prompt_compiler("artifact-spec-v3") == "artifact-spec-v3"
