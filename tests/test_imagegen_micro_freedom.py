from dataclasses import replace

from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt
from tests.test_final_prompt_ir import _artifact_spec
from tests.test_prompt_macro_structure import _current_spec


def test_region_page_gets_structured_micro_visual_freedom():
    ir = build_final_prompt_ir(_current_spec())
    assert ir.micro_visual_freedom is not None
    assert any("business-object depiction" in item for item in ir.micro_visual_freedom.allowed)
    assert any("merge or split macro regions" in item for item in ir.micro_visual_freedom.forbidden)


def test_prompt_locks_macro_mutation_and_allows_region_internal_design():
    prompt = render_final_prompt(build_final_prompt_ir(_current_spec()))
    assert "ImageGen region-internal freedom:" in prompt
    assert "Choose the exact business-object depiction inside each macro region." in prompt
    assert "Do not merge or split macro regions." in prompt
    assert "Do not move exact visible text from its assigned macro region to another region." in prompt
    assert "Do not change the focus policy" in prompt
    assert "Do not leave the allowed visual media or violate the scene policy." in prompt


def test_directed_composition_keeps_same_micro_freedom_boundary():
    spec = replace(_current_spec(), prompt_mode="directed_composition")
    prompt = render_final_prompt(build_final_prompt_ir(spec))
    assert "ImageGen region-internal freedom:" in prompt
    assert "Macro visual authority remains locked:" in prompt


def test_legacy_spec_without_region_or_medium_policy_remains_compatible():
    ir = build_final_prompt_ir(_artifact_spec())
    assert ir.micro_visual_freedom is None
    prompt = render_final_prompt(ir)
    assert "ImageGen region-internal freedom:" not in prompt


def test_debug_receipt_persists_micro_visual_freedom():
    ir = build_final_prompt_ir(_current_spec())
    receipt = render_debug_receipt(ir, page_id="P01", compiler="artifact-spec-v2", prompt_ir_version="v3")
    freedom = receipt["micro_visual_freedom"]
    assert freedom is not None
    assert freedom["allowed"]
    assert freedom["forbidden"]
