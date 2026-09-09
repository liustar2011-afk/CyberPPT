from cyberppt.copy_contract import (
    CopyContractSpec, ExtraTextPolicySpec, LockedCopySpec, RewriteableCopySpec,
)
from scripts.imagegen_pipeline.final_prompt_ir import (
    CompositionIR, FinalPromptIR, PromptContractError, RegionGraphIR, RegionIR,
    RuntimeLockIR, SemanticGroupIR, TextBindingIR,
)
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt


def _ir(contract):
    return FinalPromptIR(
        deliverable="Create one finished PowerPoint body visual.",
        page_judgment="形成统一可信服务能力。",
        dominant_relationship="数据能力支撑可信服务。",
        reading_path=("input", "service"),
        semantic_groups=(SemanticGroupIR(id="root-a", role="content", summary="可信服务", emphasis="primary"),),
        composition=CompositionIR(
            spatial_organization="one coherent field",
            primary_focus="可信服务",
            visual_responsibility=("Use one coherent business relationship field.",),
        ),
        visible_text=("统一接入", "可信使用"),
        hard_constraints=("Do not render instructions.",),
        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),
        copy_contract=contract,
        text_bindings=(TextBindingIR(
            group_id="root-a", role="content", hierarchy_level=1,
            exact_text=("统一接入", "可信使用"), text_ids=("T1", "T2"),
            hierarchy_levels=(1, 2),
        ),),
        region_graph=RegionGraphIR(
            primary_axis="left_to_right",
            regions=(RegionIR(
                id="R1", semantic_refs=("root-a",), role="content", anchor="center",
                weight=1.0, span="full", priority="primary", text_ids=("T1", "T2"),
            ),),
            relations=(),
        ),
    )


def test_locked_copy_is_declared_exactly_once_without_blanket_rewrite_authority():
    contract = CopyContractSpec(locked_copy=(
        LockedCopySpec(text_id="T1", text="统一接入", region_id="R1", hierarchy=1),
        LockedCopySpec(text_id="T2", text="可信使用", region_id="R1", hierarchy=2),
    ))
    prompt = render_final_prompt(_ir(contract))
    assert prompt.count('- Exact visible text: "统一接入"') == 1
    assert prompt.count('- Exact visible text: "可信使用"') == 1
    assert "Source onscreen text" not in prompt
    assert "You may rewrite, merge, shorten, reorder, split, select, or replace" not in prompt
    assert "Do not add any visible text that is not declared in this copy contract." in prompt
    assert "assigned macro region: Region 1" in prompt
    assert "R1" not in prompt


def test_mixed_copy_contract_only_grants_rewrite_to_explicit_item():
    contract = CopyContractSpec(
        locked_copy=(LockedCopySpec(text_id="T1", text="统一接入", region_id="R1", hierarchy=1),),
        rewriteable_copy=(RewriteableCopySpec(
            text_id="T2", source_text="可信使用", region_id="R1", max_length=12,
            rewrite_goal="shorten without changing business meaning",
        ),),
        extra_text=ExtraTextPolicySpec(),
    )
    prompt = render_final_prompt(_ir(contract))
    assert prompt.count('- Exact visible text: "统一接入"') == 1
    assert prompt.count('- Rewriteable visible source: "可信使用"') == 1
    assert "rewrite goal: shorten without changing business meaning; max length 12" in prompt


def test_prompt_ir_rejects_copy_contract_coverage_drift():
    contract = CopyContractSpec(locked_copy=(LockedCopySpec(text_id="T1", text="统一接入"),))
    try:
        _ir(contract)
    except PromptContractError as exc:
        assert "copy contract visible text must match" in str(exc)
    else:
        raise AssertionError("expected copy-contract coverage validation to fail")
