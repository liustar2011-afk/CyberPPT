from dataclasses import replace

from cyberppt.region_graph import validate_region_graph
from cyberppt.page_artifact_spec import VisibleTextBindingSpec
from cyberppt.visual_medium_policy import validate_visual_medium_policy
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt
from tests.test_final_prompt_ir import _artifact_spec


def _current_spec():
    base = _artifact_spec()
    graph = validate_region_graph({
        "canvas_ratio": "2:1",
        "primary_axis": "horizontal",
        "regions": [
            {"id": "RG01", "semantic_refs": ["E1"], "role": "stage", "anchor": "left", "weight": 0.33, "span": "compact", "priority": "primary", "text_ids": ["P01-T01"]},
            {"id": "RG02", "semantic_refs": ["E2"], "role": "stage", "anchor": "center", "weight": 0.34, "span": "compact", "priority": "primary", "text_ids": ["P01-T02"]},
            {"id": "RG03", "semantic_refs": ["E3"], "role": "result", "anchor": "right", "weight": 0.33, "span": "compact", "priority": "primary", "text_ids": ["P01-T03"]},
        ],
        "relations": [
            {"from": "RG01", "to": "RG02", "type": "flow"},
            {"from": "RG02", "to": "RG03", "type": "flow"},
        ],
    })
    policy = validate_visual_medium_policy({
        "preferred": "mixed",
        "allowed": ["business_scene", "object_illustration", "relationship_diagram", "mixed"],
        "scene_policy": "auto",
        "rationale": "Use page mission and drawable business objects to choose the concrete medium.",
    })
    composition = replace(base.composition, focus_policy="sequence_focus")
    bindings = tuple(
        VisibleTextBindingSpec(
            text_id=f"P01-T{index:02d}",
            text=visible_text,
            root_id=f"ROOT-{index}",
            order=index,
            role="root_module",
            hierarchy_level=1,
        )
        for index, visible_text in enumerate(base.typography.visible_text, start=1)
    )
    return replace(
        base,
        region_graph=graph,
        visual_medium_policy=policy,
        composition=composition,
        visible_text_bindings=bindings,
    )


def test_final_prompt_renders_macro_region_authority_without_backend_ids():
    ir = build_final_prompt_ir(_current_spec())
    prompt = render_final_prompt(ir)
    assert "Macro reading axis: horizontal." in prompt
    assert "Focus policy: sequence focus." in prompt
    assert "Region 1: role stage; anchor left; relative share about 33%" in prompt
    assert "Region relationship: Region 1 to Region 2 — flow." in prompt
    assert "Preferred visual medium: mixed." in prompt
    assert "Allowed visual media: business scene; object illustration; relationship diagram; mixed." in prompt
    assert "owns exact visible-text item(s) 1" in prompt
    assert "RG01" not in prompt
    assert "RG02" not in prompt
    assert "E1" not in prompt
    assert "P01-T01" not in prompt
    assert "required text hierarchy:" not in prompt
    assert "card/group heading" not in prompt


def test_semantic_brief_no_longer_delegates_macro_spatial_organization():
    spec = replace(_current_spec(), prompt_mode="semantic_brief")
    ir = build_final_prompt_ir(spec)
    prompt = render_final_prompt(ir)
    assert "follow the macro reading axis defined in Section 5" in prompt
    assert "choose only region-internal reading implementation freely" in prompt
    assert "Follow the authoritative macro region structure" in prompt
    assert "choose the visual reading implementation freely" not in prompt


def test_exact_visible_text_is_not_redeclared_inside_region_lines():
    ir = build_final_prompt_ir(_current_spec())
    prompt = render_final_prompt(ir)
    for text in ir.visible_text:
        assert prompt.count(f'- Exact visible text: "{text}"') == 1
    region_lines = [line for line in prompt.splitlines() if line.startswith("Region ")]
    assert all(text not in "\n".join(region_lines) for text in ir.visible_text)


def test_legacy_ir_without_region_graph_keeps_compatible_prompt():
    base = _artifact_spec()
    ir = build_final_prompt_ir(base)
    prompt = render_final_prompt(ir)
    assert "Macro reading axis:" not in prompt
    assert "Region 1:" not in prompt
